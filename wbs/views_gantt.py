# wbs/views_gantt.py

from datetime import date, timedelta
from typing import Dict, List, Set

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import models
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .constants import (
    GANTT_PIXELS_PER_DAY,
    GANTT_RESOURCE_CONFLICT_THRESHOLD,
    GANTT_TIMELINE_CACHE_SECONDS,
)
from .models import ProjectItem, TaskDependency, WbsItem
from .performance import profile_view
from .utils import (
    days_between,
    ensure_date,
    get_owner_display_name,
)


def compute_timeline_bands(min_start, max_end, px_per_day):
    """
    Compute year/month/day timeline bands for Gantt chart.
    Results are cached for 1 hour based on date range and scale.

    Args:
        min_start: datetime.date - earliest task start
        max_end: datetime.date - latest task end
        px_per_day: int - pixels per day (zoom level)

    Returns:
        dict with keys: year_bands, month_bands, day_ticks
    """
    cache_key = f"gantt_timeline:{min_start}:{max_end}:{px_per_day}"
    cached = cache.get(cache_key)
    if cached:
        return cached

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

    result = {
        "year_bands": year_bands,
        "month_bands": month_bands,
        "day_ticks": day_ticks,
    }

    # Cache for 1 hour
    cache.set(cache_key, result, GANTT_TIMELINE_CACHE_SECONDS)
    return result


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

    # ---- Base queryset: tasks with dates + optimized prefetch ----
    qs = (
        WbsItem.objects.for_gantt_view()
        .filter(planned_start__isnull=False, planned_end__isnull=False)
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
            "label": get_owner_display_name(user),
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
    min_start = ensure_date(min_start)
    max_end = ensure_date(max_end)

    total_days = days_between(min_start, max_end)

    # Pixels per day (controls horizontal zoom)
    px_per_day = GANTT_PIXELS_PER_DAY
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
        start = ensure_date(t.planned_start)
        end = ensure_date(t.planned_end)

        offset_days = (start - min_start).days
        duration_days = max(1, (end - start).days + 1)

        t.bar_offset = offset_days * px_per_day
        t.bar_width = duration_days * px_per_day

        # Calculate actual dates baseline (if available)
        t.has_actual_dates = False
        t.actual_bar_offset = 0
        t.actual_bar_width = 0
        t.variance_days = 0

        if t.actual_start and t.actual_end:
            actual_start = ensure_date(t.actual_start)
            actual_end = ensure_date(t.actual_end)

            actual_offset_days = (actual_start - min_start).days
            actual_duration_days = max(1, (actual_end - actual_start).days + 1)

            t.has_actual_dates = True
            t.actual_bar_offset = actual_offset_days * px_per_day
            t.actual_bar_width = actual_duration_days * px_per_day
            # Variance: positive = behind schedule, negative = ahead
            t.variance_days = (actual_end - end).days

        # MPPT provides `level`; we use it for indenting in the template
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

    # ---- Calculate critical path ----
    critical_path_codes = calculate_critical_path(tasks)
    for t in tasks:
        t.is_critical_path = t.code in critical_path_codes

    # ---- Calculate resource allocation and conflicts ----
    resource_calendar = calculate_resource_allocation(tasks, min_start, max_end)
    resource_conflicts = identify_resource_conflicts(
        resource_calendar, max_tasks_per_owner=GANTT_RESOURCE_CONFLICT_THRESHOLD
    )

    # ---- Build Year, Month, Day structures for the 3-level timeline (cached) ----
    timeline_bands = compute_timeline_bands(min_start, max_end, px_per_day)

    # Convert resource conflict dates into pixel offsets for frontend
    resource_conflict_positions = []
    resource_conflict_details = []
    try:
        for d in resource_conflicts:
            # d is ISO date string like 'YYYY-MM-DD'
            dt = date.fromisoformat(d)
            offset_days = (dt - min_start).days
            pos_px = offset_days * px_per_day
            resource_conflict_positions.append(pos_px)

            # Build a simple owner summary string for frontend tooltips (Owner:count;Owner2:count)
            owners = resource_calendar.get(d, {}) if isinstance(resource_calendar, dict) else {}
            owner_summary = ", ".join([f"{o}:{c}" for o, c in owners.items()])

            resource_conflict_details.append(
                {
                    "pos_px": pos_px,
                    "date": d,
                    "owner_summary": owner_summary,
                }
            )
    except Exception:
        resource_conflict_positions = []
        resource_conflict_details = []

    context = {
        "tasks": tasks,
        "min_start": min_start,
        "max_end": max_end,
        "total_days": total_days,
        "px_per_day": px_per_day,
        "timeline_width_px": timeline_width_px,
        "year_bands": timeline_bands["year_bands"],
        "month_bands": timeline_bands["month_bands"],
        "day_ticks": timeline_bands["day_ticks"],
        "resource_conflict_positions": resource_conflict_positions,
        "resource_conflict_details": resource_conflict_details,
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
        # Resource leveling
        "resource_conflicts": resource_conflicts,
        "resource_calendar": resource_calendar,
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


@staff_member_required
@require_POST
def update_task_name(request):
    """Update task name via inline editing."""
    import json

    try:
        data = json.loads(request.body)
        code = data.get("code")
        new_name = data.get("name", "").strip()

        if not code or not new_name:
            return JsonResponse({"error": "Code and name required"}, status=400)

        task = WbsItem.objects.filter(code=code).first()
        if not task:
            return JsonResponse({"error": "Task not found"}, status=404)

        task.name = new_name
        task.save(update_fields=["name"])

        return JsonResponse({"ok": True, "name": task.name, "code": task.code})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@staff_member_required
def search_autocomplete(request):
    """
    Provide autocomplete suggestions for Gantt search.
    Returns WBS codes, task names, and owner names matching the query.
    """
    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"suggestions": []})

    suggestions = []
    seen = set()

    # Search WBS codes
    code_matches = WbsItem.objects.filter(code__icontains=query).values_list("code", "name")[:5]
    for code, name in code_matches:
        key = f"code:{code}"
        if key not in seen:
            suggestions.append(
                {
                    "type": "code",
                    "value": code,
                    "label": f"{code} — {name}",
                    "icon": "📋",
                }
            )
            seen.add(key)

    # Search task names
    name_matches = WbsItem.objects.filter(name__icontains=query).values_list("code", "name")[:5]
    for code, name in name_matches:
        key = f"name:{code}"
        if key not in seen:
            suggestions.append(
                {
                    "type": "name",
                    "value": f"{code} {name}",
                    "label": f"{code} — {name}",
                    "icon": "📝",
                }
            )
            seen.add(key)

    # Search owners
    User = get_user_model()
    owner_matches = User.objects.filter(
        models.Q(username__icontains=query)
        | models.Q(first_name__icontains=query)
        | models.Q(last_name__icontains=query)
    )[:5]

    for user in owner_matches:
        display_name = get_owner_display_name(user)
        key = f"owner:{user.id}"
        if key not in seen:
            suggestions.append(
                {
                    "type": "owner",
                    "value": display_name,
                    "label": display_name,
                    "icon": "👤",
                }
            )
            seen.add(key)

    return JsonResponse({"suggestions": suggestions[:10]})


def calculate_critical_path(tasks: List[WbsItem]) -> Set[str]:
    """
    Calculate critical path using forward and backward pass algorithm.

    The critical path is the longest sequence of dependent tasks that determines
    the minimum project duration. Tasks on the critical path have zero slack
    (ES == LS and EF == LF), meaning any delay impacts project completion.

    Algorithm Steps:
    1. Forward Pass: Calculate Earliest Start (ES) and Earliest Finish (EF)
       - Tasks with no predecessors start at their planned_start date
       - Other tasks: ES = max(predecessor EF + lag) for all predecessors
       - EF = ES + duration (in days)

    2. Backward Pass: Calculate Latest Start (LS) and Latest Finish (LF)
       - Tasks with no successors: LF = project end date
       - Other tasks: LF = min(successor LS - lag) for all successors
       - LS = LF - duration

    3. Identify Critical Tasks: Tasks where ES == LS (zero slack)

    Args:
        tasks: List of WbsItem objects with planned dates and dependency links

    Returns:
        Set of task codes (strings) on the critical path

    Note:
        Requires predecessor_links and successor_links to be accessible.
        Tasks must have planned_start and planned_end dates.
    """
    from datetime import timedelta as td

    # Early Start (ES), Early Finish (EF), Late Start (LS), Late Finish (LF)
    # Maps task codes to their calculated dates
    es: Dict[str, date] = {}
    ef: Dict[str, date] = {}
    ls: Dict[str, date] = {}
    lf: Dict[str, date] = {}

    # ========================================================================
    # Forward Pass: Calculate ES (Earliest Start) and EF (Earliest Finish)
    # ========================================================================
    for task in tasks:
        if not task.planned_start or not task.planned_end:
            continue

        # Get all predecessors
        predecessor_links = task.predecessor_links.select_related("predecessor")

        if not predecessor_links.exists():
            # No predecessors - task can start at its planned start date
            es[task.code] = task.planned_start
        else:
            # ES = max(predecessor EF + lag) for all predecessors
            # Find the latest finish date among all predecessors, accounting for lag
            max_ef = task.planned_start
            for link in predecessor_links:
                pred_code = link.predecessor.code
                if pred_code in ef:
                    lag = int(link.lag_days or 0)
                    pred_finish = ef[pred_code] + td(days=lag)
                    if pred_finish > max_ef:
                        max_ef = pred_finish
            es[task.code] = max_ef

        # EF = ES + duration (duration includes start and end day)
        duration = (task.planned_end - task.planned_start).days + 1
        ef[task.code] = es[task.code] + td(days=duration - 1)

    # Find project end date (maximum EF across all tasks)
    if not ef:
        return set()

    project_end = max(ef.values())

    # ========================================================================
    # Backward Pass: Calculate LS (Latest Start) and LF (Latest Finish)
    # Process tasks in reverse to propagate constraints backward
    # ========================================================================
    tasks_reversed = list(reversed(tasks))

    for task in tasks_reversed:
        if task.code not in ef:
            continue

        # Get all successors
        successor_links = task.successor_links.select_related("successor")

        if not successor_links.exists():
            # No successors - task must finish by project end
            lf[task.code] = project_end
        else:
            # LF = min(successor LS - lag) for all successors
            # Find the earliest start among all successors, accounting for lag
            min_ls = project_end
            for link in successor_links:
                succ_code = link.successor.code
                if succ_code in ls:
                    lag = int(link.lag_days or 0)
                    succ_start = ls[succ_code] - td(days=lag)
                    if succ_start < min_ls:
                        min_ls = succ_start
            lf[task.code] = min_ls

        # LS = LF - duration
        duration = (task.planned_end - task.planned_start).days + 1
        ls[task.code] = lf[task.code] - td(days=duration - 1)

    # ========================================================================
    # Identify Critical Path: Tasks with zero slack (ES == LS)
    # ========================================================================
    critical_path: Set[str] = set()

    for task_code in es.keys():
        if task_code in ls:
            es_date = es[task_code]
            ls_date = ls[task_code]

            # Tasks with zero slack are on the critical path
            # (no flexibility in scheduling)
            if es_date == ls_date:
                critical_path.add(task_code)

    return critical_path


def calculate_resource_allocation(
    tasks: List[WbsItem], min_start: date, max_end: date
) -> Dict[str, Dict[str, int]]:
    """
    Calculate daily resource allocation by analyzing task owners.

    Builds a calendar showing how many tasks each owner is assigned to on each day.
    This is used to identify overallocation (resource conflicts) when an owner has
    too many concurrent tasks.

    Args:
        tasks: List of WbsItem objects (requires project_items prefetched)
        min_start: Earliest task start date (datetime.date)
        max_end: Latest task end date (datetime.date)

    Returns:
        Dict mapping date strings to owner allocations:
        {
            "2025-12-01": {"John Smith": 2, "Jane Doe": 1, ...},
            "2025-12-02": {"John Smith": 3, ...},
            ...
        }
        Task counts represent number of concurrent tasks per owner per day.
    """
    from datetime import timedelta as td

    resource_calendar: Dict[str, Dict[str, int]] = {}
    current_date = min_start

    # Initialize calendar: create an entry for each day in the project timeline
    while current_date <= max_end:
        date_str = current_date.isoformat()
        resource_calendar[date_str] = {}
        current_date += td(days=1)

    # For each task, allocate it to owners for each day it's active
    for task in tasks:
        if not task.planned_start or not task.planned_end:
            continue

        start = ensure_date(task.planned_start)
        end = ensure_date(task.planned_end)

        # Get owners from linked ProjectItems
        project_items = list(task.project_items.all())
        owners = set()
        for pi in project_items:
            if pi.owner:
                owner_name = get_owner_display_name(pi.owner)
                owners.add(owner_name)

        # If no owner from ProjectItems, skip this task
        if not owners:
            continue

        # Allocate task to each owner for each day it's active
        for day in range((end - start).days + 1):
            current_date = start + td(days=day)
            date_str = current_date.isoformat()

            if date_str in resource_calendar:
                for owner in owners:
                    resource_calendar[date_str][owner] = (
                        resource_calendar[date_str].get(owner, 0) + 1
                    )

        # Allocate task to each owner for each day
        current = start
        while current <= end:
            date_str = current.isoformat()
            if date_str in resource_calendar:
                for owner in owners:
                    resource_calendar[date_str][owner] = (
                        resource_calendar[date_str].get(owner, 0) + 1
                    )

    return resource_calendar


def identify_resource_conflicts(
    resource_calendar: Dict[str, Dict[str, int]],
    max_tasks_per_owner: int = GANTT_RESOURCE_CONFLICT_THRESHOLD,
) -> List[str]:
    """
    Identify dates where resource allocation exceeds safe capacity.

    A resource conflict occurs when an owner is assigned to more than the
    maximum number of concurrent tasks on a single day. These dates are flagged
    on the Gantt chart for resource planning and load balancing.

    Args:
        resource_calendar: Dict from calculate_resource_allocation()
                          Maps date strings to {owner_name: task_count}
        max_tasks_per_owner: Threshold for conflict detection (default from config).
                            When an owner exceeds this, the day is flagged.

    Returns:
        List of date strings (ISO format) with resource conflicts,
        sorted chronologically and deduplicated.

    Example:
        >>> resource_calendar = {
        ...     "2025-12-01": {"John": 2, "Jane": 1},
        ...     "2025-12-02": {"John": 4},  # John has 4 tasks - exceeds threshold
        ... }
        >>> identify_resource_conflicts(resource_calendar, max_tasks_per_owner=3)
        ["2025-12-02"]
    """
    conflicts: List[str] = []

    # Check each day in the calendar
    for date_str, allocations in resource_calendar.items():
        # Check if any owner exceeds the threshold on this day
        for owner, task_count in allocations.items():
            if task_count > max_tasks_per_owner:
                conflicts.append(date_str)
                break  # Only flag date once, move to next date

    # Return sorted, unique dates
    return sorted(set(conflicts))
