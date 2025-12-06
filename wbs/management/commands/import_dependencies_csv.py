import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from wbs.models import WbsItem, TaskDependency


def parse_decimal(val):
    if val is None:
        return Decimal("0")
    s = str(val).strip()
    if not s:
        return Decimal("0")
    return Decimal(s)


class Command(BaseCommand):
    help = (
        "Import task dependencies from CSV. "
        "CSV must have columns: "
        "predecessor_code,successor_code,dependency_type,lag_days,notes"
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to CSV file to import")
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing dependency entries instead of skipping (matched by predecessor+successor)",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        update_existing = options["update"]

        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        code_to_item = {item.code: item for item in WbsItem.objects.all()}

        with csv_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise CommandError("CSV has no header row.")

            required = {"predecessor_code", "successor_code"}
            missing = required - set(reader.fieldnames)
            if missing:
                raise CommandError(f"Missing required columns: {', '.join(sorted(missing))}")

            for row in reader:
                pred_code = (row.get("predecessor_code") or "").strip()
                succ_code = (row.get("successor_code") or "").strip()
                if not pred_code or not succ_code:
                    continue

                dep_type = (row.get("dependency_type") or "FS").strip() or "FS"
                lag_days = parse_decimal(row.get("lag_days"))
                notes = (row.get("notes") or "").strip()

                predecessor = code_to_item.get(pred_code)
                successor = code_to_item.get(succ_code)

                if not predecessor or not successor:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping dependency {pred_code} -> {succ_code} (missing task)"
                        )
                    )
                    continue

                defaults = {
                    "dependency_type": dep_type,
                    "lag_days": lag_days,
                    "notes": notes,
                }

                try:
                    dep = TaskDependency.objects.get(
                        predecessor=predecessor,
                        successor=successor,
                    )
                    if update_existing:
                        for field, value in defaults.items():
                            setattr(dep, field, value)
                        dep.save()
                        self.stdout.write(
                            f"Updated dependency {pred_code} -> {succ_code}"
                        )
                    else:
                        self.stdout.write(
                            f"Skipping existing dependency {pred_code} -> {succ_code}"
                        )
                except TaskDependency.DoesNotExist:
                    TaskDependency.objects.create(
                        predecessor=predecessor, successor=successor, **defaults
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created dependency {pred_code} -> {succ_code}"
                        )
                    )

        self.stdout.write(self.style.SUCCESS("Dependency import complete."))
