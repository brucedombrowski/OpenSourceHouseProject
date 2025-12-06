# wbs/utils.py
"""
Shared utility functions for the WBS app.
Centralizes code that is used across models, views, and admin.
"""

from decimal import Decimal
from typing import List, Dict, Any, Tuple
from django.db.models import Case, When, IntegerField, Q
from .constants import (
    PRIORITY_RANK_MAP,
    PROJECT_ITEM_PRIORITY_CRITICAL,
    PROJECT_ITEM_PRIORITY_HIGH,
    PROJECT_ITEM_PRIORITY_MEDIUM,
    PROJECT_ITEM_PRIORITY_LOW,
)


def normalize_code_for_sort(code: str) -> str:
    """
    Normalize an outline code string for sorting.
    Pads numeric parts to 5 digits for natural ordering.
    
    Example: "1.12.3" -> "00001.00012.00003"
    """
    if not code:
        return ""
    parts = code.split(".")
    normalized_parts = []
    for part in parts:
        try:
            num = int(part)
            normalized_parts.append(f"{num:05d}")
        except ValueError:
            normalized_parts.append(part)
    return ".".join(normalized_parts)


def get_priority_rank_case() -> Case:
    """
    Returns a Django Case/When expression for priority ranking.
    Used to sort ProjectItems by priority in queries.
    
    Returns:
        Case object that maps priority values to numeric ranks
    """
    return Case(
        When(priority=PROJECT_ITEM_PRIORITY_CRITICAL, then=0),
        When(priority=PROJECT_ITEM_PRIORITY_HIGH, then=1),
        When(priority=PROJECT_ITEM_PRIORITY_MEDIUM, then=2),
        When(priority=PROJECT_ITEM_PRIORITY_LOW, then=3),
        default=4,
        output_field=IntegerField(),
    )


def group_items_by_status(
    items: List[Any],
    status_order: List[str],
    status_labels: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Groups items by status and creates column structures for display.
    Useful for Kanban-style layouts.
    
    Args:
        items: QuerySet or list of ProjectItem objects
        status_order: List of statuses in desired order
        status_labels: Dict mapping status code to display label
        
    Returns:
        List of dicts with structure: 
        {status, label, items}
    """
    columns_map = {status: [] for status in status_order}
    
    for item in items:
        columns_map.setdefault(item.status, []).append(item)
    
    columns = [
        {
            "status": status,
            "label": status_labels.get(status, status.replace("_", " ").title()),
            "items": columns_map.get(status, []),
        }
        for status in status_order
    ]
    
    return columns


def calculate_task_duration(start_date, end_date) -> Decimal:
    """
    Calculate duration in days between two dates.
    
    Args:
        start_date: datetime.date object
        end_date: datetime.date object
        
    Returns:
        Decimal number of days (can be fractional)
    """
    if not start_date or not end_date:
        return Decimal("0.00")
    
    delta = end_date - start_date
    return Decimal(str(delta.days))


def is_valid_date_range(start_date, end_date) -> bool:
    """
    Validate that end_date is >= start_date.
    
    Returns:
        True if valid, False otherwise
    """
    if not start_date or not end_date:
        return True  # Allow partial dates
    
    return end_date >= start_date


def merge_filters(*filter_objects) -> Q:
    """
    Merge multiple Django Q objects with OR logic.
    
    Args:
        *filter_objects: Variable number of Q objects
        
    Returns:
        Combined Q object
    """
    if not filter_objects:
        return Q()
    
    result = filter_objects[0]
    for q in filter_objects[1:]:
        result |= q
    
    return result
