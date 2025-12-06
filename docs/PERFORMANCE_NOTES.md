# Performance Notes & Optimizations

**Last Updated**: December 6, 2025

## Query Optimizations

### Gantt View (`wbs/views_gantt.py`)
- **Owner List Query**: Computed once early in `gantt_chart()` and reused for both the empty-data case and normal case to avoid duplicate User queries. ✅
- **Prefetch Related**: Gantt uses `Prefetch` to efficiently load ProjectItems with their owners in a single batch query.
- **Select Related**: Both `gantt_chart` and `project_item_list` use `select_related("wbs_item", "owner")` to prevent N+1 queries.

### Project Item Views (`wbs/views.py`)
- **Kanban Board**: Uses `select_related("wbs_item")` and orders by status/priority for efficient rendering.
- **List View**: Filters/groups by WBS with proper foreign key optimization.
- **Search**: Searches owner by `username`, `first_name`, `last_name` after migration to FK.

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
- **Test Coverage**: 41 comprehensive tests including query efficiency checks (e.g., `test_gantt_owner_query_efficiency`).

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
