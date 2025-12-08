
# API and CSV Schemas

## Recent Changes

- **Dec 8, 2025:** Documentation updated, troubleshooting added, endpoint details clarified
- **Dec 6, 2025:** New dependency types supported, CSV validation improved

This project exposes lightweight HTML views plus a handful of POST endpoints used by the UI. Import/export commands accept CSVs with defined schemas. Use this guide to integrate safely.


## HTTP Endpoints

**Authentication:** All endpoints require a valid Django admin login session. For POST requests, include a CSRF token in the form data or headers.

**Common Issues:**
- If you receive a 403 error, check that you are logged in and have a valid CSRF token.
- For API automation, use Django's session authentication and fetch CSRF tokens from the rendered HTML or `/admin/` page.

- `GET /gantt/` — Gantt chart UI. Query params: `highlight=<WBS code>`, `mode`, `type`, `status`, `priority`, `severity`, `items_only=1`.
- `POST /gantt/shift/` — Shift a task (and optionally children). Form fields: `code` (str), `delta_days` (int), `include_children` ("true"/"false"). Returns JSON with updated tasks.
- `POST /gantt/set-dates/` — Set exact planned start/end for a task. Form fields: `code`, `planned_start` (YYYY-MM-DD), `planned_end` (YYYY-MM-DD). Returns JSON with updated task.
- `POST /gantt/optimize/` — ASAP reschedule respecting dependencies. No body required; returns JSON with updated tasks.
- `GET /project-items/board/` — Kanban board UI.
- `GET /project-items/list/` — List view UI. Filters: `type`, `status`, `priority`, `severity`, `wbs` (id), `q` (search).
- `POST /project-items/status/` — Update ProjectItem status (used by board drag/drop). Form fields: `id` (int), `status` (choice). Returns JSON `{ok, status}`.


## CSV Import/Export

Management commands live under `wbs.management.commands`. See [Quick Reference](QUICK_REFERENCE.md) and code in `wbs/management/commands/` for advanced usage and options.

### WBS items
- Import: `python manage.py import_wbs_csv <file> [--update] [--skip-rollup] [--dry-run]`
- Export: `python manage.py export_wbs_csv <file>`
- Schema (columns):
  - `code` (required, unique per file)
  - `name` (required)
  - `parent_code` (optional, must exist in CSV or DB)
  - `wbs_level` (int, defaults 1)
  - `sequence` (int, defaults 1)
  - `duration_days` (decimal)
  - `cost_labor` (decimal)
  - `cost_material` (decimal)
  - `planned_start`, `planned_end`, `actual_start`, `actual_end` (YYYY-MM-DD)
  - `status` (WBS status choice)
  - `percent_complete` (0-100, decimal)
  - `is_milestone` (bool: true/false/1/0/yes/no)
  - `description`, `notes` (text)
- Validation: required headers, duplicate code detection, date ordering checks, percent range, parent existence. `--dry-run` validates without writes.

### Task dependencies
- Import: `python manage.py import_dependencies_csv <file> [--update] [--dry-run]`
- Export: `python manage.py export_dependencies_csv <file>`
- Schema (columns):
  - `predecessor_code` (required, must exist)
  - `successor_code` (required, must exist)
  - `dependency_type` (FS/SS/FF/SF)
  - `lag_days` (numeric, can be negative for lead)
  - `notes` (text)
- Validation: required headers, duplicate pair detection, self-dependency rejection, allowed types check, numeric lag. `--dry-run` validates without writes.


### Sample data
- Templates: `data/wbs_items_template.csv`, `data/wbs_dependencies_template.csv`
- Create your own by exporting first (`export_wbs_csv`, `export_dependencies_csv`), editing the rows, then importing with `--dry-run` to validate before applying.


## Troubleshooting & FAQ

**API returns 403 Forbidden:**
- Ensure you are logged in to Django admin and have a valid CSRF token.
- For POST requests, include CSRF token in form data or headers.

**CSV import fails:**
- Check for required headers and valid codes.
- Use `--dry-run` to validate before applying changes.
- Review error messages for duplicate codes or invalid dates.

**Exported CSV missing data:**
- Ensure items exist in the database and are not filtered out by status or type.

For more help, see the [User Guide](USER_GUIDE.md) or open a GitHub issue.

## Notes
- Static files are served in DEBUG via Django staticfiles; production should serve `/static/` via your web server.
- Keep `.env` for secrets and host settings; `DEBUG` default is True for local dev but should be False in production.
