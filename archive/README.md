# Archive Directory

## project_tracker.csv

**Archived**: December 6, 2025

Original project tracking CSV used during early development. Contains 82 items documenting bugs, features, tasks, and decisions from project inception through performance optimization phase.

**Why archived:**
- Migrated to GitHub Issues for better collaboration
- All items completed or resolved
- Preserved for historical reference

**Summary:**
- 79 items **Completed**
- 3 items **Closed**
- Covered: authentication, WBS core, Gantt visualization, Project Items board/list, performance optimizations, testing, documentation

**New workflow:**
See `docs/GITHUB_ISSUES_MIGRATION.md` for GitHub Issues usage.

---

**CSV Structure:**
- `id`: Unique identifier
- `type`: bug, feature, task, decision, documentation, performance
- `title`: Brief description
- `description`: Detailed info
- `status`: Completed, Closed
- `severity`: Critical, High, Medium, Low (for bugs)
- `component`: Which part of the system
- `date_started` / `date_completed`: Timeline
- `reported_by`: bruce
- `related_ids`: Links to other items
- `notes`: Additional context
