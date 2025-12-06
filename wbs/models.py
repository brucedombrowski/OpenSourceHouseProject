# wbs/models.py

from decimal import Decimal

from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from .constants import (
    WBS_STATUS_NOT_STARTED,
    WBS_STATUS_IN_PROGRESS,
    WBS_STATUS_DONE,
    WBS_STATUS_BLOCKED,
    WBS_STATUS_CHOICES,
    PROJECT_ITEM_TYPE_ISSUE,
    PROJECT_ITEM_TYPE_TASK,
    PROJECT_ITEM_TYPE_ENHANCEMENT,
    PROJECT_ITEM_TYPE_RISK,
    PROJECT_ITEM_TYPE_DECISION,
    PROJECT_ITEM_TYPE_CHOICES,
    PROJECT_ITEM_STATUS_TODO,
    PROJECT_ITEM_STATUS_IN_PROGRESS,
    PROJECT_ITEM_STATUS_BLOCKED,
    PROJECT_ITEM_STATUS_DONE,
    PROJECT_ITEM_STATUS_OPEN,
    PROJECT_ITEM_STATUS_CLOSED,
    PROJECT_ITEM_STATUS_CHOICES,
    PROJECT_ITEM_PRIORITY_LOW,
    PROJECT_ITEM_PRIORITY_MEDIUM,
    PROJECT_ITEM_PRIORITY_HIGH,
    PROJECT_ITEM_PRIORITY_CRITICAL,
    PROJECT_ITEM_PRIORITY_CHOICES,
    PROJECT_ITEM_SEVERITY_LOW,
    PROJECT_ITEM_SEVERITY_MEDIUM,
    PROJECT_ITEM_SEVERITY_HIGH,
    PROJECT_ITEM_SEVERITY_CRITICAL,
    PROJECT_ITEM_SEVERITY_CHOICES,
)
from .utils import normalize_code_for_sort


class WbsItem(MPTTModel):
    """
    Core WBS node for the house project.
    Supports hierarchy (via MPPT), scheduling, and progress tracking.
    """

    # --- Status choices (for high-level progress) ---
    STATUS_NOT_STARTED = WBS_STATUS_NOT_STARTED
    STATUS_IN_PROGRESS = WBS_STATUS_IN_PROGRESS
    STATUS_DONE = WBS_STATUS_DONE
    STATUS_BLOCKED = WBS_STATUS_BLOCKED

    STATUS_CHOICES = WBS_STATUS_CHOICES

    # --- Identity / hierarchy ---
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    parent = TreeForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )

    wbs_level = models.PositiveIntegerField(default=1)
    sequence = models.PositiveIntegerField(default=1)
    sort_key = models.CharField(max_length=255, editable=False, default="")

    # --- Planning ---
    duration_days = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    cost_labor = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    cost_material = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    # --- Schedule ---
    planned_start = models.DateField(null=True, blank=True)
    planned_end = models.DateField(null=True, blank=True)
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)

    # --- Progress ---
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NOT_STARTED,
    )
    percent_complete = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00")
    )

    is_milestone = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class MPTTMeta:
        # Default insertion order in the tree (numeric-friendly via sort_key)
        order_insertion_by = ["sort_key"]

    class Meta:
        # Default queryset ordering (admin overrides with sort_key)
        ordering = ["sort_key"]
        verbose_name = "WBS Item"
        verbose_name_plural = "WBS Items"

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

    # --- Core hooks / helpers ---

    def save(self, *args, **kwargs):
        """
        Keep sort_key in sync with code so admin ordering is natural numeric.
        """
        if self.code:
            self.sort_key = normalize_code_for_sort(self.code)
        super().save(*args, **kwargs)

    # --- Rollup: dates ---

    def update_rollup_dates(self, include_self: bool = False) -> bool:
        """
        Roll up planned_start / planned_end from children to this node.

        Returns True if this node's dates changed as a result of the rollup.
        Called recursively from roots downward.

        NOTE: Signature is compatible with rollup_wbs_dates management command:
              item.update_rollup_dates(include_self=True)
        """
        changed = False
        children = self.get_children()

        if children.exists():
            min_start = None
            max_end = None

            for child in children:
                # Recurse first so grandchildren are up to date
                if child.update_rollup_dates(include_self=True):
                    changed = True

                if child.planned_start:
                    min_start = (
                        child.planned_start
                        if min_start is None
                        else min(min_start, child.planned_start)
                    )
                if child.planned_end:
                    max_end = (
                        child.planned_end
                        if max_end is None
                        else max(max_end, child.planned_end)
                    )

            if min_start != self.planned_start or max_end != self.planned_end:
                self.planned_start = min_start
                self.planned_end = max_end
                self.save(update_fields=["planned_start", "planned_end"])
                changed = True

        return changed if include_self else False

    # --- Rollup: percent_complete ---

    def update_rollup_progress(self, include_self: bool = False) -> bool:
        """
        Roll up percent_complete from children to this node.

        - If a node has children: its percent_complete becomes the
          duration-weighted average of its direct children.
        - Leaves keep their own percent_complete values.

        Returns True if this node's percent_complete changed.
        Compatible with rollup_progress management command:
            root.update_rollup_progress(include_self=True)
        """
        changed = False
        children = self.get_children()

        # First recurse so children/grandchildren are up to date
        for child in children:
            if child.update_rollup_progress(include_self=True):
                changed = True

        if children.exists():
            total_weight = Decimal("0")
            weighted_sum = Decimal("0")

            for child in children:
                # Use duration_days as weight; fall back to 1 if missing/zero
                dur = child.duration_days
                try:
                    weight = Decimal(dur) if dur not in (None, 0, Decimal("0")) else Decimal("1")
                except Exception:
                    weight = Decimal("1")

                pct = child.percent_complete or Decimal("0")
                total_weight += weight
                weighted_sum += pct * weight

            if total_weight > 0:
                new_pct = (weighted_sum / total_weight).quantize(Decimal("0.01"))
            else:
                new_pct = self.percent_complete or Decimal("0")

            if new_pct != (self.percent_complete or Decimal("0")):
                self.percent_complete = new_pct
                self.save(update_fields=["percent_complete"])
                changed = True

        return changed if include_self else False


class TaskDependency(models.Model):
    """
    Logical relationships between WBS items (FS/SS/FF/SF with lag).
    """

    FS = "FS"
    SS = "SS"
    FF = "FF"
    SF = "SF"

    DEPENDENCY_TYPES = [
        (FS, "Finish to Start"),
        (SS, "Start to Start"),
        (FF, "Finish to Finish"),
        (SF, "Start to Finish"),
    ]

    predecessor = models.ForeignKey(
        WbsItem,
        related_name="successor_links",
        on_delete=models.CASCADE,
    )

    successor = models.ForeignKey(
        WbsItem,
        related_name="predecessor_links",
        on_delete=models.CASCADE,
    )

    dependency_type = models.CharField(
        max_length=2,
        choices=DEPENDENCY_TYPES,
        default=FS,
    )

    lag_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Lag in days (negative for lead).",
    )

    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("predecessor", "successor")
        verbose_name = "Task Dependency"
        verbose_name_plural = "Task Dependencies"

    def __str__(self) -> str:
        return (
            f"{self.predecessor.code} → {self.successor.code} "
            f"({self.dependency_type}, {self.lag_days}d)"
        )


class ProjectItem(models.Model):
    """
    Unified project item (issue / task / enhancement / risk / decision),
    optionally linked to a WBS item.
    """

    # Types
    TYPE_ISSUE = PROJECT_ITEM_TYPE_ISSUE
    TYPE_TASK = PROJECT_ITEM_TYPE_TASK
    TYPE_ENHANCEMENT = PROJECT_ITEM_TYPE_ENHANCEMENT
    TYPE_RISK = PROJECT_ITEM_TYPE_RISK
    TYPE_DECISION = PROJECT_ITEM_TYPE_DECISION

    TYPE_CHOICES = PROJECT_ITEM_TYPE_CHOICES

    # Statuses
    STATUS_TODO = PROJECT_ITEM_STATUS_TODO
    STATUS_IN_PROGRESS = PROJECT_ITEM_STATUS_IN_PROGRESS
    STATUS_BLOCKED = PROJECT_ITEM_STATUS_BLOCKED
    STATUS_DONE = PROJECT_ITEM_STATUS_DONE
    STATUS_OPEN = PROJECT_ITEM_STATUS_OPEN
    STATUS_CLOSED = PROJECT_ITEM_STATUS_CLOSED

    STATUS_CHOICES = PROJECT_ITEM_STATUS_CHOICES

    # Priority
    PRIORITY_LOW = PROJECT_ITEM_PRIORITY_LOW
    PRIORITY_MEDIUM = PROJECT_ITEM_PRIORITY_MEDIUM
    PRIORITY_HIGH = PROJECT_ITEM_PRIORITY_HIGH
    PRIORITY_CRITICAL = PROJECT_ITEM_PRIORITY_CRITICAL

    PRIORITY_CHOICES = PROJECT_ITEM_PRIORITY_CHOICES

    # Severity (mostly for issues/bugs)
    SEVERITY_LOW = PROJECT_ITEM_SEVERITY_LOW
    SEVERITY_MEDIUM = PROJECT_ITEM_SEVERITY_MEDIUM
    SEVERITY_HIGH = PROJECT_ITEM_SEVERITY_HIGH
    SEVERITY_CRITICAL = PROJECT_ITEM_SEVERITY_CRITICAL

    SEVERITY_CHOICES = PROJECT_ITEM_SEVERITY_CHOICES

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_TASK,
    )

    wbs_item = models.ForeignKey(
        WbsItem,
        null=True,
        blank=True,
        related_name="project_items",
        on_delete=models.SET_NULL,
        help_text="Optional: link this item to a specific WBS node.",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_TODO,
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_MEDIUM,
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_MEDIUM,
    )

    reported_by = models.CharField(max_length=100, blank=True)
    owner = models.CharField(max_length=100, blank=True)

    date_started = models.DateTimeField(null=True, blank=True)
    date_completed = models.DateTimeField(null=True, blank=True)

    estimate_hours = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    actual_hours = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )

    external_ref = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional external ID (e.g. Jira, GitHub, etc.)",
    )

    tags = models.CharField(
        max_length=200, blank=True, help_text="Comma-separated tags."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Project Item"
        verbose_name_plural = "Project Items"

    def __str__(self) -> str:
        prefix = f"[{self.wbs_item.code}] " if self.wbs_item else ""
        return f"{prefix}{self.title}"
