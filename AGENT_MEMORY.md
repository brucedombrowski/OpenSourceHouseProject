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
- **Status**: Production-ready v1.0.0 with 44 passing tests
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
- ✅ Tested (44 unit tests, 2.3s runtime)
- ✅ Production-ready infrastructure (Docker, nginx, PostgreSQL support)

## Session History Notes

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
