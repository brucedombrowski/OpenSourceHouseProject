"""
Management command to import project items from CSV.

CSV columns:
- title (required)
- description
- type (issue, task, enhancement, risk, decision)
- status (todo, in_progress, blocked, done, open, closed)
- priority (low, medium, high, critical)
- severity (low, medium, high, critical)
- wbs_code (optional; links to WbsItem)
- reported_by
- owner
- estimate_hours
- external_ref

Usage:
    python manage.py import_project_items_csv data/project_items_template.csv
    python manage.py import_project_items_csv data/project_items_template.csv --dry-run
"""

import csv
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from wbs.models import ProjectItem, WbsItem


class Command(BaseCommand):
    help = "Import project items from CSV file."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to CSV file")
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing items (by title + wbs_code)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without saving",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        dry_run = options.get("dry_run", False)
        update = options.get("update", False)
        verbosity = options.get("verbosity", 1)

        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise CommandError("CSV file is empty or unreadable")

                rows = list(reader)
                if not rows:
                    self.stdout.write("No rows found in CSV.")
                    return

                created_count = 0
                updated_count = 0
                skipped_count = 0
                errors = []

                for idx, row in enumerate(rows, start=2):
                    try:
                        title = row.get("title", "").strip()
                        if not title:
                            errors.append(f"Row {idx}: Missing title")
                            continue

                        # Resolve WBS item
                        wbs_item = None
                        wbs_code = row.get("wbs_code", "").strip()
                        if wbs_code:
                            try:
                                wbs_item = WbsItem.objects.get(code=wbs_code)
                            except WbsItem.DoesNotExist:
                                errors.append(f"Row {idx}: WBS code '{wbs_code}' not found")
                                continue

                        # Parse fields
                        item_type = row.get("type", "task").strip().lower()
                        status = row.get("status", "todo").strip().lower()
                        priority = row.get("priority", "medium").strip().lower()
                        severity = row.get("severity", "medium").strip().lower()
                        description = row.get("description", "").strip()
                        reported_by = row.get("reported_by", "").strip()
                        owner = row.get("owner", "").strip()
                        external_ref = row.get("external_ref", "").strip()

                        # Parse estimate_hours
                        estimate_hours = None
                        try:
                            if row.get("estimate_hours", "").strip():
                                estimate_hours = Decimal(row.get("estimate_hours", "0"))
                        except Exception:
                            errors.append(f"Row {idx}: Invalid estimate_hours")
                            continue

                        # Lookup or create
                        if update:
                            item, created = ProjectItem.objects.update_or_create(
                                title=title,
                                wbs_item=wbs_item,
                                defaults={
                                    "description": description,
                                    "type": item_type,
                                    "status": status,
                                    "priority": priority,
                                    "severity": severity,
                                    "reported_by": reported_by,
                                    "owner": owner,
                                    "estimate_hours": estimate_hours,
                                    "external_ref": external_ref,
                                },
                            )
                            if created:
                                created_count += 1
                                if verbosity >= 2:
                                    self.stdout.write(f"Created: {title}")
                            else:
                                updated_count += 1
                                if verbosity >= 2:
                                    self.stdout.write(f"Updated: {title}")
                        else:
                            # Create only (skip if exists)
                            try:
                                ProjectItem.objects.get(title=title, wbs_item=wbs_item)
                                skipped_count += 1
                                if verbosity >= 2:
                                    self.stdout.write(f"Skipped (exists): {title}")
                                continue
                            except ProjectItem.DoesNotExist:
                                pass

                            item = ProjectItem(
                                title=title,
                                description=description,
                                type=item_type,
                                status=status,
                                priority=priority,
                                severity=severity,
                                wbs_item=wbs_item,
                                reported_by=reported_by,
                                owner=owner,
                                estimate_hours=estimate_hours,
                                external_ref=external_ref,
                            )
                            item.save()
                            created_count += 1
                            if verbosity >= 2:
                                self.stdout.write(f"Created: {title}")

                    except Exception as e:
                        errors.append(f"Row {idx}: {str(e)}")

                # Summary
                if dry_run:
                    self.stdout.write(self.style.WARNING("\n[DRY RUN - No changes saved]\n"))

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✓ Import complete:\n"
                        f"  Created: {created_count}\n"
                        f"  Updated: {updated_count}\n"
                        f"  Skipped: {skipped_count}"
                    )
                )

                if errors:
                    self.stdout.write(self.style.ERROR(f"\n✗ {len(errors)} errors found:"))
                    for err in errors[:10]:
                        self.stdout.write(f"  {err}")
                    if len(errors) > 10:
                        self.stdout.write(f"  ... and {len(errors) - 10} more")

        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_file}")
        except Exception as e:
            raise CommandError(f"Import failed: {str(e)}")
