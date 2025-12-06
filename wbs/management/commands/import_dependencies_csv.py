import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from wbs.models import TaskDependency, WbsItem


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
        parser.add_argument(
            "csv_path",
            type=str,
            nargs="?",
            help="Path to CSV file to import (optional if --minimal)",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing dependency entries instead of skipping (matched by predecessor+successor)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the CSV without writing to the database",
        )
        parser.add_argument(
            "--minimal",
            action="store_true",
            help="Use minimal fixture (quick testing). Ignores csv_path.",
        )

    def handle(self, *args, **options):
        csv_path_arg = options["csv_path"]
        use_minimal = options.get("minimal", False)
        update_existing = options["update"]
        dry_run = options["dry_run"]

        # Resolve CSV path
        if use_minimal:
            csv_path = (
                Path(__file__).parent.parent.parent.parent / "data" / "wbs_dependencies_minimal.csv"
            )
            self.stdout.write(self.style.SUCCESS(f"Using minimal fixture: {csv_path}"))
        else:
            if not csv_path_arg:
                raise CommandError("csv_path required unless --minimal is used")
            csv_path = Path(csv_path_arg)

        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        code_to_item = {item.code: item for item in WbsItem.objects.all()}
        errors = []
        parsed_rows = []
        seen_pairs = set()

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
                    errors.append("Missing predecessor_code or successor_code")
                    continue

                dep_type = (row.get("dependency_type") or "FS").strip().upper() or "FS"
                allowed_types = {choice[0] for choice in TaskDependency.DEPENDENCY_TYPES}
                if dep_type not in allowed_types:
                    errors.append(
                        f"Invalid dependency type '{dep_type}' for {pred_code} -> {succ_code}"
                    )
                    continue

                key = (pred_code, succ_code)
                if key in seen_pairs:
                    errors.append(
                        f"Duplicate dependency {pred_code} -> {succ_code} in file (unique pair required)"
                    )
                    continue
                seen_pairs.add(key)

                if pred_code == succ_code:
                    errors.append(f"Self-dependency for {pred_code} not allowed")
                    continue

                try:
                    lag_days = parse_decimal(row.get("lag_days"))
                except Exception:
                    errors.append(
                        f"Invalid lag_days for {pred_code} -> {succ_code}: {row.get('lag_days')}"
                    )
                    continue

                notes = (row.get("notes") or "").strip()

                parsed_rows.append(
                    {
                        "pred_code": pred_code,
                        "succ_code": succ_code,
                        "dep_type": dep_type,
                        "lag_days": lag_days,
                        "notes": notes,
                    }
                )

        # Validate referenced tasks exist
        for parsed in parsed_rows:
            if parsed["pred_code"] not in code_to_item:
                errors.append(f"Unknown predecessor_code: {parsed['pred_code']}")
            if parsed["succ_code"] not in code_to_item:
                errors.append(f"Unknown successor_code: {parsed['succ_code']}")

        if errors:
            summary = "\n".join(errors)
            raise CommandError(f"Validation failed with {len(errors)} error(s):\n{summary}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run OK: {len(parsed_rows)} rows validated."))
            return

        for parsed in parsed_rows:
            pred_code = parsed["pred_code"]
            succ_code = parsed["succ_code"]
            dep_type = parsed["dep_type"]
            lag_days = parsed["lag_days"]
            notes = parsed["notes"]

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
                    self.stdout.write(f"Updated dependency {pred_code} -> {succ_code}")
                else:
                    self.stdout.write(f"Skipping existing dependency {pred_code} -> {succ_code}")
            except TaskDependency.DoesNotExist:
                TaskDependency.objects.create(
                    predecessor=predecessor, successor=successor, **defaults
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Created dependency {pred_code} -> {succ_code}")
                )

        self.stdout.write(self.style.SUCCESS("Dependency import complete."))
