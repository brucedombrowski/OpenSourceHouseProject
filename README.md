HOUSE PROJECT MANAGEMENT APP
============================

Django 6 + MPTT-powered WBS, Gantt chart, Project Items (issues/tasks/etc.), and admin tooling.

Quick start
-----------
Option 1 — single command (runs everything, no prompts):
```
bash quickstart.sh  # run from repo root (after git clone && cd OpenSourceHouseProject)
# change port/host: PORT=8001 HOST=0.0.0.0 bash quickstart.sh
```

Already set up and just need the server?
```
bash runserver.sh           # auto-picks a free port starting at 8000
PORT=8001 bash runserver.sh # start search at 8001
```

Option 2 — do it manually (paste as-is):
```bash
set -euo pipefail

# from repo root (after git clone && cd OpenSourceHouseProject)
# create virtualenv and install deps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # or: pip install django django-mptt

# initialize DB and admin (no prompts)
python manage.py migrate
DJANGO_SUPERUSER_USERNAME=admin \
DJANGO_SUPERUSER_EMAIL=admin@example.com \
DJANGO_SUPERUSER_PASSWORD=adminpass \
python manage.py createsuperuser --noinput

# load sample WBS + dependencies (optional seed data)
# NOTE: the admin user is stored in db.sqlite3; keep the DB after import.
python manage.py import_wbs_csv data/wbs_items_template.csv --update
python manage.py import_dependencies_csv data/wbs_dependencies_template.csv --update
python manage.py rollup_wbs_dates
python manage.py rollup_wbs_progress

# run dev server
python manage.py runserver
```

Defaults: admin user `admin/adminpass` (change via `DJANGO_SUPERUSER_*` env vars). Keeps `db.sqlite3` with seeded data.

Key URLs
--------
- Admin: http://127.0.0.1:8000/admin/
- Gantt: http://127.0.0.1:8000/gantt/
- Project Item Board (Kanban): http://127.0.0.1:8000/project-items/board/
- Project Item List: http://127.0.0.1:8000/project-items/list/

Features
--------
- WBS hierarchy with scheduling fields, rollup dates/progress, and dependency lags.
- Gantt with drag-to-reschedule, date edit modal, dependency highlighting, sticky headers, and Project Item panel toggle.
- Optimize schedule action (ASAP with dependency lags; root anchored).
- Project Items (issues/tasks/enhancements/risks/decisions) with board and list views.
- Admin customizations (inline Project Items, branding).

Data/imports
------------
Sample templates are provided:
- `data/wbs_items_template.csv` (validated 148-row WBS)
- `data/wbs_dependencies_template.csv` (generated dependencies aligned to WBS)

Restore from templates:
```
python manage.py import_wbs_csv data/wbs_items_template.csv --update
python manage.py import_dependencies_csv data/wbs_dependencies_template.csv --update
python manage.py rollup_wbs_dates
python manage.py rollup_wbs_progress
```

If you have your own CSVs, use the same commands with your filenames.

Testing
-------
```
source venv/bin/activate
python manage.py test
```

Notes
-----
- Keep `db.sqlite3` out of version control; use your own DB as needed.
- Sticky headers rely on current CSS; if you tweak layout widths, revisit `wbs/static/wbs/gantt.css`.
- Additional docs live in `docs/` (architecture decision record, snapshot, work summary).
