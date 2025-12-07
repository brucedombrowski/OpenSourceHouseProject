# Quick Reference Guide

**House Project Management System** - Cheat Sheet

---

## 🚀 Quick Start

```bash
# Start the server
bash runserver.sh

# Or manually:
source venv/bin/activate
python manage.py runserver
```

**Login**: http://localhost:8000/admin/ (admin/adminpass)

---

## 📍 Main URLs

| View | URL | Purpose |
|------|-----|---------|
| **Gantt Chart** | `/gantt/` | Visual timeline |
| **Kanban Board** | `/project-items/board/` | Drag-and-drop tasks |
| **Items List** | `/project-items/list/` | Filtered list view |
| **Admin Panel** | `/admin/` | Full management |

---

## ⌨️ Gantt Chart

### Actions
- **Drag task bar** → Reschedule
- **Click pencil icon** → Edit details
- **Click task row** → Highlight dependencies
- **Toggle panel (≡)** → Show/hide project items

### Toolbar
- **Zoom**: Daily, Weekly, Monthly, Quarterly
- **Today**: Jump to current date
- **Show Deps**: Toggle dependency arrows
- **Optimize**: Auto-schedule ASAP
- **Export/Import**: CSV data management

### Dependency Arrow Colors
- 🟢 **Green**: Finish-to-Start (FS)
- 🟠 **Orange**: Start-to-Start (SS)
- 🟣 **Purple**: Finish-to-Finish (FF)
- 🔵 **Blue**: Start-to-Finish (SF)

---

## 📋 Kanban Board

### Columns
- **To Do** → Not started
- **In Progress** → Active work
- **Blocked** → Waiting
- **Done** → Completed

### Actions
- **Drag card** → Change status
- **Click card** → View/edit details
- **Filter dropdown** → Narrow results
- **Add Item button** → Create new

---

## 🔧 Management Commands

```bash
# Import/Export
python manage.py import_wbs_csv file.csv --update
python manage.py export_wbs_csv output.csv
python manage.py import_dependencies_csv deps.csv --update
python manage.py export_dependencies_csv out_deps.csv

# Schedule Operations
python manage.py auto_schedule_wbs           # ASAP scheduling
python manage.py rollup_wbs_dates            # Parent date calc
python manage.py rollup_wbs_progress         # Parent % calc

# Maintenance
python manage.py renumber_wbs                # Fix WBS codes
python manage.py full_backup backups/        # Backup all data
```

---

## 📊 WBS Codes

**Format**: Hierarchical numbering

```
1.0           Project Root
  1.1         Phase 1
    1.1.1     Task A
    1.1.2     Task B
  1.2         Phase 2
    1.2.1     Task C
```

**Rules**:
- Unique codes only
- Consistent depth
- Use decimals for hierarchy

---

## 🔗 Dependencies

### Types

| Type | Code | Meaning | Example |
|------|------|---------|---------|
| **Finish-to-Start** | FS | B starts when A finishes | Foundation → Framing |
| **Start-to-Start** | SS | B starts when A starts | Inspection starts with work |
| **Finish-to-Finish** | FF | B finishes when A finishes | Testing ends with dev |
| **Start-to-Finish** | SF | B finishes when A starts | Night shift ends when day starts |

### Lag Days
- **+3d** = 3-day delay
- **-2d** = 2-day overlap

---

## 🏷️ Project Item Types

| Type | Purpose | Common Status |
|------|---------|---------------|
| **Issue** | Bugs, problems | Open, Closed |
| **Task** | Work items | To Do, In Progress, Done |
| **Enhancement** | New features | To Do, In Progress, Done |
| **Risk** | Potential issues | Open, Mitigated, Closed |
| **Decision** | Choices made | Open, Decided, Closed |

---

## 🎨 Status & Priority

### Task Status
- **Not Started**: Planned but not begun
- **In Progress**: Currently being worked
- **Completed**: Finished
- **On Hold**: Paused
- **Blocked**: Waiting on something

### Priority Levels
- 🔴 **Critical**: Drop everything
- 🟠 **High**: Important
- 🟡 **Medium**: Normal
- 🟢 **Low**: When time permits

---

## 🔍 Filters & Search

### List View Filters
- **Type**: Issue, Task, Enhancement, Risk, Decision
- **Status**: To Do, In Progress, Blocked, Done
- **Priority**: Critical, High, Medium, Low
- **Severity**: Low, Medium, High, Critical (for issues)
- **Search**: Text across title, description, owner, WBS

### Kanban Board Filters
- Type, Priority, WBS task
- Search by title/description

---

## 📦 CSV Import Format

### WBS Items
```csv
code,name,description,parent_code,duration_days,planned_start,planned_end,status,percent_complete
1.0,Project,Main project,,100,2025-01-01,2025-04-10,in_progress,25
1.1,Phase 1,First phase,1.0,30,2025-01-01,2025-01-30,completed,100
```

### Dependencies
```csv
predecessor_code,successor_code,dependency_type,lag_days,notes
1.1,1.2,FS,0,Phase 2 starts after Phase 1
1.2.1,1.2.2,SS,2,2-day delay for review
```

---

## ⚡ Performance Tips

1. **Pagination**: List view shows 10 groups per page
2. **Caching**: Gantt timeline cached for 1 hour
3. **Query Optimization**: All views use select_related
4. **GZip Compression**: Enabled for HTML/CSS/JS

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| Tasks not showing in Gantt | Check dates are set |
| Dependencies not visible | Click "Show Dependencies" button |
| Drag not working | Verify task has start+end dates |
| Slow performance | Clear cache, check task count |

---

## 📖 More Help

- **Full Guide**: `docs/USER_GUIDE.md`
- **Architecture**: `docs/ARCHITECTURE_DECISION_RECORD.md`
- **Performance**: `docs/PERFORMANCE_NOTES.md`
- **GitHub Issues**: https://github.com/brucedombrowski/OpenSourceHouseProject/issues

---

**Version**: 1.0 | **Date**: December 6, 2025
