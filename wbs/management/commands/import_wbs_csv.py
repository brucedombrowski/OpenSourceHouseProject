import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from wbs.models import WbsItem


def parse_decimal(val, default=None):
    if val is None:
        return default
    s = str(val).strip()
    if not s:
        return default
    try:
        return Decimal(s)
    except InvalidOperation:
        # Bad numeric value in CSV; fall back to default
        return default


def parse_bool(val):
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ("1", "true", "yes", "y")


def parse_date(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    # expects YYYY-MM-DD
    return date.fromisoformat(s)


class Command(BaseCommand):
    help = (
        "Import WBS items from a CSV file. "
        "CSV must have columns: "
        "code,name,parent_code,wbs_level,sequence,"
        "duration_days,cost_labor,cost_material,"
        "planned_start,planned_end,actual_start,actual_end,"
        "status,percent_complete,is_milestone,description,notes"
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to CSV file to import")
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing items (matched by code) instead of skipping",
        )
        parser.add_argument(
            "--skip-rollup",
            action="store_true",
            help="Skip post-import rollup of planned dates/duration.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        update_existing = options["update"]
        skip_rollup = options["skip_rollup"]

        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        code_to_item = {item.code: item for item in WbsItem.objects.all()}

        with csv_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise CommandError("CSV file has no header row.")

            required = {"code", "name"}
            missing = required - set(reader.fieldnames)
            if missing:
                raise CommandError(f"Missing required columns: {', '.join(sorted(missing))}")

            # first pass: create/update items without worrying about parent
            pending_parent_links = []

            for row in reader:
                code = (row.get("code") or "").strip()
                if not code:
                    continue

                name = (row.get("name") or "").strip()
                parent_code = (row.get("parent_code") or "").strip() or None

                wbs_level = int((row.get("wbs_level") or "1").strip())
                sequence = int((row.get("sequence") or "1").strip())

                duration_days = parse_decimal(row.get("duration_days"))
                cost_labor = parse_decimal(row.get("cost_labor"))
                cost_material = parse_decimal(row.get("cost_material"))

                planned_start = parse_date(row.get("planned_start"))
                planned_end = parse_date(row.get("planned_end"))
                actual_start = parse_date(row.get("actual_start"))
                actual_end = parse_date(row.get("actual_end"))

                status = (row.get("status") or "").strip() or WbsItem.STATUS_NOT_STARTED
                percent_complete = parse_decimal(row.get("percent_complete"), default=Decimal("0"))

                is_milestone = parse_bool(row.get("is_milestone"))
                description = (row.get("description") or "").strip()
                notes = (row.get("notes") or "").strip()

                defaults = {
                    "name": name,
                    "wbs_level": wbs_level,
                    "sequence": sequence,
                    "duration_days": duration_days,
                    "cost_labor": cost_labor,
                    "cost_material": cost_material,
                    "planned_start": planned_start,
                    "planned_end": planned_end,
                    "actual_start": actual_start,
                    "actual_end": actual_end,
                    "status": status,
                    "percent_complete": percent_complete,
                    "is_milestone": is_milestone,
                    "description": description,
                    "notes": notes,
                }

                if code in code_to_item:
                    item = code_to_item[code]
                    if update_existing:
                        for field, value in defaults.items():
                            setattr(item, field, value)
                        item.save()
                        self.stdout.write(f"Updated {code} — {name}")
                    else:
                        self.stdout.write(f"Skipped existing {code} — {name}")
                else:
                    item = WbsItem.objects.create(code=code, **defaults)
                    code_to_item[code] = item
                    self.stdout.write(self.style.SUCCESS(f"Created {code} — {name}"))

                if parent_code:
                    pending_parent_links.append((code, parent_code))

        # second pass: set parents (after all codes exist)
        for child_code, parent_code in pending_parent_links:
            child = code_to_item.get(child_code)
            parent = code_to_item.get(parent_code)
            if child and parent:
                child.parent = parent
                # if wbs_level not set manually, we *could* infer from parent, but you already have it in CSV
                child.save()
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Could not set parent for {child_code} -> {parent_code} (missing item)"
                    )
                )

        # rebuild MPTT tree
        WbsItem.objects.rebuild()

        if not skip_rollup:
            changed_count = 0
            roots = WbsItem.objects.filter(parent__isnull=True).order_by("tree_id", "lft")
            for root in roots:
                if root.update_rollup_dates(include_self=True):
                    changed_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Import complete, tree rebuilt, rollup applied ({changed_count} item(s) updated)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("Import complete and tree rebuilt (rollup skipped).")
            )
