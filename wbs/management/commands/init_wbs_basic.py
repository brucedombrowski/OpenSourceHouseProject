from django.core.management.base import BaseCommand
from wbs.models import WbsItem


DEFAULT_ITEMS = [
    ("0", "Pre-Construction & Administration", None, 1, 1),
    ("1", "Site Work & Earthwork", None, 1, 2),
    ("1.1", "Clearing & Demolition", "1", 2, 1),
    ("1.2", "Grading & Excavation", "1", 2, 2),
    ("1.3", "Fill & Compaction", "1", 2, 3),
    ("2", "Foundation System", None, 1, 3),
    ("2.1", "Formwork", "2", 2, 1),
    ("2.2", "Reinforcement", "2", 2, 2),
    ("2.3", "Footings", "2", 2, 3),
    ("3", "Structural Framing", None, 1, 4),
    ("3.1", "Floor Framing", "3", 2, 1),
    ("3.2", "Wall Framing", "3", 2, 2),
    ("3.3", "Roof Framing", "3", 2, 3),
    ("4", "Roofing System", None, 1, 5),
    ("5", "Building Envelope", None, 1, 6),
    ("6", "Exterior Finishes", None, 1, 7),
    ("7", "Rough-In Systems", None, 1, 8),
    ("8", "Insulation & Air Sealing", None, 1, 9),
    ("9", "Interior Finishes", None, 1, 10),
    ("10", "Finish MEP", None, 1, 11),
    ("11", "Appliance Installation", None, 1, 12),
    ("12", "Exterior Works & Hardscape", None, 1, 13),
    ("13", "Inspections & Certifications", None, 1, 14),
    ("14", "Punch List & Closeout", None, 1, 15),
]


class Command(BaseCommand):
    help = "Initialize a basic house WBS structure"

    def handle(self, *args, **options):
        code_to_item = {}

        for code, name, parent_code, level, sequence in DEFAULT_ITEMS:
            parent = code_to_item.get(parent_code) if parent_code else None
            item, created = WbsItem.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "parent": parent,
                    "wbs_level": level,
                    "sequence": sequence,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created {code} — {name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Exists {code} — {name}"))

            code_to_item[code] = item

        self.stdout.write(self.style.SUCCESS("Basic WBS initialized."))
