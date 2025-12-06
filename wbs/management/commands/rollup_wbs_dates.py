from django.core.management.base import BaseCommand

from wbs.models import WbsItem


class Command(BaseCommand):
    help = (
        "Roll up planned_start / planned_end (and derived duration_days) from "
        "children to parents for the entire WBS tree."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--include-self",
            action="store_true",
            default=True,
            help=(
                "Included for compatibility; the model method always expects "
                "include_self=True when called from here."
            ),
        )

    def handle(self, *args, **options):
        include_self = True  # we always want the call to report if this node changed

        self.stdout.write(
            "Rolling up planned dates and duration_days for all WBS items (include_self=True)..."
        )

        changed_count = 0

        # Work from roots downward so each subtree is handled once
        roots = WbsItem.objects.filter(parent__isnull=True).order_by("tree_id", "lft")

        if not roots.exists():
            self.stdout.write(self.style.WARNING("No WBS items found."))
            return

        for root in roots:
            if root.update_rollup_dates(include_self=include_self):
                changed_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Rollup complete. {changed_count} WBS item(s) updated.")
        )
