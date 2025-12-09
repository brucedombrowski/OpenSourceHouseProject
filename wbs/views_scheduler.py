import datetime
import json
from typing import Any, Dict, List

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .models import WbsItem
from .performance import profile_view


@profile_view("scheduler_view")
def scheduler_view(request: HttpRequest) -> Any:
    """
    Lightweight scheduling view focused on bulk operations (delete/status/assign).

    Keeps the Gantt chart read-only while providing a dedicated workspace for
    bulk task changes.
    """

    tasks: List[Dict[str, Any]] = []
    qs = (
        WbsItem.objects.for_gantt_view()
        .filter(planned_start__isnull=False, planned_end__isnull=False)
        .select_related("parent")
        .order_by("tree_id", "lft")
    )

    for item in qs:
        status_label = dict(WbsItem.STATUS_CHOICES).get(item.status, item.status)
        tasks.append(
            {
                "code": item.code,
                "name": item.name,
                "planned_start": item.planned_start,
                "planned_end": item.planned_end,
                "status": item.status,
                "status_label": status_label,
                "level": item.level,
                "indent_px": max(0, (item.level - 1) * 14),
            }
        )

    return render(
        request,
        "wbs/scheduler.html",
        {
            "tasks": tasks,
            "status_choices": WbsItem.STATUS_CHOICES,
        },
    )


@csrf_exempt
def scheduler_rebaseline(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = request.json if hasattr(request, "json") else None
        if data is None:
            data = json.loads(request.body.decode())
        codes = data.get("codes", [])
        new_date = data.get("newDate")
        if not codes or not new_date:
            return JsonResponse({"error": "Missing codes or newDate"}, status=400)
        try:
            baseline_date = datetime.datetime.strptime(new_date, "%Y-%m-%d").date()
        except Exception:
            return JsonResponse({"error": "Invalid date format"}, status=400)
        updated = 0
        for item in WbsItem.objects.filter(code__in=codes):
            # Rebaseline logic: set planned_start to new baseline, shift planned_end accordingly
            duration = (
                (item.planned_end - item.planned_start).days
                if item.planned_end and item.planned_start
                else 0
            )
            item.planned_start = baseline_date
            if duration > 0:
                item.planned_end = baseline_date + datetime.timedelta(days=duration)
            item.save(update_fields=["planned_start", "planned_end"])
            updated += 1
        return JsonResponse({"message": f"Rebaselined {updated} task(s) to {baseline_date}"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
