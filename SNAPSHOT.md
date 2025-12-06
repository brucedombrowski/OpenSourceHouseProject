# House WBS Project Snapshot
**Date: December 5, 2025**

## Project Overview
A Django-based Work Breakdown Structure (WBS) project management system for house construction/renovation planning with Gantt scheduling, dependencies, and project item tracking.

## Current Codebase Structure

### Core Models (wbs/models.py - 399 lines)
- **WbsItem**: Hierarchical MPPT-based WBS nodes with:
  - Code, name, description, hierarchy
  - Planning: duration_days, cost_labor, cost_material
  - Scheduling: planned_start, planned_end, actual_start, actual_end
  - Progress: status (not_started, in_progress, done, blocked), percent_complete
  - Methods: update_rollup_dates(), update_rollup_progress()
  - Milestone support, notes

- **ProjectItem**: Linked to WbsItem with:
  - Types: Issue, Task
  - Status: todo, in_progress, blocked, done, open, closed
  - Priority, severity, external_ref
  - Methods: get_linked_wbs_item()

- **TaskDependency**: Links between WbsItem predecessors/successors
  - Lag_days field
  - Unique constraint on (predecessor, successor)

### Views (4,066 lines across views.py + views_gantt.py)
**views.py** (144 lines):
- project_item_board() - Kanban view
- project_item_status_update() - Status update API
- Re-exports from views_gantt.py

**views_gantt.py** (19,733 lines):
- gantt_view() - Main Gantt page
- gantt_chart() - Gantt data API
- gantt_shift_task() - Drag scheduling
- gantt_set_task_dates() - Precise date editing
- gantt_optimize_schedule() - ASAP scheduling
- Dependency checking & conflict warnings

### Admin Interface (wbs/admin.py - 5,168 bytes)
- WbsItemAdmin with:
  - Hierarchical list display (tree, code, name, dates)
  - Inline ProjectItemInline
  - Admin actions: rollup_wbs_dates
  - Custom sorting by sort_key
  - Percent complete display

- ProjectItemAdmin with:
  - Type, status, priority, severity filtering
  - WBS item link display

### Tests (wbs/tests.py - 5,171 bytes - 149 lines)
- RollupTests class:
  - test_update_rollup_dates_rolls_up_from_descendants
  - test_update_rollup_progress_weights_by_duration
- TaskDependencyTests class (incomplete)

### Templates
- gantt.html - Main Gantt UI with:
  - Sticky headers/columns
  - Collapsible hierarchy
  - Project Items side panel
  - Filter controls
  - Drag-and-drop scheduling

- kanban.html - Kanban board view
- admin/base_site.html - Branded admin

### Static Assets
- wbs/gantt.js - Timeline rendering, drag logic, filter handling
- wbs/gantt.css - Layout, sticky positioning, dependency highlights

### Management Commands
- import_wbs_csv.py - Import WBS from CSV
- export_wbs_csv.py - Export to CSV
- import_dependencies_csv.py - Import links
- export_dependencies_csv.py - Export links
- init_wbs_basic.py - Initialize sample data
- rollup_wbs_dates.py - Trigger rollup
- rollup_wbs_progress.py - Trigger progress rollup
- renumber_wbs.py - Re-sequence codes
- auto_schedule_wbs.py - Auto-scheduling
- full_backup.py - Backup to CSV

## Completed Features (Task Status)
✅ Collapse/Expand Gantt Rows
✅ Gantt Highlight Dependencies
✅ Sample Dependencies Import
✅ Percent Complete Bar Overlay
✅ Fix Missing Collapse/Expand Buttons
✅ Implement update_rollup_dates
✅ Fix rollup_wbs_dates Command
✅ Add Admin Action: Rollup WBS Dates
✅ Rename Admin Branding to House Project Admin
✅ Add Project Item System
✅ Add Project Item counts to WBS items
✅ Inline Project Items in WBS Admin
✅ Gantt Filters for Items with Issues/Tasks
✅ Gantt: Click Task → Show Project Items
✅ Refactor Gantt Assets
✅ Admin Text Cleanup
✅ Gantt draggable scheduling
✅ Gantt edit start/end dates
✅ Gantt optimize schedule button
✅ Gantt sticky task name
✅ Gantt collapsible Project Items
✅ Gantt enlarge expand/collapse icons
✅ Gantt sticky headers columns

## Open/In-Progress Items

### Issues (Open/Closed Status)
1. **Issue #1**: WBS Renumbering Inconsistent
   - Status: Open
   - Problem: Renumbering behaves differently in admin UI vs CLI; drag of root nodes triggers MPPT InvalidMove
   - Component: Admin UI
   
2. **Issue #20**: App Module Name 'wbs' Unclear
   - Status: Open
   - Problem: Django app named 'wbs' doesn't match House Project branding
   - Component: Architecture
   - Note: Future refactor; consider renaming app or adding alias without breaking migrations

### In-Progress Tasks
3. **Task #15**: Project Item Board & List Views
   - Status: In Progress
   - Kanban board: ✅ Implemented with Gantt ↔ Board links; drag-and-drop status updates supported
   - List view: ⏳ Still pending
   - Component: Project Items

4. **Task #21**: Add basic tests for rollup and dependencies
   - Status: In Progress
   - Needed: Tests for update_rollup_dates, update_rollup_progress, TaskDependency uniqueness
   - Component: Tests / QA
   - Note: Structural quality task; no behavior changes

## Database/Migrations
Current migrations: 0001 through 0009
- 0009: alter_projectitem_external_ref_and_more (latest)

## Key Observations
- App branding unified to "House Project" but code still uses "wbs" module name
- Gantt scheduling fully functional with drag, date editing, optimization
- Project Items (issues/tasks) system integrated but list view incomplete
- Test coverage basic; need comprehensive tests for rollup/dependencies
- MPPT tree integrity issues noted during admin renumbering

## Performance Notes
- Large static files (gantt.js ~800 lines)
- Tree operations (MPPT) require careful handling during bulk operations
- Drag/drop requires precision with dependency checking
