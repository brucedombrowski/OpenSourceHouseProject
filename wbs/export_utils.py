# wbs/export_utils.py
"""
Shared utilities for CSV export commands.
Centralizes validation, date formatting, and CSV writing logic.
"""

import csv
from pathlib import Path

from django.core.management import CommandError


def validate_output_path(output_path_str):
    """
    Validate that the output directory exists.

    Args:
        output_path_str (str): Path to output file

    Returns:
        Path: Validated pathlib.Path object

    Raises:
        CommandError: If parent directory doesn't exist
    """
    output_path = Path(output_path_str)

    if output_path.parent and not output_path.parent.exists():
        raise CommandError(f"Directory does not exist: {output_path.parent}")

    return output_path


def format_date(date_obj):
    """
    Format date object to ISO string, or empty string if None.

    Args:
        date_obj: Date/datetime object or None

    Returns:
        str: ISO formatted date string or empty string
    """
    return date_obj.isoformat() if date_obj else ""


def write_csv(output_path, fieldnames, rows, encoding="utf-8"):
    """
    Write rows to CSV file with standard formatting.

    Args:
        output_path (Path): Output file path
        fieldnames (list): CSV header field names
        rows (list): List of dicts with row data
        encoding (str): File encoding (default: utf-8)
    """
    with output_path.open("w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_success_message(output_path):
    """Return a standard success message for exports."""
    return f"Export complete: {output_path}"


# Standardized field mappings for common exports
WBS_EXPORT_FIELDS = [
    "code",
    "name",
    "parent_code",
    "wbs_level",
    "sequence",
    "duration_days",
    "cost_labor",
    "cost_material",
    "planned_start",
    "planned_end",
    "actual_start",
    "actual_end",
    "status",
    "percent_complete",
    "is_milestone",
    "description",
    "notes",
]

DEPENDENCY_EXPORT_FIELDS = [
    "predecessor_code",
    "successor_code",
    "dependency_type",
    "lag_days",
    "notes",
]
