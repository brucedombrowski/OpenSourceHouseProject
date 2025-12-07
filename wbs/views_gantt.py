# wbs/views_gantt.py

from datetime import date, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import ProjectItem, TaskDependency, WbsItem
from .performance import profile_view


@profile_view("gantt_chart")
@staff_member_required
def gantt_chart(request):
    """
    Render a Gantt chart for WBS items with planned dates.

    Features:
      - 3-level time axis: Year (top), Month (middle), Day (bottom, weekly/Mondays)
      - Collapsible task hierarchy (driven by template JS using has_children/level_indent)
      - ProjectItem awareness:
          * Each WbsItem can have linked ProjectItems (issues/tasks/etc.)
          * Server-side filter / highlight support via query params:
              - mode: "none" | "highlight" | "filter"
              - items_only: "1" (only tasks with any ProjectItems)
              - type: repeated param (ProjectItem.type)
              - status: repeated param (ProjectItem.status)
              - priority: repeated param (ProjectItem.priority)
              - severity: repeated param (ProjectItem.severity)
    """

    # ---- Filter parameters from query string ----
    filter_mode = request.GET.get("mode", "none")  # "none", "highlight", "filter"
    has_items_only = request.GET.get("items_only") == "1"

    selected_types = request.GET.getlist("type")
    selected_statuses = request.GET.getlist("status")
    selected_priorities = request.GET.getlist("priority")
    selected_severities = request.GET.getlist("severity")
    selected_owners = request.GET.getlist("owner")
    selected_owner_ids = {oid for oid in selected_owners if oid}

    # ---- Base queryset: tasks with dates + prefetch ProjectItems ----
    qs = (
        WbsItem.objects.filter(planned_start__isnull=False, planned_end__isnull=False)
        .select_related("parent")
        .prefetch_related(
            Prefetch(
                "project_items",
                queryset=ProjectItem.objects.select_related("owner").order_by("-created_at"),
            )
        )
        .order_by("tree_id", "lft")  # MPTT-style ordering
    )

    # ---- DB-level filtering when mode = "filter" ----
    if filter_mode == "filter":
        if has_items_only:
            qs = qs.filter(project_items__isnull=False)

        if selected_types:
            qs = qs.filter(project_items__type__in=selected_types)

        if selected_statuses:
            qs = qs.filter(project_items__status__in=selected_statuses)

        if selected_priorities:
            qs = qs.filter(project_items__priority__in=selected_priorities)

        if selected_severities:
            qs = qs.filter(project_items__severity__in=selected_severities)

        if selected_owner_ids:
            qs = qs.filter(project_items__owner_id__in=selected_owner_ids)

        qs = qs.distinct()

    tasks = list(qs)

    # ---- Prepare owner list for filter UI (computed once, used in both branches) ----
    User = get_user_model()
    all_owners = [
        {
            "id": str(user.id),
            "label": (user.get_full_name().strip() or user.get_username()),
        }
        for user in User.objects.filter(project_items__isnull=False).distinct().order_by("username")
    ]

    # ---- No-data case ----
    if not tasks:
        context = {
            "tasks": [],
            "min_start": None,
            "max_end": None,
            "total_days": 0,
            "timeline_width_px": 0,
            "year_bands": [],
            "month_bands": [],
            "day_ticks": [],
            # Filter UI state
            "filter_mode": filter_mode,
            "has_items_only": has_items_only,
            "selected_types": selected_types,
            "selected_statuses": selected_statuses,
            "selected_priorities": selected_priorities,
            "selected_severities": selected_severities,
            "selected_owners": list(selected_owner_ids),
            # Choices for building the filter form
            "projectitem_type_choices": ProjectItem.TYPE_CHOICES,
            "projectitem_status_choices": ProjectItem.STATUS_CHOICES,
            "projectitem_priority_choices": ProjectItem.PRIORITY_CHOICES,
            "projectitem_severity_choices": ProjectItem.SEVERITY_CHOICES,
            "all_owners": all_owners,
        }
        return render(request, "wbs/gantt.html", context)

    # ---- Overall date range ----
    min_start = min(t.planned_start for t in tasks if t.planned_start)
    max_end = max(t.planned_end for t in tasks if t.planned_end)

    # Ensure we are working with date objects (not datetimes)
    if hasattr(min_start, "date"):
        min_start = min_start.date()
    if hasattr(max_end, "date"):
        max_end = max_end.date()

    total_days = (max_end - min_start).days + 1

    # Pixels per day (controls horizontal zoom)
    px_per_day = 4
    timeline_width_px = total_days * px_per_day

    # ---- Helper: does a WbsItem match the current ProjectItem filters? ----
    def item_matches_filters(item) -> bool:
        project_items = list(item.project_items.all())

        # If we require at least one ProjectItem and there are none
        if has_items_only and not project_items:
            return False

        # If no specific ProjectItem filters are selected:
        if not (
            selected_types
            or selected_statuses
            or selected_priorities
            or selected_severities
            or selected_owner_ids
        ):
            # Match everything (subject to has_items_only above)
            return True

        if not project_items:
            # No items to satisfy type/status/priority/severity/owner filters
            return False

        # Type filter
        if selected_types and not any(pi.type in selected_types for pi in project_items):
            return False

        # Status filter
        if selected_statuses and not any(pi.status in selected_statuses for pi in project_items):
            return False

        # Priority filter
        if selected_priorities and not any(
            pi.priority in selected_priorities for pi in project_items
        ):
            return False

        # Severity filter
        if selected_severities and not any(
            pi.severity in selected_severities for pi in project_items
        ):
            return False

        # Owner filter (empty owner "" is treated as unassigned)
        if selected_owner_ids and not any(
            str(pi.owner_id) in selected_owner_ids for pi in project_items
        ):
            return False

        return True

    # ---- Dependencies for highlighting ----
    task_ids = [t.id for t in tasks]
    deps = TaskDependency.objects.filter(
        models.Q(predecessor_id__in=task_ids) | models.Q(successor_id__in=task_ids)
    ).select_related("predecessor", "successor")

    incoming = {}  # succ_code -> [pred_codes]
    outgoing = {}  # pred_code -> [succ_codes]
    outgoing_meta = {}  # pred_code -> list of dicts {code, type, lag}
    for dep in deps:
        pred_code = dep.predecessor.code
        succ_code = dep.successor.code
        outgoing.setdefault(pred_code, []).append(succ_code)
        incoming.setdefault(succ_code, []).append(pred_code)
        outgoing_meta.setdefault(pred_code, []).append(
            {
                "code": succ_code,
                "type": getattr(dep, "dependency_type", TaskDependency.FS),
                "lag": getattr(dep, "lag_days", 0),
            }
        )

    # ---- Annotate each task with bar offsets, indentation, flags ----
    for t in tasks:
        start = t.planned_start
        end = t.planned_end
        if hasattr(start, "date"):
            start = start.date()
        if hasattr(end, "date"):
            end = end.date()

        offset_days = (start - min_start).days
        duration_days = max(1, (end - start).days + 1)

        t.bar_offset = offset_days * px_per_day
        t.bar_width = duration_days * px_per_day

        # MPTT provides `level`; we use it for indenting in the template
        level = getattr(t, "level", 0)
        t.level_indent = range(level)

        # Used by template to decide whether to show an expander
        # (MPTT provides get_children()).
        try:
            t.has_children = t.get_children().exists()
        except AttributeError:
            # Fallback if not using MPTT's get_children
            t.has_children = (
                bool(getattr(t, "children", []).all()) if hasattr(t, "children") else False
            )

        # ProjectItem-related flags
        project_items = list(t.project_items.all())
        t.has_project_items = bool(project_items)
        t.matches_filter = item_matches_filters(t)
        t.predecessor_codes = incoming.get(t.code, [])
        t.successor_codes = outgoing.get(t.code, [])
        t.successor_meta = outgoing_meta.get(t.code, [])

    # ---- Build Year, Month, Day structures for the 3-level timeline ----

    # YEAR BANDS
    year_bands = []
    start_year = min_start.year
    end_year = max_end.year

    for year in range(start_year, end_year + 1):
        band_start_date = date(year, 1, 1)
        if band_start_date < min_start:
            band_start_date = min_start

        next_year_start = date(year + 1, 1, 1)
        band_end_date = next_year_start - timedelta(days=1)
        if band_end_date > max_end:
            band_end_date = max_end

        offset_days = (band_start_date - min_start).days
        width_days = (band_end_date - band_start_date).days + 1

        year_bands.append(
            {
                "label": str(year),
                "offset_px": offset_days * px_per_day,
                "width_px": width_days * px_per_day,
            }
        )

    # MONTH BANDS
    month_bands = []
    month_cursor = date(min_start.year, min_start.month, 1)

    while month_cursor <= max_end:
        band_start_date = max(month_cursor, min_start)

        if month_cursor.month == 12:
            next_month = date(month_cursor.year + 1, 1, 1)
        else:
            next_month = date(month_cursor.year, month_cursor.month + 1, 1)

        band_end_date = next_month - timedelta(days=1)
        if band_end_date > max_end:
            band_end_date = max_end

        offset_days = (band_start_date - min_start).days
        width_days = (band_end_date - band_start_date).days + 1

        label = month_cursor.strftime("%b")

        month_bands.append(
            {
                "label": label,
                "offset_px": offset_days * px_per_day,
                "width_px": width_days * px_per_day,
            }
        )

        month_cursor = next_month

    # DAY TICKS: one per Monday for readability
    day_ticks = []
    first_monday = min_start
    offset_to_monday = (7 - first_monday.weekday()) % 7
    first_monday = first_monday + timedelta(days=offset_to_monday)

    day_cursor = first_monday
    while day_cursor <= max_end:
        offset_days = (day_cursor - min_start).days
        day_ticks.append(
            {
                "label": day_cursor.strftime("%d"),
                "offset_px": offset_days * px_per_day,
            }
        )
        day_cursor += timedelta(days=7)

    context = {
        "tasks": tasks,
        "min_start": min_start,
        "max_end": max_end,
        "total_days": total_days,
        "px_per_day": px_per_day,
        "timeline_width_px": timeline_width_px,
        "year_bands": year_bands,
        "month_bands": month_bands,
        "day_ticks": day_ticks,
        # Filter UI state
        "filter_mode": filter_mode,
        "has_items_only": has_items_only,
        "selected_types": selected_types,
        "selected_statuses": selected_statuses,
        "selected_priorities": selected_priorities,
        "selected_severities": selected_severities,
        "selected_owners": list(selected_owner_ids),
        # Choices for building the filter form
        "projectitem_type_choices": ProjectItem.TYPE_CHOICES,
        "projectitem_status_choices": ProjectItem.STATUS_CHOICES,
        "projectitem_priority_choices": ProjectItem.PRIORITY_CHOICES,
        "projectitem_severity_choices": ProjectItem.SEVERITY_CHOICES,
        "all_owners": all_owners,
    }
    return render(request, "wbs/gantt.html", context)


# Backward-compatible alias (if any code still imports `gantt_view`)
gantt_view = gantt_chart


@staff_member_required
@require_POST
def gantt_shift_task(request):
    """
    Shift a task (and its descendants) by moving planned_start/planned_end.
    Expects POST fields: code, new_start (YYYY-MM-DD).
    """
    code = request.POST.get("code", "").strip()
    new_start_str = request.POST.get("new_start", "").strip()

    if not code or not new_start_str:
        return JsonResponse({"ok": False, "error": "code and new_start are required"}, status=400)

    try:
        target = WbsItem.objects.get(code=code)
    except WbsItem.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Task not found"}, status=404)

    if not target.planned_start or not target.planned_end:
        return JsonResponse({"ok": False, "error": "Task missing planned dates"}, status=400)

    try:
        new_start = date.fromisoformat(new_start_str)
    except ValueError:
        return JsonResponse({"ok": False, "error": "Invalid date"}, status=400)

    duration = (target.planned_end - target.planned_start).days
    if duration < 0:
        duration = 0

    delta_days = (new_start - target.planned_start).days
    if delta_days == 0:
        return JsonResponse(
            {
                "ok": True,
                "start": target.planned_start.isoformat(),
                "end": target.planned_end.isoformat(),
            }
        )

    def shift_subtree(node, delta):
        stack = [node]
        while stack:
            n = stack.pop()
            update_fields = []
            if n.planned_start:
                n.planned_start = n.planned_start + timedelta(days=delta)
                update_fields.append("planned_start")
            if n.planned_end:
                n.planned_end = n.planned_end + timedelta(days=delta)
                update_fields.append("planned_end")
            if update_fields:
                n.save(update_fields=update_fields)
            stack.extend(list(n.get_children()))

    shift_subtree(target, delta_days)

    # Re-roll parents to keep rollups consistent
    for ancestor in target.get_ancestors():
        ancestor.update_rollup_dates(include_self=True)

    # Refresh target after updates
    target.refresh_from_db()
    new_end = target.planned_start + timedelta(days=duration)
    target.planned_end = new_end
    target.save(update_fields=["planned_end"])

    # Final parent rollup after end adjustment
    for ancestor in target.get_ancestors():
        ancestor.update_rollup_dates(include_self=True)

    return JsonResponse(
        {
            "ok": True,
            "code": target.code,
            "start": target.planned_start.isoformat() if target.planned_start else None,
            "end": target.planned_end.isoformat() if target.planned_end else None,
        }
    )


@staff_member_required
@require_POST
def gantt_set_task_dates(request):
    """
    Set explicit planned_start/planned_end for a task (no auto-shift of children).
    """
    code = request.POST.get("code", "").strip()
    start_str = request.POST.get("start", "").strip()
    end_str = request.POST.get("end", "").strip()

    if not code or not start_str or not end_str:
        return JsonResponse({"ok": False, "error": "code, start, and end are required"}, status=400)

    try:
        target = WbsItem.objects.get(code=code)
    except WbsItem.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Task not found"}, status=404)

    try:
        start_date = date.fromisoformat(start_str)
        end_date = date.fromisoformat(end_str)
    except ValueError:
        return JsonResponse({"ok": False, "error": "Invalid date"}, status=400)

    if end_date < start_date:
        return JsonResponse({"ok": False, "error": "End date cannot be before start"}, status=400)

    target.planned_start = start_date
    target.planned_end = end_date
    target.save(update_fields=["planned_start", "planned_end"])

    # Roll up ancestors
    for ancestor in target.get_ancestors():
        ancestor.update_rollup_dates(include_self=True)

    return JsonResponse(
        {
            "ok": True,
            "code": target.code,
            "start": target.planned_start.isoformat(),
            "end": target.planned_end.isoformat(),
        }
    )


@staff_member_required
@require_POST
def gantt_optimize_schedule(request):
    """
    Auto-adjust schedule respecting dependencies (simple ASAP forward pass).
    - Orders tasks topologically by dependencies.
    - Respects planned durations.
    - Sets each task start to max(parent start, root start, predecessors anchor+lag).
    - Rolls up ancestors after updates.
    Returns updated tasks (code, start, end).
    """
    tasks = (
        WbsItem.objects.prefetch_related("predecessor_links__predecessor")
        .select_related("parent")
        .all()
    )
    by_code = {t.code: t for t in tasks if t.code}
    preds = {t.code: [] for t in tasks if t.code}
    succs = {t.code: [] for t in tasks if t.code}

    # Build dependency graph
    for t in tasks:
        for dep in t.predecessor_links.all():
            pcode = dep.predecessor.code
            scode = dep.successor.code
            if pcode and scode:
                succs.setdefault(pcode, []).append((scode, dep))
                preds.setdefault(scode, []).append((pcode, dep))

    # Kahn's algorithm
    indeg = {code: len(preds.get(code, [])) for code in preds}
    queue = [c for c, d in indeg.items() if d == 0]
    topo = []
    while queue:
        c = queue.pop(0)
        topo.append(c)
        for n, _dep in succs.get(c, []):
            if n in indeg:
                indeg[n] -= 1
                if indeg[n] == 0:
                    queue.append(n)

    # If cycle detected, fallback to all codes as-is
    if len(topo) < len(preds):
        topo = list(by_code.keys())

    updated = []
    root_code = "1"
    root_start = None
    root_task = by_code.get(root_code)
    if root_task and root_task.planned_start:
        root_start = root_task.planned_start

    # Forward pass
    for code in topo:
        task = by_code.get(code)
        if not task:
            continue
        if code == root_code:
            # Keep root as anchor; do not move it
            continue

        # Duration
        if task.planned_start and task.planned_end:
            duration = (task.planned_end - task.planned_start).days
        else:
            duration = 0

        # Earliest based on predecessors with lag and type
        pred_earliest = None
        for pcode, dep in preds.get(code, []):
            ptask = by_code.get(pcode)
            if not ptask:
                continue
            try:
                lag = float(dep.lag_days or 0)
            except Exception:
                lag = 0
            dep_type = getattr(dep, "dependency_type", TaskDependency.FS)
            if dep_type == TaskDependency.FS:
                anchor = ptask.planned_end
            elif dep_type == TaskDependency.SS:
                anchor = ptask.planned_start
            elif dep_type == TaskDependency.FF:
                anchor = ptask.planned_end
            elif dep_type == TaskDependency.SF:
                anchor = ptask.planned_start
            else:
                anchor = ptask.planned_end

            if anchor:
                candidate = anchor + timedelta(days=lag)
                if pred_earliest is None or candidate > pred_earliest:
                    pred_earliest = candidate

        # Parent constraint: start no earlier than parent start
        parent = task.parent
        parent_start = parent.planned_start if parent and parent.planned_start else None

        # Build earliest start: prioritize predecessor constraints, then parent constraint
        earliest = None
        if pred_earliest:
            # If there are predecessors, use their calculated earliest
            # (don't include current task.planned_start to allow slack removal)
            earliest = pred_earliest

        if parent_start:
            # Parent constraint: cannot start before parent
            if earliest:
                earliest = max(earliest, parent_start)
            else:
                earliest = parent_start

        if root_start and not pred_earliest:
            # Only apply root start if no predecessors (root drives the schedule otherwise)
            if earliest:
                earliest = max(earliest, root_start)
            else:
                earliest = root_start

        if not earliest:
            # fallback to today for tasks without dates
            earliest = date.today()

        new_start = earliest
        new_end = new_start + timedelta(days=max(duration, 0))

        task.planned_start = new_start
        task.planned_end = new_end
        task.save(update_fields=["planned_start", "planned_end"])
        updated.append({"code": code, "start": new_start.isoformat(), "end": new_end.isoformat()})

    # Roll up ancestors once
    roots = [t for t in tasks if t.parent is None]
    for root in roots:
        root.update_rollup_dates(include_self=True)

    return JsonResponse({"ok": True, "message": "Schedule optimized", "tasks": updated})
