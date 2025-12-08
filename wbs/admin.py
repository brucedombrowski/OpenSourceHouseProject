# wbs/admin.py

from django.contrib import admin
from django.utils.html import format_html
from mptt.admin import DraggableMPTTAdmin

from .models import ProjectItem, Tag, TaskDependency, WbsItem
from .utils import normalize_code_for_sort


class ProjectItemInline(admin.TabularInline):
    """
    Inline editor for ProjectItems on the WBS Item detail page.
    """

    model = ProjectItem
    extra = 1  # one empty row by default
    # wbs_item is implied by the parent WbsItem, so we don't show it
    fields = (
        "title",
        "type",
        "status",
        "priority",
        "severity",
        "date_started",
        "date_completed",
        "estimate_hours",
        "actual_hours",
        "owner",
        "reported_by",
        "external_ref",
        "tags",
    )
    readonly_fields = ()
    show_change_link = True  # allows clicking through to full ProjectItem page


@admin.register(WbsItem)
class WbsItemAdmin(DraggableMPTTAdmin):
    mptt_indent_field = "wbs_label"
    # Use MPTT natural tree order so draggable reordering works correctly
    ordering = ("tree_id", "lft")

    # Attach inline project items
    inlines = [ProjectItemInline]

    list_display = (
        "tree_actions",
        "indented_title",
        "code_display",
        "parent",
        "status",
        "percent_complete",
        "planned_start",
        "planned_end",
        "duration_days",
        "sequence",
        "is_milestone",
        "project_items_open",
        "project_items_total",
    )
    list_display_links = ("indented_title",)

    list_filter = ("status", "is_milestone")
    search_fields = ("code", "name", "description", "notes")

    actions = ["renumber_wbs_action", "rollup_dates_action"]

    def get_queryset(self, request):
        """Optimize queryset with prefetch for project items."""
        qs = super().get_queryset(request)
        return qs.with_project_items()

    # ---- Labels / display helpers ----

    def wbs_label(self, instance):
        return f"{instance.code} {instance.name}"

    wbs_label.short_description = "Task"

    def code_display(self, obj):
        return obj.code

    code_display.short_description = "Code"
    code_display.admin_order_field = "sort_key"

    # ---- ProjectItem counts ----

    def project_items_open(self, obj):
        """
        Count of linked ProjectItems that are not done/closed.
        """
        open_statuses = [
            ProjectItem.STATUS_TODO,
            ProjectItem.STATUS_IN_PROGRESS,
            ProjectItem.STATUS_BLOCKED,
            ProjectItem.STATUS_OPEN,
        ]
        return obj.project_items.filter(status__in=open_statuses).count()

    project_items_open.short_description = "Open items"

    def project_items_total(self, obj):
        """
        Total number of ProjectItems linked to this WBS node.
        """
        return obj.project_items.count()

    project_items_total.short_description = "Total items"

    # ---- Actions ----

    @admin.action(description="Renumber entire WBS (outline codes)")
    def renumber_wbs_action(self, request, queryset):
        # Use tree_id and lft (MPPT fields) to maintain tree order consistency
        # This matches the renumber_wbs management command behavior
        roots = WbsItem.objects.filter(parent__isnull=True).order_by("tree_id", "lft")

        def renumber_node(node, prefix, index):
            new_code = f"{prefix}.{index}" if prefix else str(index)
            try:
                new_seq = int(new_code.split(".")[-1])
            except ValueError:
                new_seq = 1

            node.code = new_code
            node.sequence = new_seq
            node.sort_key = normalize_code_for_sort(new_code)
            node.save(update_fields=["code", "sequence", "sort_key"])

            # Use MPPT order_by for children to ensure consistent tree traversal
            children = node.get_children().order_by("tree_id", "lft")
            for child_idx, child in enumerate(children, start=1):
                renumber_node(child, new_code, child_idx)

        for root_idx, root in enumerate(roots, start=1):
            renumber_node(root, "", root_idx)

        self.message_user(request, "WBS renumbered successfully.")

    @admin.action(description="Roll up planned dates from children → parents")
    def rollup_dates_action(self, request, queryset):
        count = 0
        for item in queryset:
            if item.update_rollup_dates(include_self=True):
                count += 1
        self.message_user(request, f"Rolled up dates for {count} items.")

    class Media:
        css = {"all": ("wbs/admin_wbs.css",)}
        js = ("wbs/admin_wbs.js",)


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = ("id", "predecessor", "successor", "dependency_type", "lag_days")
    search_fields = (
        "predecessor__code",
        "predecessor__name",
        "successor__code",
        "successor__name",
    )
    list_filter = ("dependency_type",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name",)


@admin.register(ProjectItem)
class ProjectItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "type",
        "status",
        "priority",
        "severity",
        "wbs_link",
        "owner",
        "date_started",
        "date_completed",
        "estimate_hours",
        "actual_hours",
    )
    list_filter = (
        "type",
        "status",
        "priority",
        "severity",
        "wbs_item",
    )
    search_fields = (
        "title",
        "description",
        "wbs_item__code",
        "wbs_item__name",
        "reported_by",
        "owner",
        "tags__name",
    )
    autocomplete_fields = ("wbs_item", "tags")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("wbs_item", "owner")
    list_prefetch_related = ("tags",)

    def wbs_link(self, obj):
        if not obj.wbs_item:
            return ""
        code = obj.wbs_item.code
        url = f"/gantt/?highlight={code}#code-{code}"
        return format_html("<a href='{}' target='_blank' rel='noopener'>{}</a>", url, code)

    wbs_link.short_description = "WBS"
