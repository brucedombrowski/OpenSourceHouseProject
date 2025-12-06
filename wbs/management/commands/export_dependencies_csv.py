import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from wbs.models import TaskDependency


class Command(BaseCommand):
    help = "Export task dependencies to a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "output_path",
            type=str,
            help="Path to output CSV file (e.g. dependencies_export.csv)",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output_path"])

        if output_path.parent and not output_path.parent.exists():
            raise CommandError(f"Directory does not exist: {output_path.parent}")

        fieldnames = [
            "predecessor_code",
            "successor_code",
            "dependency_type",
            "lag_days",
            "notes",
        ]

        qs = TaskDependency.objects.select_related("predecessor", "successor")

        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for dep in qs:
                writer.writerow(
                    {
                        "predecessor_code": dep.predecessor.code,
                        "successor_code": dep.successor.code,
                        "dependency_type": dep.dependency_type,
                        "lag_days": dep.lag_days,
                        "notes": dep.notes or "",
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"Exported dependencies to {output_path}"))
