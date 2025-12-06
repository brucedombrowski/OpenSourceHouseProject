from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from wbs.models import WbsItem


class Command(BaseCommand):
    help = (
        "Auto-populate planned_start and planned_end for all WBS items "
        "based on duration_days, walking the WBS tree in sequence order."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--start-date",
            type=str,
            default=None,
            help="Project start date in YYYY-MM-DD format (default: today).",
        )

    def handle(self, *args, **options):
        start_date_str = options.get("start_date")

        if start_date_str:
            try:
                project_start = date.fromisoformat(start_date_str)
            except ValueError:
                raise CommandError(f"Invalid --start-date '{start_date_str}'. Use YYYY-MM-DD.")
        else:
            project_start = date.today()

        self.stdout.write(f"Scheduling WBS starting at {project_start.isoformat()}")

        # Get root nodes (no parent), ordered
        roots = WbsItem.objects.filter(parent__isnull=True).order_by("sequence", "code")

        current_date = project_start

        for root in roots:
            current_date = self._schedule_node(root, current_date)

        self.stdout.write(self.style.SUCCESS("Auto-scheduling complete."))

    def _schedule_node(self, node, start_date):
        """
        Schedule this node, then its children sequentially after it.
        Returns the next available date after this subtree.
        """
        # Default 1 day if no duration set
        dur = node.duration_days
        try:
            days = int(dur) if dur is not None else 1
        except (TypeError, ValueError):
            days = 1

        if days < 1:
            days = 1

        node.planned_start = start_date
        node.planned_end = start_date + timedelta(days=days - 1)
        node.save()

        self.stdout.write(
            f"Scheduled {node.code} ({node.name}) "
            f"{node.planned_start} → {node.planned_end} ({days}d)"
        )

        next_date = node.planned_end + timedelta(days=1)

        # Schedule children in order
        children = node.get_children().order_by("sequence", "code")
        for child in children:
            next_date = self._schedule_node(child, next_date)

        return next_date
