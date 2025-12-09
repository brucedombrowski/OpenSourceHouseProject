from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path

from wbs.views import (
    gantt_bulk_assign,
    gantt_bulk_delete,
    gantt_bulk_update_status,
    gantt_optimize_schedule,
    gantt_set_task_dates,
    gantt_shift_task,
    gantt_view,
    index,
    project_item_board,
    project_item_list,
    project_item_status_update,
    scheduler_view,
)
from wbs.views_gantt import search_autocomplete, update_task_name
from wbs.views_health import health_check, health_check_detailed, readiness_check
from wbs.views_scheduler import scheduler_rebaseline

urlpatterns = [
    path("", index, name="index"),
    path("admin/", admin.site.urls),
    # Health check endpoints (no authentication required)
    path("health/", health_check, name="health_check"),
    path("health/detailed/", health_check_detailed, name="health_check_detailed"),
    path("readiness/", readiness_check, name="readiness_check"),
    # Gantt chart endpoints
    path("gantt/", gantt_view, name="gantt_view"),
    path("gantt/", gantt_view, name="gantt"),  # alias for admin links
    path("gantt/shift/", gantt_shift_task, name="gantt_shift_task"),
    path("gantt/set-dates/", gantt_set_task_dates, name="gantt_set_task_dates"),
    path("gantt/optimize/", gantt_optimize_schedule, name="gantt_optimize_schedule"),
    path("gantt/bulk-delete/", gantt_bulk_delete, name="gantt_bulk_delete"),
    path("gantt/bulk-assign/", gantt_bulk_assign, name="gantt_bulk_assign"),
    path("gantt/bulk-update-status/", gantt_bulk_update_status, name="gantt_bulk_update_status"),
    path("gantt/update-name/", update_task_name, name="update_task_name"),
    path("gantt/search/", search_autocomplete, name="search_autocomplete"),
    path("scheduler/", scheduler_view, name="scheduler_view"),
    path("scheduler/rebaseline/", scheduler_rebaseline, name="scheduler_rebaseline"),
    # Project items endpoints
    path("project-items/board/", project_item_board, name="project_item_board"),
    path("project-items/list/", project_item_list, name="project_item_list"),
    path(
        "project-items/status/",
        project_item_status_update,
        name="project_item_status_update",
    ),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
