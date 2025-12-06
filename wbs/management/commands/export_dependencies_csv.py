from django.core.management.base import BaseCommand

from wbs.export_utils import (
    DEPENDENCY_EXPORT_FIELDS,
    validate_output_path,
    write_csv,
)
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
        output_path = validate_output_path(options["output_path"])

        qs = TaskDependency.objects.select_related("predecessor", "successor")

        rows = []
        for dep in qs:
            rows.append(
                {
                    "predecessor_code": dep.predecessor.code,
                    "successor_code": dep.successor.code,
                    "dependency_type": dep.dependency_type,
                    "lag_days": dep.lag_days,
                    "notes": dep.notes or "",
                }
            )

        write_csv(output_path, DEPENDENCY_EXPORT_FIELDS, rows)

        self.stdout.write(self.style.SUCCESS(f"Exported dependencies to {output_path}"))
