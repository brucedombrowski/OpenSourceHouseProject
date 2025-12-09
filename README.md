
![Build Status](https://img.shields.io/github/actions/workflow/status/brucedombrowski/OpenSourceHouseProject/ci.yml?branch=main)
![License](https://img.shields.io/github/license/brucedombrowski/OpenSourceHouseProject)
![Issues](https://img.shields.io/github/issues/brucedombrowski/OpenSourceHouseProject)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)
![Django Version](https://img.shields.io/badge/Django-6.0-darkgreen)
![Tests Passing](https://img.shields.io/badge/Tests-45%20Passing-brightgreen)

HOUSE PROJECT MANAGEMENT APP
============================

Django 6 + MPPT-powered WBS, Gantt chart, Project Items (issues/tasks/etc.), and admin tooling.

## ✅ Production Ready

**Version 1.0.0** - Ready for deployment
**Test Coverage**: 45 tests passing (100%)
**Code Quality**: Flake8 ✅ | Black ✅ | No issues detected
**Performance**: GZip enabled | WhiteNoise configured | Query optimized

For production deployment, see:
- **Quick Start**: [QUICK_DEPLOYMENT.md](QUICK_DEPLOYMENT.md) (5 minutes)
- **Full Guide**: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
- **Checklist**: [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)

Quick start
-----------
Copy the sample env and adjust as needed (at minimum set a new SECRET_KEY):
```
cp .env.example .env
```

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
pip install -r requirements.txt  # Core dependencies (Django, MPTT, etc.)
# For production with PostgreSQL, also install:
# pip install -r requirements-production.txt

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
- `data/project_items_template.csv` (57 diverse project items for testing Kanban/filters)
- `data/wbs_items_minimal.csv` (5 top-level tasks for quick testing)
- `data/wbs_dependencies_minimal.csv` (5 dependency relationships: FS, SS, FF, SF, + lag)

Restore from templates:
```
python manage.py import_wbs_csv data/wbs_items_template.csv --update
python manage.py import_dependencies_csv data/wbs_dependencies_template.csv --update
python manage.py import_project_items_csv data/project_items_template.csv --update
python manage.py rollup_wbs_dates
python manage.py rollup_wbs_progress
```

Quick start with minimal fixtures (for testing Gantt arrows/dependencies):
```
python manage.py import_wbs_csv --minimal --update
python manage.py import_dependencies_csv --minimal --update
python manage.py rollup_wbs_dates
# Minimal fixture: 5 tasks with FS/SS/FF/SF dependencies and 1-day lag example
```

If you have your own CSVs, use the same commands with your filenames.

Build & Deployment
------------------

**Dependencies**:
- `requirements.txt` - Core dependencies for development (Django, MPTT, SQLite)
- `requirements-production.txt` - Production add-ons (PostgreSQL, Gunicorn, WhiteNoise)

Static assets (CSS/JS) are collected and optimized for production:

**Development** (default):
```
pip install -r requirements.txt
python manage.py runserver
# Uses basic static file storage; assets auto-reload
```

**Production build** (collectstatic with manifest + cache busting):
```
pip install -r requirements.txt
pip install -r requirements-production.txt  # PostgreSQL, Gunicorn, WhiteNoise
python build_assets.py       # Collect and process static files
# Generates staticfiles/ with content hashes for cache busting
# Set DEBUG=False and SECURE_* flags in .env for full production mode
```

For best performance in production:
- Use WhiteNoise middleware (included in `requirements-production.txt`)
- Serve staticfiles/ from CDN or reverse proxy with long cache headers
- Set `STATIC_ROOT` to a persistent location on your server

Development & Performance Profiling
------------------------------------
Enable query logging to see all SQL queries during development:

```bash
# Edit .env to include:
DEBUG=True

# Restart server and check terminal for query logs:
# [11/Dec/2025 10:30:45] "SELECT ..." from django.db.backends

# Use performance decorators in views for detailed profiling:
from wbs.performance import profile_view, query_counter, log_query_details

@profile_view("my_expensive_endpoint")
@query_counter
def my_view(request):
    # Logs execution time and query count
    ...
```

Available profiling decorators:
- `@profile_view("name")` — logs execution time and query count (warning if > 1s)
- `@query_counter` — counts and logs all queries executed
- `@log_query_details` — detailed SQL logging with timing per query

See `wbs/performance.py` for more options.

Testing
-------
```
source venv/bin/activate
python manage.py test
```


Contributing & Issue Tracking
------------------------------
We welcome contributions! To get started:

1. **Fork** the repository on GitHub.
2. **Clone** your fork and create a new branch for your changes.
3. Follow the code style and linting guidelines (see `docs/LINTING_GUIDE.md`).
4. Add or update tests as needed.
5. Submit a **pull request** with a clear description of your changes.

We use **GitHub Issues** for bug reports, feature requests, and task tracking:
- [Report bugs](https://github.com/brucedombrowski/OpenSourceHouseProject/issues/new?template=bug_report.md)
- [Request features](https://github.com/brucedombrowski/OpenSourceHouseProject/issues/new?template=feature_request.md)
- [Create tasks](https://github.com/brucedombrowski/OpenSourceHouseProject/issues/new?template=task.md)

See `docs/GITHUB_ISSUES_MIGRATION.md` for workflow details, labels, and best practices.

**Quick tips:**
- Use issue templates for consistency
- Link commits with `fixes #123` to auto-close issues
- Add labels (`bug`, `enhancement`, `task`) for organization
- Group work with milestones for releases

**Contact/Support:**
For questions or support, open an issue or contact the maintainer via GitHub.

Documentation
-------------
Comprehensive documentation is available in the `docs/` directory:

- **[User Guide](docs/USER_GUIDE.md)** - Complete guide to using the system (Gantt, Kanban, WBS, filters, etc.)
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Cheat sheet with commands, shortcuts, and common tasks
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Production deployment instructions (nginx, PostgreSQL, SSL, monitoring)
- **[Architecture Decisions](docs/ARCHITECTURE_DECISION_RECORD.md)** - Technical design decisions and rationale
- **[Performance Notes](docs/PERFORMANCE_NOTES.md)** - Optimization strategies and profiling results
- **[GitHub Issues Migration](docs/GITHUB_ISSUES_MIGRATION.md)** - Issue tracking workflow and best practices

**Quick links:**
- New user? Start with the [User Guide](docs/USER_GUIDE.md)
- Need a quick command? Check [Quick Reference](docs/QUICK_REFERENCE.md)
- Deploying to production? See [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)


Troubleshooting & FAQ
---------------------

**Common Issues:**

- *Virtualenv not activating?* Ensure you are using `bash` and run `source venv/bin/activate` from the repo root.
- *Missing dependencies?* Run `pip install -r requirements.txt` after activating your virtualenv.
- *Port already in use?* Change the port with `PORT=8001 bash runserver.sh` or kill the process using the port.
- *Static files not updating?* Run `python build_assets.py` and clear your browser cache.
- *Database errors?* Delete `db.sqlite3` and re-run migrations if you want a fresh start.

For more help, see the [User Guide](docs/USER_GUIDE.md) or open a GitHub issue.

Notes
-----
- Keep `db.sqlite3` out of version control; use your own DB as needed.
- Sticky headers rely on current CSS; if you tweak layout widths, revisit `wbs/static/wbs/gantt.css`.
- The Django app name stays `wbs` internally for stability; UI branding uses "House Project" (see `docs/ARCHITECTURE_DECISION_RECORD.md`).
- Historical project tracking data archived in `archive/project_tracker.csv`.
