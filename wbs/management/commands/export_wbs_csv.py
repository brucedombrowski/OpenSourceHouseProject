from django.core.management.base import BaseCommand

from wbs.export_utils import (
    WBS_EXPORT_FIELDS,
    format_date,
    validate_output_path,
    write_csv,
)
from wbs.models import WbsItem


class Command(BaseCommand):
    help = "Export WBS items to a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "output_path",
            type=str,
            help="Path to output CSV file (e.g. wbs_export.csv)",
        )

    def handle(self, *args, **options):
        output_path = validate_output_path(options["output_path"])

        qs = WbsItem.objects.order_by("tree_id", "lft")

        rows = []
        for item in qs:
            rows.append(
                {
                    "code": item.code,
                    "name": item.name,
                    "parent_code": item.parent.code if item.parent else "",
                    "wbs_level": item.wbs_level,
                    "sequence": item.sequence,
                    "duration_days": item.duration_days or "",
                    "cost_labor": item.cost_labor or "",
                    "cost_material": item.cost_material or "",
                    "planned_start": format_date(item.planned_start),
                    "planned_end": format_date(item.planned_end),
                    "actual_start": format_date(item.actual_start),
                    "actual_end": format_date(item.actual_end),
                    "status": item.status,
                    "percent_complete": item.percent_complete,
                    "is_milestone": "true" if item.is_milestone else "false",
                    "description": item.description or "",
                    "notes": item.notes or "",
                }
            )

        write_csv(output_path, WBS_EXPORT_FIELDS, rows)

        self.stdout.write(self.style.SUCCESS(f"Exported WBS to {output_path}"))
