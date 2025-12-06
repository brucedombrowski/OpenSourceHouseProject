from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from wbs.models import WbsItem, normalize_code_for_sort


class Command(BaseCommand):
    help = (
        "Renumber WBS codes based on the current MPTT tree.\n"
        "Roots: 1, 2, 3 ...\n"
        "Children: 1.1, 1.2, 2.1, etc.\n"
        "Also updates sequence and sort_key."
    )

    def handle(self, *args, **options):
        verbosity = options.get("verbosity", 1)

        items = list(
            WbsItem.objects.order_by("tree_id", "lft").only("id", "parent_id", "code", "name")
        )

        if not items:
            self.stdout.write("No WBS items found.")
            return

        self.stdout.write(
            f"Renumbering WBS for {len([i for i in items if i.parent_id is None])} root items..."
        )

        by_parent = defaultdict(list)
        for item in items:
            by_parent[item.parent_id].append(item)

        updates = []

        def renumber_node(node, prefix: str, index: int):
            new_code = f"{prefix}.{index}" if prefix else str(index)
            try:
                new_seq = int(new_code.split(".")[-1])
            except ValueError:
                new_seq = 1

            old_code = node.code or ""
            node.code = new_code
            node.sequence = new_seq
            node.sort_key = normalize_code_for_sort(new_code)
            updates.append(node)

            if verbosity >= 2:
                self.stdout.write(f"{node.name}: {old_code} -> {new_code} (sequence={new_seq})")

            for child_idx, child in enumerate(by_parent.get(node.id, []), start=1):
                renumber_node(child, new_code, child_idx)

        for root_idx, root in enumerate(by_parent.get(None, []), start=1):
            renumber_node(root, prefix="", index=root_idx)

        with transaction.atomic():
            WbsItem.objects.bulk_update(updates, ["code", "sequence", "sort_key"])

        self.stdout.write(self.style.SUCCESS("Renumbering complete."))
