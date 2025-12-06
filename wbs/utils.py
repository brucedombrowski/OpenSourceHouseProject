# wbs/utils.py
"""
Shared utility functions for the WBS app.
Centralizes code that is used across models, views, and admin.
"""

import re
from decimal import Decimal
from typing import List, Dict, Any, Tuple, Optional
from django.db.models import Case, When, IntegerField, Q
from .constants import (
    PRIORITY_RANK_MAP,
    PROJECT_ITEM_PRIORITY_CRITICAL,
    PROJECT_ITEM_PRIORITY_HIGH,
    PROJECT_ITEM_PRIORITY_MEDIUM,
    PROJECT_ITEM_PRIORITY_LOW,
)


def normalize_code_for_sort(code: str, pad_width: int = 5) -> str:
    """
    Normalize an outline code string for sorting.
    Pads numeric parts to `pad_width` digits for natural ordering.
    
    Uses regex to identify and pad numeric groups.
    Example: "1.12.3" -> "00001.00012.00003" (with pad_width=5)
    
    Args:
        code: The code string to normalize (e.g., "1.2.3")
        pad_width: Number of digits to pad numeric groups (default 5)
        
    Returns:
        Normalized code string with padded numeric groups
    """
    if not code:
        return ""
    
    def pad_numeric(match):
        num_str = match.group(0)
        try:
            num = int(num_str)
            return f"{num:0{pad_width}d}"
        except ValueError:
            return num_str
    
    # Replace all numeric sequences with padded versions
    return re.sub(r'\d+', pad_numeric, code)


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


def group_items_by_wbs(
    items: List[Any],
) -> List[Tuple[Tuple[Optional[int], str], List[Any]]]:
    """
    Groups ProjectItems by their linked WBS item.
    Unlinked items are grouped under (None, "Unlinked Items").
    
    Args:
        items: QuerySet or list of ProjectItem objects (assumed to have wbs_item FK)
        
    Returns:
        List of tuples: ((wbs_id, wbs_label), items)
        Sorted with linked items first (by WBS sort_key), unlinked last.
        
    Example:
        >>> items = ProjectItem.objects.select_related('wbs_item')
        >>> groups = group_items_by_wbs(items)
        >>> for (wbs_id, label), item_list in groups:
        ...     print(f"{label}: {len(item_list)} items")
    """
    wbs_groups = {}
    
    for item in items:
        wbs_key = (
            (item.wbs_item.id, f"{item.wbs_item.code} — {item.wbs_item.name}")
            if item.wbs_item
            else (None, "Unlinked Items")
        )
        if wbs_key not in wbs_groups:
            wbs_groups[wbs_key] = []
        wbs_groups[wbs_key].append(item)
    
    # Sort: linked items first (by wbs_id), unlinked last
    sorted_groups = sorted(
        wbs_groups.items(),
        key=lambda x: (x[0][0] is None, x[0][0] or ""),
    )
    
    return sorted_groups
    """
    Calculate duration in days between two dates.
    
    By default, returns inclusive duration (e.g., Jan 1 to Jan 1 = 1 day).
    This aligns with rollup semantics where start and end date both count.
    
    Args:
        start_date: datetime.date object or None
        end_date: datetime.date object or None
        inclusive: If True (default), add 1 to the day count for inclusive range
        
    Returns:
        Decimal number of days (rounded to 2 decimal places)
    """
    if not start_date or not end_date:
        return Decimal("0.00")
    
    delta = end_date - start_date
    days = Decimal(str(delta.days))
    
    if inclusive:
        days += Decimal("1")
    
    return days.quantize(Decimal("0.01"))


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
