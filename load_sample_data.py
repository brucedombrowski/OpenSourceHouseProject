#!/usr/bin/env python
import os
from datetime import date

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "house_wbs.settings")
django.setup()

# fmt: off
# isort: skip_file
from wbs.models import TaskDependency, WBSItem  # noqa: E402

# Create WBS items with dates
data = [
    {"code": "1", "name": "High-Level Build", "start": date(2025, 1, 1), "end": date(2025, 1, 7)},
    {"code": "2", "name": "Site Prep", "start": date(2025, 1, 6), "end": date(2025, 1, 12)},
    {"code": "3", "name": "Foundation", "start": date(2025, 1, 1), "end": date(2025, 1, 5)},
    {"code": "4", "name": "Framing", "start": date(2025, 1, 12), "end": date(2025, 1, 18)},
    {"code": "5", "name": "Roofing", "start": date(2025, 1, 19), "end": date(2025, 1, 24)},
]

items = {}
for d in data:
    item, created = WBSItem.objects.get_or_create(
        code=d["code"],
        defaults={
            "name": d["name"],
            "planned_start": d["start"],
            "planned_end": d["end"],
        },
    )
    items[d["code"]] = item
    if created:
        print(f"Created: {d['code']} - {d['name']}")

# Create dependencies
deps = [
    ("1", "2", "FS"),
    ("1", "3", "SS"),
    ("2", "4", "FF"),
    ("3", "5", "SF"),
    ("4", "5", "FS", 1.0),
]

for dep in deps:
    pred_code = dep[0]
    succ_code = dep[1]
    dep_type = dep[2]
    lag = dep[3] if len(dep) > 3 else 0

    pred = items[pred_code]
    succ = items[succ_code]

    dep_obj, created = TaskDependency.objects.get_or_create(
        predecessor=pred, successor=succ, defaults={"dependency_type": dep_type, "lag": lag}
    )
    if created:
        print(f"Created dependency: {pred_code} -> {succ_code} ({dep_type})")

print("Sample data loaded successfully!")
