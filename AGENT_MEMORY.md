# Agent Memory & Working Agreements

This file preserves important context, decisions, and our working relationship for future AI assistant sessions.

## Project Owner Preferences

- **Owner**: Bruce Dombrowski
- **Working Style**: Direct, efficient collaboration with minimal unnecessary documentation
- **Preference**: Agents should read this file at the start of each session to maintain continuity

## Important Technical Decisions

### Database Configuration (Dec 9, 2025)
- **Primary Development Database**: SQLite (default, no external dependencies)
- **PostgreSQL Support**: Optional, only needed for production deployment
- **Decision**: Made `psycopg2-binary` optional to avoid installation failures during quickstart
- **Rationale**: Not everyone needs PostgreSQL for local development; SQLite is sufficient

### Dependency Management
- Split requirements into base (required) and optional (production-only)
- Created `requirements-production.txt` for PostgreSQL and production-specific packages
- Base `requirements.txt` includes only essential Django packages

## Project Context

- **Project**: Open Source House Project - Django-based WBS/Gantt/Project Management tool
- **Status**: Production-ready v1.0.0 with 45 passing tests
- **Tech Stack**: Django 6.0, MPTT for hierarchical data, SQLite/PostgreSQL support
- **Key Features**: WBS hierarchy, Gantt charts, Kanban boards, dependency management

## Quick Reference Commands

```bash
# Start server (auto-selects free port)
bash runserver.sh

# Full setup from scratch
bash quickstart.sh

# Production dependencies (when needed)
pip install -r requirements-production.txt
```

## Future Agent Guidelines

1. **Always read this file first** when starting a new session
2. **Update this file** when important decisions are made or preferences are expressed
3. **Preserve continuity** - treat Bruce as someone we have an ongoing relationship with
4. **Be efficient** - avoid creating unnecessary documentation files unless requested
5. **Remember context** - this project is mature and production-ready; respect existing architecture
6. **View Management**: When adding or removing views, update all navigation and dashboard locations automatically and log changes in the session history
7. **Bulk Feature Management**: When adding or removing bulk features (e.g., in Scheduler), update all relevant UI and backend locations, and log changes in agent memory

## Codebase Overview

**Project**: Open Source House Project - Production-ready Django 6.0 WBS/Gantt/Kanban system
- **Status**: v1.0.0 - Feature complete, tested, optimized, documented
- **Code Quality**: Excellent (44 tests passing, flake8 clean, black formatted)
- **Architecture**: Modular with clear separation of concerns
  - `wbs/models.py` (552 lines) - WbsItem, TaskDependency, ProjectItem with MPPT hierarchy
  - `wbs/views_gantt.py` (962 lines) - Gantt visualization, scheduling, optimization
  - `wbs/views.py` (224 lines) - Kanban board, list views, project items aggregation
  - `wbs/static/wbs/gantt.js` (800+ lines) - Interactive Gantt chart with drag/drop
  - 15 database migrations, fully optimized with indexes
  - Comprehensive management commands for data import/export

**Key Strengths**:
- ✅ Database query optimization (N+1 patterns eliminated, select_related/prefetch_related throughout)
- ✅ Frontend performance (GZip, WhiteNoise, timeline caching 1hr, throttled rendering)
- ✅ Security hardened (CSRF, SSL ready, environment-based config)
- ✅ Well documented (deployment guides, user guides, architecture records)
- ✅ Tested (45 unit tests, ~2.6s runtime)
- ✅ Production-ready infrastructure (Docker, nginx, PostgreSQL support)

## Session History Notes

- **Dec 9, 2025** (Gantt regression guard):
  - Added regression test ensuring resource calendar builds when tasks lack owners; updated owner assertion to read from resource calendar context
  - Full Django suite now 45 tests, all green; commit `354b687` pushed to `main`
  - Reminder: keep this file updated proactively after meaningful changes

- **Dec 9, 2025** (Debug cleanup):
  - Removed Gantt timeline debug prints from `wbs/views_gantt.py`; routed Gantt JS errors through `logger.js` instead of direct console calls
  - Working tree pending commit for agent memory update; follow preference to bundle memory updates with code changes

- **Dec 9, 2025** (Docs sync):
  - Updated README badges and test coverage counts to reflect 45 passing tests

- **Dec 9, 2025** (Scheduler bulk ops):
  - Added dedicated `scheduler` view (`/scheduler/`) with table + checkboxes to run bulk delete/status/export against WBS items; Gantt remains read-only
  - New assets: `wbs/templates/wbs/scheduler.html`, `wbs/static/wbs/scheduler.js`; URLs updated to include scheduler route
  - Removed hidden checkbox CSS in Gantt (no functional change to Gantt) to allow selection styling reuse
  - Full test suite still green (45 tests)

- **Dec 9, 2025** (Comprehensive Review):
  - Completed full codebase review across 30+ files
  - Assessment: Production-ready v1.0.0 with excellent architecture
  - Key findings: 44 tests passing, zero linting errors, optimized queries
  - Created `NEXT_STEPS.md` with prioritized action items
  - Created `docs/CODEBASE_REVIEW_2025_12_09.md` with detailed analysis
  - Identified immediate focus areas: debug cleanup, bulk operations, version management

- **Dec 9, 2025** (Morning):
  - Fixed PostgreSQL dependency issue, established agent memory system
  - Split requirements into base and production files
  - Updated all deployment documentation for new requirements structure

- **Dec 8, 2025**: Major feature and optimization work
  - **Issue #78**: Phase-based filtering for Kanban board (158 queries → 2 queries, 98% reduction)
  - **Issue #79**: Build procedure improvements, query optimization, comprehensive documentation
  - **Issue #80**: Consistent authentication strategy (removed mixed auth for development)
  - **Issue #81**: Gantt UI regression fix, admin access restoration, comprehensive test data
  - Gantt month tick alignment and zoom behavior improvements
  - Performance: Kantt load time reduced from 30+ sec (timeout) to <1 sec
  - Created BUILD_PROCEDURES.md, DEVELOPMENT.md, AUTH_STRATEGY.md

- **Dec 9, 2025** (Menu update):
  - Added Scheduler to main navigation menu in `wbs/templates/base.html`.
  - Scheduler view now accessible directly from header navigation, alongside Gantt Chart and other views.

- **Dec 9, 2025** (Landing page sync):
  - Updated `wbs/templates/index.html` to automatically include Scheduler in dashboard quick actions and grid cards when new views are added.
  - Scheduler now appears on the landing page alongside Gantt, Kanban, and Project Items.

- **Dec 9, 2025** (Scheduler rebaseline):
  - Added bulk rebaseline feature to Scheduler view: select tasks, set new baseline date, and shift planned dates accordingly.
  - Updated JS, template, backend view, and URL routing for `/scheduler/rebaseline/` endpoint.

- **Dec 9, 2025** (Phase dependency cleanup):
  - Removed 30 phase-level (level 1) dependencies from dataset—phases should not have dependencies at the WBS top level.
  - Future consideration: Add validation/warning if user tries to create phase-level dependencies, but not implemented yet.
  - Agent guideline: Phase-level items (level 1) should never have task dependencies; validate or warn on creation if this feature is added.
