HOUSE PROJECT MANAGEMENT APP
============================

Django 6 + MPTT-powered WBS, Gantt chart, Project Items (issues/tasks/etc.), and admin tooling.

Quick start
-----------
```bash
# fresh OS: clone and set up env
git clone https://github.com/brucedombrowski/OpenSourceHouseProject.git
cd OpenSourceHouseProject

# create virtualenv and install deps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # or pip install django django-mptt

# initialize DB and admin
python manage.py migrate
python manage.py createsuperuser

# load sample WBS + dependencies (optional seed data)
# NOTE: createsuperuser is wiped if you delete db.sqlite3; keep the DB after import.
python manage.py import_wbs_csv wbs_items_template.csv --update
python manage.py import_dependencies_csv wbs_dependencies_template.csv --update
python manage.py rollup_wbs_dates
python manage.py rollup_wbs_progress

# run dev server
python manage.py runserver
```

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
- `wbs_items_template.csv` (validated 148-row WBS)
- `wbs_dependencies_template.csv` (generated dependencies aligned to WBS)

Restore from templates:
```
cp wbs_items_template.csv wbs_items.csv
cp wbs_dependencies_template.csv dependencies.csv
python manage.py import_wbs_csv wbs_items.csv --update
python manage.py import_dependencies_csv dependencies.csv --update
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
