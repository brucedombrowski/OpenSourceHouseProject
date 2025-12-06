HOUSE PROJECT MANAGEMENT APP
============================

Django 6 + MPTT-powered WBS, Gantt chart, Project Items (issues/tasks/etc.), and admin tooling.

Quick start
-----------
```bash
cd /Users/brucedombrowski/house_wbs_crud
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # or pip install django django-mptt
python manage.py migrate
python manage.py createsuperuser
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
If you have CSVs to restore:
```
python manage.py import_wbs_csv wbs_items.csv --update
python manage.py import_dependencies_csv dependencies.csv --update
```

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
