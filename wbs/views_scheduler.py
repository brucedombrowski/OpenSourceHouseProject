from typing import Any, Dict, List

from django.http import HttpRequest
from django.shortcuts import render

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
