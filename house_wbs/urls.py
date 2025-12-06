from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path

from wbs.views import (
    gantt_optimize_schedule,
    gantt_set_task_dates,
    gantt_shift_task,
    gantt_view,
    project_item_board,
    project_item_list,
    project_item_status_update,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("gantt/", gantt_view, name="gantt_view"),
    path("gantt/", gantt_view, name="gantt"),  # alias for admin links
    path("gantt/shift/", gantt_shift_task, name="gantt_shift_task"),
    path("gantt/set-dates/", gantt_set_task_dates, name="gantt_set_task_dates"),
    path("gantt/optimize/", gantt_optimize_schedule, name="gantt_optimize_schedule"),
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
