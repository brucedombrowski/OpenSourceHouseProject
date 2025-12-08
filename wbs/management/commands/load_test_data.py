import csv

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from wbs.models import ProjectItem, WbsItem


class Command(BaseCommand):
    help = "Load test data from CSV files"

    def handle(self, *args, **options):
        # Get or create admin user
        admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@test.com", "is_staff": True, "is_superuser": True},
        )

        # Load WBS items from template
        wbs_file = "/app/data/wbs_items_template.csv"
        self.stdout.write(f"Loading WBS items from {wbs_file}...")
        wbs_count = 0
        with open(wbs_file, "r") as f:
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
        proj_file = "/app/data/project_items_template.csv"
        self.stdout.write(f"Loading ProjectItems from {proj_file}...")
        proj_count = 0
        skipped = 0
        with open(proj_file, "r") as f:
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

        total_projects = ProjectItem.objects.count()
        total_wbs = WbsItem.objects.count()
        self.stdout.write(self.style.SUCCESS(f"\n✅ Total ProjectItems in DB: {total_projects}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Total WbsItems in DB: {total_wbs}"))
