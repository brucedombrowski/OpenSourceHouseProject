# House Project Management - User Guide

**Version 1.0** | December 6, 2025

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Gantt Chart View](#gantt-chart-view)
3. [Kanban Board](#kanban-board)
4. [Project Items List](#project-items-list)
5. [WBS Management](#wbs-management)
6. [Dependencies](#dependencies)
7. [Admin Features](#admin-features)
8. [Tips & Best Practices](#tips--best-practices)

---

## Getting Started

### First Login

1. Navigate to `http://localhost:8000/admin/`
2. Login with your credentials (default: `admin/adminpass`)
3. You'll see the Django admin interface

### Main Views

The application has four primary views:

- **Gantt Chart** (`/gantt/`) - Visual timeline of WBS tasks with dependencies
- **Kanban Board** (`/project-items/board/`) - Drag-and-drop task management
- **Project Items List** (`/project-items/list/`) - Filterable list of all items
- **Admin Panel** (`/admin/`) - Full data management interface

---

## Gantt Chart View

### Overview

The Gantt chart displays your Work Breakdown Structure (WBS) as a visual timeline with bars representing task durations.

### Features

#### **Timeline Navigation**

- **Zoom In/Out**: Use the zoom controls in the toolbar
  - Daily, Weekly, Monthly, Quarterly views available
- **Scroll**: Horizontal scroll to see past/future dates
- **Today Button**: Quickly jump to current date

#### **Task Bars**

Each task is represented by a colored bar:
- **Blue**: Active tasks
- **Green**: Completed tasks (100% progress)
- **Red**: Milestone tasks (zero duration)
- **Gray**: Not started tasks

**Bar Information:**
- Hover over a bar to see task details
- Bar width = task duration
- Bar position = scheduled dates

#### **Drag to Reschedule**

1. Click and hold on a task bar
2. Drag left or right to new dates
3. Release to update the schedule
4. Task automatically saves with new dates

**Note:** Dependencies are preserved when dragging. Dependent tasks will update accordingly.

#### **Edit Task Details**

1. Click the **pencil icon** (✏️) next to any task name
2. Modal opens with editable fields:
   - Planned Start/End dates
   - Actual Start/End dates
   - Status (Not Started, In Progress, Completed, On Hold)
   - Progress percentage
   - Description and notes
3. Click **Save** to update

#### **Dependencies (Arrows)**

Tasks with dependencies show **colored arrows**:
- **Green arrow** (→): Finish-to-Start (FS) - Task B starts when Task A finishes
- **Orange arrow** (→): Start-to-Start (SS) - Task B starts when Task A starts
- **Purple arrow** (→): Finish-to-Finish (FF) - Task B finishes when Task A finishes
- **Blue arrow** (→): Start-to-Finish (SF) - Task B finishes when Task A starts

**Dependency Features:**
- Click "Show Dependencies" to highlight arrows
- Click a task row to highlight its dependencies
- Arrows show lag days if applicable (+2d, -1d, etc.)

#### **Project Items Panel**

Toggle the **right sidebar** to see project items (bugs, tasks, enhancements) linked to WBS tasks:

1. Click the **panel toggle button** (≡) in the toolbar
2. Panel slides in from the right
3. Click any WBS task row to filter items for that task
4. Click items to see details

#### **Toolbar Actions**

- **Optimize Schedule**: Automatically schedules tasks ASAP respecting dependencies
- **Export CSV**: Download current WBS data
- **Import CSV**: Upload WBS data from file
- **Rollup Dates**: Recalculate parent task dates from children
- **Rollup Progress**: Update parent task completion % from children

---

## Kanban Board

### Overview

Manage project items (issues, tasks, enhancements, risks, decisions) using a drag-and-drop board.

### Columns

- **To Do**: Items not yet started
- **In Progress**: Actively being worked on
- **Blocked**: Waiting on something
- **Done**: Completed items

### Card Features

Each card shows:
- **Title** and description snippet
- **Type badge**: Issue, Task, Enhancement, Risk, Decision
- **Priority badge**: Critical, High, Medium, Low
- **WBS link**: Which task it's related to
- **Owner**: Assigned person
- **Dates**: Started and completed timestamps

### Actions

#### **Move Items**

1. Click and drag a card
2. Drop in a different column
3. Status automatically updates

#### **Filter & Search**

Use the top filters to narrow down items:
- **Type**: Show only issues, tasks, etc.
- **Priority**: Filter by urgency
- **WBS**: Show items for specific tasks
- **Search**: Find by title/description

#### **Create New Items**

1. Click "Add Item" button
2. Fill in the form:
   - Type (required)
   - Title (required)
   - Description
   - Priority
   - Severity (for issues)
   - Link to WBS task
   - Assign owner
3. Click "Create"

#### **Edit Items**

1. Click on a card
2. Modal opens with full details
3. Edit any field
4. Click "Save"

---

## Project Items List

### Overview

A filterable, sortable list view of all project items grouped by WBS task.

### Features

#### **Filtering**

Use the filter panel at the top:
- **Search**: Text search across title, description, owner, WBS
- **Type**: Issue, Task, Enhancement, Risk, Decision
- **Status**: To Do, In Progress, Blocked, Done, Open, Closed
- **Priority**: Critical, High, Medium, Low
- **Severity**: Low, Medium, High, Critical

Click **Filter** to apply, **Clear** to reset.

#### **Grouping**

Items are grouped by their linked WBS task:
- Each group shows WBS code and name
- Count of items in each group
- Expand/collapse groups

#### **Pagination**

- 10 WBS groups per page
- Navigation controls at bottom
- Page indicator shows current position

#### **Item Details**

Each item shows:
- Icon indicating completion status (✓ or clock)
- Title
- Type, priority, status badges
- Owner (if assigned)
- Dates (started/completed)

---

## WBS Management

### What is WBS?

Work Breakdown Structure (WBS) is a hierarchical decomposition of your project into manageable tasks.

**Example:**
```
1.0 House Construction
  1.1 Foundation
    1.1.1 Site Preparation
    1.1.2 Pour Concrete
  1.2 Framing
    1.2.1 Floor Framing
    1.2.2 Wall Framing
```

### Creating WBS Items

#### **Via Admin Panel**

1. Go to `Admin > WBS Items > Add WBS Item`
2. Fill in required fields:
   - **Code**: Unique identifier (e.g., "1.1.2")
   - **Name**: Task name
   - **Parent**: Select parent task (if child)
3. Optional fields:
   - Duration, costs, dates
   - Status, progress %
   - Notes
4. Click "Save"

#### **Via CSV Import**

1. Prepare CSV file with columns:
   - `code, name, description, parent_code, duration_days, planned_start, planned_end, status, percent_complete`
2. Run command:
   ```bash
   python manage.py import_wbs_csv your_file.csv --update
   ```
3. Items are created/updated automatically

### Editing WBS Items

- **Gantt View**: Click pencil icon to edit dates/status
- **Admin Panel**: Full edit access to all fields
- **CSV**: Export, edit, re-import

### Deleting WBS Items

**Caution:** Deleting a parent task deletes all children!

1. Go to Admin panel
2. Select WBS item
3. Click "Delete"
4. Confirm deletion

### WBS Codes

**Best practices:**
- Use hierarchical numbering (1.1.1, 1.1.2, 1.2.1)
- Keep codes unique
- Don't reuse deleted codes
- Use consistent depth levels

---

## Dependencies

### Dependency Types

1. **Finish-to-Start (FS)** - Most common
   - Task B can't start until Task A finishes
   - Example: Can't frame walls until foundation is poured

2. **Start-to-Start (SS)**
   - Task B can't start until Task A starts
   - Example: Quality inspection starts when construction starts

3. **Finish-to-Finish (FF)**
   - Task B can't finish until Task A finishes
   - Example: Testing finishes when development finishes

4. **Start-to-Finish (SF)** - Rarely used
   - Task B can't finish until Task A starts
   - Example: Night security can't finish until day security starts

### Lag Days

Add delays or overlaps:
- **Positive lag** (+3d): 3-day delay between tasks
- **Negative lag** (-2d): 2-day overlap (Task B starts early)

### Creating Dependencies

#### **Via Admin Panel**

1. Go to `Admin > Task Dependencies > Add Task Dependency`
2. Select:
   - **Predecessor**: Task that must happen first
   - **Successor**: Task that depends on predecessor
   - **Type**: FS, SS, FF, or SF
   - **Lag**: Number of days (can be negative)
3. Click "Save"

#### **Via CSV Import**

1. Prepare CSV with columns:
   - `predecessor_code, successor_code, dependency_type, lag_days, notes`
2. Run:
   ```bash
   python manage.py import_dependencies_csv deps.csv --update
   ```

### Viewing Dependencies

- **Gantt Chart**: Click "Show Dependencies" button
- **Admin Panel**: View all dependencies with filters
- **Export CSV**: Download current dependencies

### Editing Dependencies

- Change type or lag in Admin panel
- Delete and recreate if needed
- Dependencies update schedule automatically

---

## Admin Features

### WBS Item Admin

**Bulk Actions:**
- Delete multiple items
- Export selected items to CSV

**Filters:**
- Status (Not Started, In Progress, etc.)
- Has parent (top-level vs. children)
- Is milestone
- Date ranges

**Search:**
- Search by code, name, or description

**Inline Management:**
- Edit Project Items directly within WBS item page

### Project Item Admin

**Bulk Actions:**
- Update status for multiple items
- Assign owner to multiple items
- Delete selected items

**Filters:**
- Type, status, priority, severity
- Has WBS link
- Assigned vs. unassigned
- Date ranges

**Search:**
- Title, description, external ref, reporter, owner

### Management Commands

Run from terminal with `python manage.py <command>`:

#### **Data Import/Export**

```bash
# Import WBS from CSV
python manage.py import_wbs_csv data/wbs_items.csv --update

# Export WBS to CSV
python manage.py export_wbs_csv output.csv

# Import dependencies
python manage.py import_dependencies_csv data/deps.csv --update

# Export dependencies
python manage.py export_dependencies_csv output_deps.csv
```

#### **Schedule Management**

```bash
# Auto-schedule tasks ASAP (respects dependencies)
python manage.py auto_schedule_wbs

# Rollup parent dates from children
python manage.py rollup_wbs_dates

# Rollup parent progress from children
python manage.py rollup_wbs_progress
```

#### **Maintenance**

```bash
# Renumber WBS codes (clean up gaps)
python manage.py renumber_wbs

# Full backup (all tables to JSON)
python manage.py full_backup backups/
```

---

## Tips & Best Practices

### Project Planning

1. **Start with WBS**
   - Break down project into manageable tasks
   - Use 3-5 levels of hierarchy
   - Keep tasks 1-10 days duration

2. **Define Dependencies Early**
   - Identify task relationships upfront
   - Use FS dependencies for most cases
   - Add lag days for realistic scheduling

3. **Set Baselines**
   - Export WBS to CSV before starting
   - Compare actual vs. planned regularly

### Daily Usage

1. **Update Progress Regularly**
   - Mark tasks as In Progress when starting
   - Update % complete weekly
   - Log actual dates when done

2. **Use Project Items for Details**
   - Create issues for problems
   - Track tasks within WBS tasks
   - Document decisions

3. **Review Gantt Weekly**
   - Check for delayed tasks
   - Adjust schedule if needed
   - Communicate changes to team

### Performance

1. **Pagination**: List view auto-paginates at 10 groups
2. **Caching**: Gantt timeline cached for 1 hour
3. **Compression**: GZip enabled for faster loading
4. **Query Optimization**: Views use select_related/prefetch_related

### Data Management

1. **Backup Regularly**
   ```bash
   python manage.py full_backup backups/$(date +%Y%m%d)/
   ```

2. **Export Before Major Changes**
   ```bash
   python manage.py export_wbs_csv backup_$(date +%Y%m%d).csv
   ```

3. **Test Imports on Dev First**
   - Never import directly to production
   - Validate CSV format
   - Check for duplicate codes

### Keyboard Shortcuts (Coming Soon)

- `←/→` - Navigate Gantt timeline
- `+/-` - Zoom in/out
- `Space` - Toggle dependencies
- `Esc` - Close modals

---

## Troubleshooting

### Common Issues

**Gantt chart not showing tasks**
- Verify tasks have planned_start and planned_end dates
- Check that dates are within visible timeline
- Try zooming out to see wider range

**Dependencies not appearing**
- Click "Show Dependencies" button
- Verify dependency exists in Admin panel
- Check that both tasks are visible on timeline

**Drag-and-drop not working**
- Ensure task has both start and end dates
- Check browser console for JavaScript errors
- Try refreshing the page

**Performance is slow**
- Clear browser cache
- Check for large number of tasks (>500)
- Consider filtering or pagination
- Verify caching is enabled in settings

### Getting Help

1. Check `docs/ARCHITECTURE_DECISION_RECORD.md` for technical details
2. Review `docs/PERFORMANCE_NOTES.md` for optimization info
3. File issues on GitHub: https://github.com/brucedombrowski/OpenSourceHouseProject/issues
4. Check README.md for setup instructions

---

## Glossary

- **WBS**: Work Breakdown Structure - hierarchical project decomposition
- **Gantt Chart**: Visual timeline showing task durations and dependencies
- **Kanban**: Visual board for managing work items by status
- **Predecessor**: Task that must happen before another
- **Successor**: Task that depends on another
- **Lag**: Delay (positive) or overlap (negative) between dependent tasks
- **Milestone**: Zero-duration task marking important events
- **Critical Path**: Longest sequence of dependent tasks (coming soon)
- **Baseline**: Original planned schedule for comparison

---

**Last Updated**: December 6, 2025
**Version**: 1.0
**Project**: OpenSourceHouseProject
