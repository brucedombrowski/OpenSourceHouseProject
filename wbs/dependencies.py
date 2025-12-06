from django.db import models
from .models import WbsItem


class TaskDependency(models.Model):
    FS = "FS"
    SS = "SS"
    FF = "FF"
    SF = "SF"

    DEP_TYPES = [
        (FS, "Finish to Start"),
        (SS, "Start to Start"),
        (FF, "Finish to Finish"),
        (SF, "Start to Finish"),
    ]

    predecessor = models.ForeignKey(
        WbsItem, related_name="successor_links", on_delete=models.CASCADE
    )
    successor = models.ForeignKey(
        WbsItem, related_name="predecessor_links", on_delete=models.CASCADE
    )

    dependency_type = models.CharField(max_length=2, choices=DEP_TYPES, default=FS)

    lag_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("predecessor", "successor")

    def __str__(self):
        return f"{self.predecessor.code} → {self.successor.code} ({self.dependency_type}, {self.lag_days}d)"
