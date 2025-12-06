# Issue #20: App Module Name 'wbs' Unclear - Strategy & Analysis

**Status**: Closed (Documented) | **Severity**: Low | **Component**: Architecture
**Date**: December 5, 2025 | **Updated**: December 6, 2025

## Problem Statement
The Django app is named `wbs` (Work Breakdown Structure), but the project is branded as "House Project" across the admin interface and user-facing views. This creates a discrepancy:
- Code imports: `from wbs.models import ...`
- Admin labels: "House Project", "WBS Items"
- Branding: All UI shows "House Project Admin"

## Options Analyzed

### Option 1: Complete App Rename (Highest Impact)
**Rename `wbs` → `house_project`**

**Pros:**
- Full branding consistency
- Clearer module naming for future developers
- Aligns code with user-facing terminology

**Cons:**
- ⚠️ **Breaking change**: All existing migrations must be remapped
- Requires data migration to update Django content types
- Must update all imports across the codebase:
  - `wbs/models.py` → `house_project/models.py`
  - `wbs/views.py` → `house_project/views.py`
  - `house_wbs/urls.py` imports
  - `settings.py` INSTALLED_APPS
  - All template references (reverse, app_name, etc.)
- Database tables would need migration (`wbs_wbsitem` → `house_project_wbsitem`)
- All 9 existing migrations would need remapping
- **Deployment risk**: High for existing installations

### Option 2: App Alias (Medium Impact, Recommended)
**Keep `wbs` app, add documentation & optional alias in Django admin**

**Pros:**
- ✅ Zero breaking changes
- Minimal code modification
- No database migration risk
- Existing installations unaffected
- Can add a Django AppConfig `verbose_name` for display

**Cons:**
- Developer confusion may persist (internal code says "wbs")
- Not a perfect solution, but pragmatic

### Option 3: Complete App Rename with Fresh Database (Development Only)
**Rename app + delete migrations + start fresh**

**Pros:**
- Full consistency achieved
- Clean slate for future development
- No migration complexity

**Cons:**
- Only viable for development/non-production
- Loses all historical data
- Not suitable for existing deployments

## Recommended Strategy: Option 2 + Documentation

### Implementation (Minimal Risk)

#### Step 1: Already Done - Update AppConfig verbose_name
File: `wbs/apps.py`
```python
class WbsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wbs"
    verbose_name = "House Project"  # ← Already set
```

#### Step 2: Add Code-Level Documentation (Completed)
- Added docstring explaining naming convention to `wbs/__init__.py`
- Documented in README.md that `wbs` is internal code name
- Help text unchanged; commands continue to live under the `wbs` label

#### Step 3: Consider Future Refactoring
- Document for future consideration (not now)
- Option to deprecate in v2.0 with migration guide
- Keep track of rename cost if needed later

## Migration Path for Future Rename (if ever needed)

If a rename is warranted in the future, here's the high-level approach:

1. Create a new Django app `house_project` (parallel)
2. Copy models and migrate data
3. Update imports in views/urls/admin
4. Create custom migration to handle content types
5. Deprecate `wbs` app
6. In v2.0: Remove old app after transition period

## Decision: **Adopt Option 2**

**Rationale:**
- Minimal risk to production
- Aligns with agile principle of "make it work, make it right, make it fast"
- Current branding is already consistent at the UI level
- Preserves data integrity and deployment stability
- Can be reconsidered if naming becomes a major pain point

## Related Tasks
- ✅ Task #19: Admin Text Cleanup (completed - unified "House Project" branding at UI level)
- Task #20: Future consideration for app rename (when business justifies the migration cost)

## Files Already Updated for Branding Consistency
- `wbs/apps.py` - verbose_name = "House Project"
- `wbs/models.py` - WbsItem & ProjectItem verbose_name
- `templates/admin/base_site.html` - Branded admin header
- `wbs/admin.py` - Display labels
- Views: Kanban, List, Gantt all show "House Project" branding

---

**Conclusion**: The architectural naming issue is acknowledged but deferred. The cost of a full rename outweighs the current benefit. The app is functionally and visibly branded as "House Project" to end users, which is the priority. Documentation now clarifies that `wbs` remains the stable internal module name.
