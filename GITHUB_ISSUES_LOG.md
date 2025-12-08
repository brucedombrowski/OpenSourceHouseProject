# GitHub Issues Tracking Log - December 8, 2025

This file tracks GitHub issues created and linked to work. Update this as new issues are created.

## Issues Created Today

### #78: Phase-Based Filtering for Kanban Board
**Status**: ✅ COMPLETED
**Description**: Add ability to filter Kanban board by WBS phases (1-15)
**Commits**:
- Optimize phase extraction queries (158 → 2 queries)
- Add phase filter to Kanban template with 2-column grid layout
- Implement phase filtering in JavaScript
- Fix numeric sorting for phases

**Files Changed**:
- `wbs/views.py` - Phase extraction logic
- `wbs/templates/wbs/kanban.html` - Phase filter UI
- `wbs/static/wbs/kanban.js` - Phase filter JavaScript

**Branch**: main
**Merged**: 2025-12-08

---

### #79: Build Procedure Improvements & Query Optimization
**Status**: ✅ COMPLETED
**Description**: Create smart build procedures to prevent caching issues and optimize database queries
**Commits**:
- Create build.sh script with quick/rebuild/fresh strategies
- Optimize WbsItem phase extraction (N+1 query fix)
- Add comprehensive documentation (BUILD_PROCEDURES.md, DEVELOPMENT.md)
- Increase Gunicorn timeout from 30s to 60s

**Performance Impact**:
- Kanban load time: 30+ sec (timeout) → <1 sec
- Database queries: 158 → 2 (98% reduction)
- Build time: 10-15 sec (quick), 20-30 sec (rebuild)

**Files Changed**:
- `build.sh` - NEW smart build script
- `BUILD_PROCEDURES.md` - NEW detailed procedures
- `DEVELOPMENT.md` - NEW quick start guide
- `docker-compose.yml` - Timeout increase
- `wbs/views.py` - Query optimization

**Branch**: main
**Merged**: 2025-12-08

---

### #80: Consistent Authentication Strategy (No Login for Development)
**Status**: ✅ COMPLETED
**Description**: Remove mixed auth requirements, allow all views to be accessible during development
**Commits**:
- Remove @staff_member_required from all Gantt views
- Document production auth strategy
- Create AUTH_STRATEGY.md with implementation plan

**Files Changed**:
- `wbs/views_gantt.py` - Removed 6 @staff_member_required decorators
- `AUTH_STRATEGY.md` - NEW auth strategy document

**Branch**: main
**Merged**: 2025-12-08

---

### #81: Gantt UI Regression Fix & Admin Access
**Status**: ✅ COMPLETED
**Description**: Fix broken Gantt layout (checkboxes in code column, expand/collapse, sticky columns) and restore admin login for testing. Ensure comprehensive test dataset (WBS, deps, project items) loads with known credentials.
**Changes**:
- `wbs/templates/wbs/gantt.html` / `wbs/static/wbs/gantt.css`: fix stray CSS brace, correct sticky column offsets, remove debug row styling.
- `wbs/management/commands/load_test_data.py`: load dependencies from template; ensure admin password resets to `admin123` for tests.
- `house_wbs/settings.py`: allow `0.0.0.0` in ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS for dev logins.
- `runserver.sh`: prefer `.venv`, pin host/port to 127.0.0.1:8000.
- Installed `whitenoise` dev dependency to start server.
**Outcome**: Gantt expand/collapse and layout restored; dependency arrows render; admin panel accessible with `admin`/`admin123`; test data load includes dependencies.
**Branch**: main
**Merged**: 2025-12-08

---

## Next Issues to Create

Before starting next feature, create GitHub issues for:
- [ ] Card detail modal on click
- [ ] Bulk actions (multi-card operations)
- [ ] Drag-and-drop improvements
- [ ] Filter presets/saved views
- [ ] Performance monitoring/dashboards

---

## Commit Message Template

Use this format going forward:

```
<type>: <description> (fixes #<issue_number>)

Body (optional):
- List of changes
- Additional context

Examples:
- feat: Add card detail modal (fixes #82)
- fix: Resolve drag-drop z-index issue (fixes #81)
- perf: Optimize WbsItem queries (fixes #83)
```

**Types**: feat, fix, perf, docs, refactor, test, chore

---

## Issue Labels (Standard)

- `bug` - Something broken
- `enhancement` - New feature or improvement
- `task` - Work item or TODO
- `documentation` - Docs updates
- `performance` - Performance optimization
- `in-progress` - Currently being worked on
- `blocked` - Waiting on something else
- `good first issue` - Good for newcomers

---

## Process

1. **Create issue** on GitHub before starting work
2. **Mark as "in-progress"** when you start
3. **Link commits** with `fixes #<num>` in commit messages
4. **Update issue description** as work progresses
5. **Close issue** when work is merged

---

**Last Updated**: 2025-12-08
**Tracking Person**: Luke (GitHub Copilot)
