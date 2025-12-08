# wbs/constants.py
"""
Centralized constants, choices, and enumerations for the WBS app.
Reduces duplication across models, views, and admin.
"""

# WbsItem Status Choices
WBS_STATUS_NOT_STARTED = "not_started"
WBS_STATUS_IN_PROGRESS = "in_progress"
WBS_STATUS_DONE = "done"
WBS_STATUS_BLOCKED = "blocked"

WBS_STATUS_CHOICES = [
    (WBS_STATUS_NOT_STARTED, "Not started"),
    (WBS_STATUS_IN_PROGRESS, "In progress"),
    (WBS_STATUS_DONE, "Done"),
    (WBS_STATUS_BLOCKED, "Blocked"),
]

WBS_STATUS_MAP = {status: label for status, label in WBS_STATUS_CHOICES}

# ProjectItem Type Choices
PROJECT_ITEM_TYPE_ISSUE = "issue"
PROJECT_ITEM_TYPE_TASK = "task"
PROJECT_ITEM_TYPE_ENHANCEMENT = "enhancement"
PROJECT_ITEM_TYPE_RISK = "risk"
PROJECT_ITEM_TYPE_DECISION = "decision"

PROJECT_ITEM_TYPE_CHOICES = [
    (PROJECT_ITEM_TYPE_ISSUE, "Issue"),
    (PROJECT_ITEM_TYPE_TASK, "Task"),
    (PROJECT_ITEM_TYPE_ENHANCEMENT, "Enhancement"),
    (PROJECT_ITEM_TYPE_RISK, "Risk"),
    (PROJECT_ITEM_TYPE_DECISION, "Decision"),
]

PROJECT_ITEM_TYPE_MAP = {typ: label for typ, label in PROJECT_ITEM_TYPE_CHOICES}

# ProjectItem Status Choices
PROJECT_ITEM_STATUS_TODO = "todo"
PROJECT_ITEM_STATUS_IN_PROGRESS = "in_progress"
PROJECT_ITEM_STATUS_BLOCKED = "blocked"
PROJECT_ITEM_STATUS_DONE = "done"
PROJECT_ITEM_STATUS_OPEN = "open"
PROJECT_ITEM_STATUS_CLOSED = "closed"

PROJECT_ITEM_STATUS_CHOICES = [
    (PROJECT_ITEM_STATUS_TODO, "To Do"),
    (PROJECT_ITEM_STATUS_IN_PROGRESS, "In Progress"),
    (PROJECT_ITEM_STATUS_BLOCKED, "Blocked"),
    (PROJECT_ITEM_STATUS_DONE, "Done"),
    (PROJECT_ITEM_STATUS_OPEN, "Open"),
    (PROJECT_ITEM_STATUS_CLOSED, "Closed"),
]

PROJECT_ITEM_STATUS_MAP = {status: label for status, label in PROJECT_ITEM_STATUS_CHOICES}

# ProjectItem Priority Choices
PROJECT_ITEM_PRIORITY_LOW = "low"
PROJECT_ITEM_PRIORITY_MEDIUM = "medium"
PROJECT_ITEM_PRIORITY_HIGH = "high"
PROJECT_ITEM_PRIORITY_CRITICAL = "critical"

PROJECT_ITEM_PRIORITY_CHOICES = [
    (PROJECT_ITEM_PRIORITY_LOW, "Low"),
    (PROJECT_ITEM_PRIORITY_MEDIUM, "Medium"),
    (PROJECT_ITEM_PRIORITY_HIGH, "High"),
    (PROJECT_ITEM_PRIORITY_CRITICAL, "Critical"),
]

PROJECT_ITEM_PRIORITY_MAP = {pri: label for pri, label in PROJECT_ITEM_PRIORITY_CHOICES}

# ProjectItem Severity Choices
PROJECT_ITEM_SEVERITY_LOW = "low"
PROJECT_ITEM_SEVERITY_MEDIUM = "medium"
PROJECT_ITEM_SEVERITY_HIGH = "high"
PROJECT_ITEM_SEVERITY_CRITICAL = "critical"

PROJECT_ITEM_SEVERITY_CHOICES = [
    (PROJECT_ITEM_SEVERITY_LOW, "Low"),
    (PROJECT_ITEM_SEVERITY_MEDIUM, "Medium"),
    (PROJECT_ITEM_SEVERITY_HIGH, "High"),
    (PROJECT_ITEM_SEVERITY_CRITICAL, "Critical"),
]

PROJECT_ITEM_SEVERITY_MAP = {sev: label for sev, label in PROJECT_ITEM_SEVERITY_CHOICES}

# Kanban board status order
KANBAN_STATUS_ORDER = [
    PROJECT_ITEM_STATUS_TODO,
    PROJECT_ITEM_STATUS_IN_PROGRESS,
    PROJECT_ITEM_STATUS_BLOCKED,
    PROJECT_ITEM_STATUS_DONE,
    PROJECT_ITEM_STATUS_OPEN,
    PROJECT_ITEM_STATUS_CLOSED,
]

# Priority ordering for sorting (lower number = higher priority)
PRIORITY_RANK_MAP = {
    PROJECT_ITEM_PRIORITY_CRITICAL: 0,
    PROJECT_ITEM_PRIORITY_HIGH: 1,
    PROJECT_ITEM_PRIORITY_MEDIUM: 2,
    PROJECT_ITEM_PRIORITY_LOW: 3,
}

# ============================================================================
# Gantt Chart Display & Calculation Constants
# ============================================================================

# Timeline rendering
GANTT_PIXELS_PER_DAY = 4  # Default zoom: pixels per day on timeline
GANTT_TIMELINE_CACHE_SECONDS = 3600  # 1 hour cache for year/month/day bands

# Resource allocation and conflict detection
GANTT_RESOURCE_CONFLICT_THRESHOLD = 3  # Maximum concurrent tasks per owner before flagging conflict

# Timeline zoom constraints
GANTT_ZOOM_MIN = 0.5
GANTT_ZOOM_MAX = 3.0
GANTT_ZOOM_STEP = 0.25
GANTT_ZOOM_LOCAL_STORAGE_KEY = "ganttZoom"

# Dependency type color mapping
GANTT_DEPENDENCY_COLORS = {
    "FS": "#42c778",  # Finish-to-Start (green)
    "SS": "#4da3ff",  # Start-to-Start (blue)
    "FF": "#f39c12",  # Finish-to-Finish (orange)
    "SF": "#e56bff",  # Start-to-Finish (purple)
}

# Critical path styling
GANTT_CRITICAL_PATH_COLOR = "#ef4444"  # Red for critical path tasks
GANTT_CRITICAL_PATH_BORDER_COLOR = "#dc2626"

# Layout measurements (CSS-related, in pixels)
GANTT_COL_CODE_WIDTH = 80
GANTT_COL_TASK_WIDTH = 240
GANTT_COL_START_WIDTH = 120
GANTT_COL_END_WIDTH = 120
GANTT_BAR_HEIGHT = 10
GANTT_BAR_HEIGHT_CRITICAL = 14
GANTT_MILESTONE_MARKER_SIZE = 16
GANTT_DETAIL_PANEL_WIDTH = 320
GANTT_ROW_HEIGHT = 28

# Resource conflict visual
GANTT_CONFLICT_MARKER_WIDTH = 16
GANTT_CONFLICT_MARKER_HEIGHT = 8

# Dependency drawing
GANTT_DEPENDENCY_LINE_WIDTH = 2
GANTT_DEPENDENCY_ARROW_SIZE = 8
