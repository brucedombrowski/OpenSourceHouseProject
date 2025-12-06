# Performance Notes & Optimizations

**Last Updated**: December 6, 2025

## Query Optimizations

### Gantt View (`wbs/views_gantt.py`)
- **Owner List Query**: Computed once early in `gantt_chart()` and reused for both the empty-data case and normal case to avoid duplicate User queries. ✅
- **Prefetch Related**: Gantt uses `Prefetch` to efficiently load ProjectItems with their owners in a single batch query.
- **Select Related**: Both `gantt_chart` and `project_item_list` use `select_related("wbs_item", "owner")` to prevent N+1 queries.

### Project Item Views (`wbs/views.py`)
- **Kanban Board**: Uses `select_related("wbs_item", "owner")` and orders by status/priority for efficient rendering.
- **List View**: Uses `select_related("wbs_item", "owner")` for efficient rendering and filtering.
- **Search**: Searches owner by `username`, `first_name`, `last_name` after migration to FK.

### Admin Interface (`wbs/admin.py`)
- **ProjectItemAdmin**: Uses `list_select_related` for owner and `list_prefetch_related` for tags to prevent N+1 queries in list view. ✅

## Database Indexes (Migration 0012)
- **WbsItem.code**: Unique constraint for fast lookups.
- **ProjectItem hot paths**:
  - `(status, -created_at)` for Kanban/board views
  - `(type, -created_at)` for filtering by type
  - `priority`, `severity` for single-column filters
  - `(wbs_item, status)` for WBS-grouped queries

## Caching & Browser Storage
- **Gantt Zoom Level**: Stored in `localStorage` and persisted across page loads.
- **Theme Preference**: Stored in `localStorage` for dark/light mode.

## Frontend Optimizations

### JavaScript
- **Arrow Redraw Throttling**: Dependency arrow redraws on scroll/resize are throttled to `requestAnimationFrame` to avoid layout thrash.
- **Passive Event Listeners**: Scroll listener registered as passive (`{ passive: true }`) to prevent blocking.
- **Will-Change Hints**: Sticky columns have `will-change: transform` to enable GPU acceleration.

### CSS
- **Fixed Layout**: Gantt table uses `table-layout: fixed` to prevent column resizing during scroll.
- **Scrollbar Gutter**: `scrollbar-gutter: stable` prevents column nudging when scrollbars appear/disappear.

## Asset Bundling
- **Static Files**: Using Django's `ManifestStaticFilesStorage` for cache-busting (MD5 hash in filename).
- **Shared Theme Logic**: Extracted to `shared-theme.js` for reuse across Gantt/Board/List.
- **Fetch Utilities**: Centralized in `fetch-utils.js` to standardize error handling and CSRF injection.

## Testing
- **Test Coverage**: 42 comprehensive tests including query efficiency checks (e.g., `test_gantt_owner_query_efficiency`).
- **Query Efficiency Test**: `test_gantt_owner_query_efficiency` verifies that the owner list is computed exactly once per Gantt page load, preventing N+1 query patterns.

## Session Optimizations (December 6, 2025)

### Commit: e49c736 - "Performance: eliminate duplicate owner query in gantt_chart view"
- **Issue**: `gantt_chart` view computed the User query twice (lines 92 and 331) in different code branches
- **Fix**: Moved all_owners computation to before the "if not tasks" conditional
- **Benefit**: Reduces query count by 1 per page load; prevents N+1 anti-pattern
- **Test**: Added `test_gantt_owner_query_efficiency` to verify single execution

### Commit: 0421ed9 - "Performance: add owner and tags prefetch_related to ProjectItemAdmin"
- **Issue**: `ProjectItemAdmin.list_select_related` was missing "owner" FK optimization
- **Fix**: Added "owner" to `list_select_related` and "tags" to `list_prefetch_related`
- **Benefit**: Admin list view now avoids N+1 queries for owner display and tag filtering

## Query Patterns to Avoid

### N+1 Anti-Pattern
❌ **Bad**: Loop that queries for related objects
```python
for item in items:
    print(item.owner.username)  # Query per item
```

✅ **Good**: Use select_related/prefetch_related
```python
items = ProjectItem.objects.select_related("owner")
for item in items:
    print(item.owner.username)  # No additional queries
```

### Duplicate Queries
❌ **Bad**: Computing same data in multiple branches
```python
if not tasks:
    all_owners = User.objects.all()
    return render(..., {"owners": all_owners})
else:
    all_owners = User.objects.all()  # Redundant query
    return render(..., {"owners": all_owners})
```

✅ **Good**: Compute once, reuse everywhere
```python
all_owners = User.objects.all()
if not tasks:
    return render(..., {"owners": all_owners})
else:
    return render(..., {"owners": all_owners})
```

## Recommended Next Steps

1. **Query Profiling**: Use Django Debug Toolbar in development to profile slow queries during peak use.
2. **Database Maintenance**: Periodically run `ANALYZE` on SQLite (or equivalent in Postgres) to update table statistics.
3. **Pagination**: Consider pagination for very large ProjectItem lists (currently fetches all).
4. **Caching**: Consider caching Gantt timeline/year/month/day bands for repeated requests.
5. **Compression**: Enable gzip compression on static assets and API responses.

## Rollup Performance Notes

- **Incremental Updates**: Rollups batch updates via `update_fields` to minimize DB writes.
- **Recursive Depth**: Tested up to 3+ levels of hierarchy; remains fast.

---

**Author**: Bruce Dombrowski
**Project**: Open Source House Project (WBS/Gantt/Kanban)
