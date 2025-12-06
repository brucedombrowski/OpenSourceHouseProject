from django.core.management.base import BaseCommand

from wbs.models import WbsItem, normalize_code_for_sort


class Command(BaseCommand):
    help = (
        "Renumber WBS codes based on the current MPTT tree.\n"
        "Roots: 1, 2, 3 ...\n"
        "Children: 1.1, 1.2, 2.1, etc.\n"
        "Also updates sequence and sort_key."
    )

    def handle(self, *args, **options):
        # Get roots in true tree order
        roots = (
            WbsItem.objects.filter(parent__isnull=True)
            .order_by("tree_id", "lft")
        )

        if not roots.exists():
            self.stdout.write("No WBS items found.")
            return

        self.stdout.write(f"Renumbering WBS for {roots.count()} root items...")

        def renumber_node(node, prefix: str, index: int):
            """
            Recursively assign outline codes:
            prefix='' & index=1 -> '1'
            prefix='1' & index=1 -> '1.1'
            prefix='1.1' & index=3 -> '1.1.3'
            """
            if prefix:
                new_code = f"{prefix}.{index}"
            else:
                new_code = str(index)

            old_code = node.code or ""

            try:
                new_seq = int(new_code.split(".")[-1])
            except ValueError:
                new_seq = 1

            node.code = new_code
            node.sequence = new_seq
            node.sort_key = normalize_code_for_sort(new_code)
            node.save(update_fields=["code", "sequence", "sort_key"])

            self.stdout.write(
                f"{node.name}: {old_code} -> {new_code} (sequence={new_seq})"
            )

            # Children in tree order
            children = node.get_children().order_by("tree_id", "lft")
            for child_idx, child in enumerate(children, start=1):
                renumber_node(child, new_code, child_idx)

        # Renumber each root subtree
        for root_idx, root in enumerate(roots, start=1):
            renumber_node(root, prefix="", index=root_idx)

        self.stdout.write(self.style.SUCCESS("Renumbering complete."))
