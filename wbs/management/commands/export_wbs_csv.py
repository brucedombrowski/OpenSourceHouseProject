import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
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
        output_path = Path(options["output_path"])

        if output_path.parent and not output_path.parent.exists():
            raise CommandError(f"Directory does not exist: {output_path.parent}")

        fieldnames = [
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

        qs = WbsItem.objects.order_by("tree_id", "lft")

        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in qs:
                def d(x):
                    return x.isoformat() if x else ""

                writer.writerow(
                    {
                        "code": item.code,
                        "name": item.name,
                        "parent_code": item.parent.code if item.parent else "",
                        "wbs_level": item.wbs_level,
                        "sequence": item.sequence,
                        "duration_days": item.duration_days or "",
                        "cost_labor": item.cost_labor or "",
                        "cost_material": item.cost_material or "",
                        "planned_start": d(item.planned_start),
                        "planned_end": d(item.planned_end),
                        "actual_start": d(item.actual_start),
                        "actual_end": d(item.actual_end),
                        "status": item.status,
                        "percent_complete": item.percent_complete,
                        "is_milestone": "true" if item.is_milestone else "false",
                        "description": item.description or "",
                        "notes": item.notes or "",
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"Exported WBS to {output_path}"))
