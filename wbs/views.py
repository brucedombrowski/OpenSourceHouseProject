# wbs/views.py
"""
Aggregate view functions for the wbs app.

This module re-exports views from more focused view modules
(e.g., views_gantt.py, views_api.py, etc.) so that existing
imports like `from wbs.views import gantt_view` continue to work
even as we split the codebase into smaller files.
"""

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .constants import KANBAN_STATUS_ORDER, PROJECT_ITEM_STATUS_MAP
from .models import ProjectItem
from .utils import (
    get_priority_rank_case,
    group_items_by_status,
    group_items_by_wbs,
)

# Gantt-related views
from .views_gantt import (
    gantt_chart,
    gantt_optimize_schedule,
    gantt_set_task_dates,
    gantt_shift_task,
    gantt_view,
)

__all__ = [
    "gantt_chart",
    "gantt_view",
    "gantt_shift_task",
    "gantt_set_task_dates",
    "gantt_optimize_schedule",
    "project_item_board",
    "project_item_list",
    "project_item_status_update",
]


@ensure_csrf_cookie
def project_item_board(request):
    """
    Lightweight Kanban view for ProjectItems grouped by status.
    """
    items = (
        ProjectItem.objects.select_related("wbs_item")
        .annotate(priority_rank=get_priority_rank_case())
        .order_by("status", "priority_rank", "-created_at")
    )

    columns = group_items_by_status(
        items,
        KANBAN_STATUS_ORDER,
        PROJECT_ITEM_STATUS_MAP,
    )

    return render(
        request,
        "wbs/kanban.html",
        {
            "columns": columns,
        },
    )


@ensure_csrf_cookie
def project_item_list(request):
    """
    Detailed list view for ProjectItems, grouped by WBS and filterable by type/status/priority.
    """
    # Get filter parameters
    filter_type = request.GET.get("type")
    filter_status = request.GET.get("status")
    filter_priority = request.GET.get("priority")
    filter_severity = request.GET.get("severity")
    filter_wbs = request.GET.get("wbs")
    search_query = request.GET.get("q", "").strip()

    # Build query
    items = ProjectItem.objects.select_related("wbs_item")

    if filter_type:
        items = items.filter(type=filter_type)
    if filter_status:
        items = items.filter(status=filter_status)
    if filter_priority:
        items = items.filter(priority=filter_priority)
    if filter_severity:
        items = items.filter(severity=filter_severity)
    if filter_wbs:
        items = items.filter(wbs_item_id=filter_wbs)
    if search_query:
        items = items.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(wbs_item__code__icontains=search_query)
            | Q(wbs_item__name__icontains=search_query)
            | Q(owner__icontains=search_query)
            | Q(reported_by__icontains=search_query)
        )

    # Group by WBS item
    items = items.annotate(priority_rank=get_priority_rank_case()).order_by(
        "wbs_item__sort_key", "priority_rank", "-created_at"
    )

    sorted_groups = group_items_by_wbs(items)

    context = {
        "groups": sorted_groups,
        "all_types": ProjectItem.TYPE_CHOICES,
        "all_statuses": ProjectItem.STATUS_CHOICES,
        "all_priorities": ProjectItem.PRIORITY_CHOICES,
        "all_severities": ProjectItem.SEVERITY_CHOICES,
        "current_type": filter_type,
        "current_status": filter_status,
        "current_priority": filter_priority,
        "current_severity": filter_severity,
        "current_wbs": filter_wbs,
        "search_query": search_query,
        "total_count": sum(len(g[1]) for g in sorted_groups),
    }

    return render(request, "wbs/project_item_list.html", context)


@require_POST
def project_item_status_update(request):
    """
    Lightweight endpoint to update a ProjectItem's status (Kanban drag/drop).
    """
    item_id = request.POST.get("id")
    new_status = request.POST.get("status")

    if not item_id or not new_status:
        return JsonResponse({"ok": False, "error": "id and status are required"}, status=400)

    valid_statuses = {choice[0] for choice in ProjectItem.STATUS_CHOICES}
    if new_status not in valid_statuses:
        return JsonResponse({"ok": False, "error": "Invalid status"}, status=400)

    try:
        item = ProjectItem.objects.get(pk=item_id)
    except ProjectItem.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Item not found"}, status=404)

    item.status = new_status
    item.save(update_fields=["status", "updated_at"])

    return JsonResponse({"ok": True, "id": item_id, "status": new_status})
