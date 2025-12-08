import csv
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from wbs.models import ProjectItem, TaskDependency, WbsItem


class Command(BaseCommand):
    help = "Load comprehensive test data (WBS, dependencies, project items) from CSV templates"

    def handle(self, *args, **options):
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"

        # Get or create admin user with known credentials for testing
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@test.com",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        # Ensure password is set so testers can log in
        if created or not admin_user.has_usable_password():
            admin_user.set_password("admin123")
            admin_user.save(update_fields=["password"])
            self.stdout.write(self.style.WARNING("Admin password reset to admin123 for testing."))

        # Load WBS items from template
        wbs_file = data_dir / "wbs_items_template.csv"
        self.stdout.write(f"Loading WBS items from {wbs_file}...")
        wbs_count = 0
        with wbs_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get("code", "").strip()
                if not code:
                    continue

                item, created = WbsItem.objects.get_or_create(
                    code=code,
                    defaults={
                        "name": row.get("name", code),
                        "planned_start": row.get("planned_start") or None,
                        "planned_end": row.get("planned_end") or None,
                    },
                )
                if created:
                    wbs_count += 1
        self.stdout.write(self.style.SUCCESS(f"  Created {wbs_count} WBS items"))

        # Load ProjectItems from template
        proj_file = data_dir / "project_items_template.csv"
        self.stdout.write(f"Loading ProjectItems from {proj_file}...")
        proj_count = 0
        skipped = 0
        with proj_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("title", "").strip()
                if not title:
                    continue

                wbs_code = row.get("wbs_code", "").strip()
                wbs_item = None
                if wbs_code:
                    try:
                        wbs_item = WbsItem.objects.get(code=wbs_code)
                    except WbsItem.DoesNotExist:
                        skipped += 1
                        continue

                proj_item, created = ProjectItem.objects.get_or_create(
                    title=title,
                    defaults={
                        "wbs_item": wbs_item,
                        "description": row.get("description", ""),
                        "type": row.get("type", "task"),
                        "status": row.get("status", "todo"),
                        "priority": row.get("priority", "medium"),
                        "severity": row.get("severity", "low"),
                        "owner": admin_user,
                    },
                )
                if created:
                    proj_count += 1
        self.stdout.write(
            self.style.SUCCESS(f"  Created {proj_count} ProjectItems (skipped {skipped})")
        )

        # Load Dependencies from template
        deps_file = data_dir / "wbs_dependencies_template.csv"
        self.stdout.write(f"Loading dependencies from {deps_file}...")
        dep_count = 0
        with deps_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pred_code = (row.get("predecessor_code") or "").strip()
                succ_code = (row.get("successor_code") or "").strip()
                if not pred_code or not succ_code:
                    continue

                dep_type = (row.get("dependency_type") or "FS").strip().upper() or "FS"
                lag_days = row.get("lag_days") or 0

                try:
                    predecessor = WbsItem.objects.get(code=pred_code)
                    successor = WbsItem.objects.get(code=succ_code)
                except WbsItem.DoesNotExist:
                    skipped += 1
                    continue

                obj, created_dep = TaskDependency.objects.get_or_create(
                    predecessor=predecessor,
                    successor=successor,
                    defaults={"dependency_type": dep_type, "lag": lag_days},
                )
                if created_dep:
                    dep_count += 1

        self.stdout.write(self.style.SUCCESS(f"  Created {dep_count} dependencies"))

        total_projects = ProjectItem.objects.count()
        total_wbs = WbsItem.objects.count()
        self.stdout.write(self.style.SUCCESS(f"\n✅ Total ProjectItems in DB: {total_projects}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Total WbsItems in DB: {total_wbs}"))
