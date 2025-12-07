# GitHub Issues Migration Guide

**Date**: December 6, 2025

## Overview

We've migrated from `project_tracker.csv` to **GitHub Issues** for better collaboration and integration with our development workflow.

## Why GitHub Issues?

✅ **Integrated**: Links directly to commits, PRs, and code
✅ **Collaborative**: Comments, mentions, notifications
✅ **Organized**: Labels, milestones, projects, search
✅ **Automated**: Auto-close with commit messages (`fixes #123`)
✅ **Free**: No additional tools or subscriptions needed

## Quick Start

### Creating Issues

1. Go to https://github.com/brucedombrowski/OpenSourceHouseProject/issues
2. Click "New Issue"
3. Choose a template:
   - **Bug Report** - for bugs and issues
   - **Feature Request** - for enhancements
   - **Task** - for work items

### Labels We Use

- `bug` - Something broken
- `enhancement` - New feature or improvement
- `task` - Work item or TODO
- `documentation` - Docs updates
- `performance` - Performance optimization
- `good first issue` - Good for newcomers
- `help wanted` - Need input/assistance

### Milestones

Group related issues into milestones (e.g., "v1.0", "Q1 2026")

### Linking Issues to Commits

Use keywords in commit messages:
```bash
git commit -m "Fix Gantt scroll jitter (fixes #57)"
git commit -m "Add pagination (closes #123)"
```

Keywords: `fixes`, `closes`, `resolves`

## Historical Data

The original CSV tracker (82 items) is archived in `archive/project_tracker.csv` for reference.

**Summary of completed work:**
- 79 items Completed
- 3 items Closed
- All major features implemented
- Performance optimizations complete

## GitHub Project Boards (Optional)

For Kanban-style tracking:
1. Go to repository → Projects
2. Create new project (board view)
3. Add columns: Backlog, Todo, In Progress, Done
4. Add issues to board

## Best Practices

1. **One issue = One thing** - Keep issues focused
2. **Use templates** - They ensure consistency
3. **Add labels** - Makes searching easier
4. **Link related issues** - Use `#123` notation
5. **Close completed issues** - Keep board clean
6. **Add milestones** - Group work into releases

## Migration Notes

All 82 items from the CSV are documented and completed. Future work should be tracked as GitHub Issues.

For questions, see: https://docs.github.com/en/issues
