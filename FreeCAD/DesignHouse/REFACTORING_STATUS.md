# BeachHouse Refactoring Status

**Last Updated**: Dec 19, 2025 (Post-Luna-Walk Session)
**Current Progress**: Foundation section refactored (~15% complete)

---

## ✅ Completed Sections

### 1. Lot Survey (100% Complete)
- **Location**: `Build_950Surf_REFACTOR.FCMacro` lines 122-174
- **Function**: `create_lot_survey()`
- **What it does**:
  - Creates property boundary (50' x 100' lot)
  - Creates buildable area (with setbacks)
  - Creates origin marker (cross at 0,0)
- **Improvements**:
  - Clean function with docstring
  - Uses `beach_common.ft()` for unit conversion
  - Uses `beach_common.create_group()` for grouping
  - 0 manual catalog lookups (none needed for survey lines)

### 2. Foundation - Piles & Beams (80% Complete)
- **Location**: `Build_950Surf_REFACTOR.FCMacro` lines 180-325
- **Function**: `create_foundation()`
- **What it does**:
  - Creates 30 piles (5x6 grid, 12x12x40 PT, 20' embedded)
  - Creates double beams (2x12x16 PT on both pile faces)
  - Groups into Foundation → Piles, Beams subgroups
- **Improvements**:
  - Uses `beach_common.make_pile()` (eliminates ~15 lines per pile)
  - Uses `beach_common.make_beam()` (eliminates ~15 lines per beam)
  - Uses `beach_common.find_stock()` for fail-fast validation
  - Uses `beach_common.attach_beach_metadata()` for all metadata
  - **Eliminated ~60 lines** of manual catalog lookup code
  - Comprehensive docstring (construction sequence, design rationale, IRC refs)
- **Missing** (20% of foundation):
  - Blocking between beams (IRC R502.7 lateral support)
  - Mid-span boards (additional load distribution)
  - Pile notching (boolean cut for beam seats)

---

## ⏸️ In Progress

### Foundation - Blocking & Mid-Boards (Next ~50 lines)
The original macro has this code (lines 234-293):
- Creates blocking at 4' and 12' along each beam pair
- Creates mid-span 8' boards between specific pile rows
- Performs boolean cuts to notch piles for beam seats

**Plan**: Add to `create_foundation()` function following same pattern as piles/beams.

---

## 📋 Remaining Sections (By Priority)

### Priority 1: Floor System (~500 lines → ~300 lines estimated)
**Original**: Lines 1121-1800 (complex, multiple joist modules)
**Sections**:
1. Joist Module 16x16 Front-Right (lines 1121-1243)
2. Joist Module 16x16 Front-Left (lines 1251-1362)
3. Additional joist modules for mid/back rows
4. Sheathing (AdvanTech 4x8 panels, staggered seams)

**Complexity**: HIGH
- Multiple 16x16 joist modules at different positions
- Hanger placement logic (Simpson LU210 at each joist end)
- Sheathing placement with stagger pattern
- Lots of manual catalog lookups (20+ instances)

**Strategy**:
- Create `create_joist_module()` helper in beach_common.py
- Mirrors the lumber/ Joist_Module_2x12_16x16.FCMacro approach
- Call once per module position (Front-Right, Front-Left, etc.)
- Use beach_common for all metadata

### Priority 2: Walls (~400 lines → ~250 lines estimated)
**Original**: Lines 1689-1920 (wall framing)
**Sections**:
- Front walls (2x4 framing)
- Back walls (mirrored)
- Left/Right walls (8' sections)
- Top plates (perimeter)

**Complexity**: MEDIUM
- Repetitive 2x4 stud walls
- Manual catalog lookups for every plate/stud
- Grouping into wall sections

**Strategy**:
- Create `create_wall_section()` helper
- Pass: length, height, stud spacing, position
- Use beach_common.attach_beach_metadata()

### Priority 3: Stairs (~400 lines → ~250 lines estimated)
**Original**: Lines 492-893 (stair assembly)
**Sections**:
- Interior stairs
- Exterior stairs
- Stair walls
- Risers + treads

**Complexity**: HIGH
- Complex geometry (risers, treads, kicker)
- Nested groups
- Manual catalog lookups

**Strategy**:
- Create `create_stair_assembly()` helper
- Break into: risers, treads, walls, landing
- Use beach_common throughout

### Priority 4: Second Floor (~300 lines → ~200 lines estimated)
**Original**: Lines 2136-2310 (mirrors first floor)
**Sections**:
- Second floor joists (copy of first floor)
- Second floor sheathing
- Second floor walls

**Complexity**: MEDIUM
- Mostly copy-paste of first floor with Z offset
- Same catalog lookup issues

**Strategy**:
- Reuse first floor functions with Z offset parameter
- Eliminate all copy-paste duplication

### Priority 5: Roof (~200 lines → ~150 lines estimated)
**Original**: Roof section (if exists in macro)
**Complexity**: LOW-MEDIUM
**Strategy**: TBD based on original implementation

---

## 📊 Estimated Total LOC Reduction

| Section | Original LOC | Estimated Refactored | Savings |
|---------|--------------|---------------------|---------|
| Lot Survey | 30 | 53 | -23 (more docs) |
| Foundation (complete) | 330 | 200 | **+130** |
| Floor System | 500 | 300 | **+200** |
| Walls | 400 | 250 | **+150** |
| Stairs | 400 | 250 | **+150** |
| Second Floor | 300 | 200 | **+100** |
| Roof | 200 | 150 | **+50** |
| **TOTAL** | **2,160** | **~1,403** | **+757 (35%)** |

*Note: LOC count doesn't include helper functions, which live in beach_common.py*

---

## 🎯 Next Immediate Steps (When You Say "Keep Going")

### Step 1: Complete Foundation Function (30 min)
Add blocking + mid-boards + pile notching to `create_foundation()`.

**Lines to add**: ~50
**Code to eliminate**: ~60 (manual catalog lookups)
**Net**: Foundation 100% complete

### Step 2: Create Joist Module Helper (45 min)
Extract joist module pattern into `beach_common.py`:

```python
def create_joist_module_16x16(doc, catalog, params):
    """Build 16x16 joist module with 2x12 joists @ 16" OC.

    Construction Sequence:
        1. Create rim joists (4 sides, box frame)
        2. Create interior joists (16" OC spacing)
        3. Create hanger hardware (Simpson LU210 at each joist end)
        4. Group into module

    Returns:
        module_grp: Group with Joists + Hardware subgroups
    """
    # Implementation using beach_common patterns
```

### Step 3: Refactor Floor Joist Sections (1 hr)
Replace lines 1121-1800 with calls to `create_joist_module_16x16()`.

**Before** (180 lines per module x 4 modules = 720 lines):
```python
# Inline manual joist creation with catalog lookups repeated 50+ times
module_grp = doc.addObject("App::DocumentObjectGroup", "Module_...")
# ... 180 lines of boilerplate ...
```

**After** (~40 lines per module x 4 modules = 160 lines):
```python
module_FR = bc.create_joist_module_16x16(doc, catalog, {
    "position_x_ft": front_right_x_ft,
    "position_y_ft": module_front_y_ft,
    "position_z_ft": module_base_z_ft,
    "joist_label": "joist_2x12_PT",
    "hanger_label": "hanger_LU210",
})
```

**Savings**: 560 lines eliminated

---

## 🔥 Why This Refactoring Matters (Construction Perspective)

### Before Refactoring:
```python
# Manual catalog lookup (repeated 20+ times)
if module_joist_label in catalog:
    row = catalog[module_joist_label]
    for prop in ("supplier", "sku", "url"):
        val = row.get(prop)
        if val:
            if prop not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", prop)
            obj.__setattr__(prop, val)
```

**Problems**:
- **8 lines** of boilerplate per part
- **No color** applied (can't visually QA model)
- **Missing fields** (sku_lowes, url_lowes not added)
- **No fail-fast** (silent failure if label not in catalog)
- **Not DRY** (change metadata format = change 20+ places)

### After Refactoring:
```python
# One line using beach_common
row = bc.find_stock(catalog, "joist_2x12_PT")
bc.attach_beach_metadata(obj, row, "joist_2x12_PT")
```

**Benefits**:
- **2 lines** vs 8 lines (75% reduction)
- **Color palette** applied automatically (visual QA)
- **All fields** (sku_lowes, url_lowes, sku_hd, url_hd, price)
- **Fail-fast** (ValueError if label not found)
- **DRY** (change once in beach_common, affects all parts)

---

## 🚦 Decision Points

### Option A: Continue Incremental Refactoring (Recommended)
**Pros**:
- Test after each section
- Commit frequently
- Catch issues early
- Easier to review

**Cons**:
- Takes longer (multiple sessions)
- Incomplete macro until finished

**Estimated Time**:
- Foundation completion: 30 min
- Joist modules: 2 hrs
- Walls: 1.5 hrs
- Stairs: 1.5 hrs
- Second floor: 1 hr
- Roof: 1 hr
- **Total: ~7.5 hours of focused work**

### Option B: Complete Foundation, Test, Then Continue
**Pros**:
- Get a working partial model ASAP
- Verify approach before committing to full refactoring
- Can test with run_beach_house.sh

**Cons**:
- Model will be incomplete
- Can't verify joist/wall sections yet

**Estimated Time**: 30 min to foundation completion

### Option C: Pause and Review
**Pros**:
- Review coding standards
- Review refactoring plan
- Discuss priorities

**Cons**:
- Delays completion

---

## 📝 Recommendation

**I recommend Option B**: Complete the foundation section (blocking + mid-boards + pile notching), then test it.

**Why**:
1. Foundation is standalone (can be tested independently)
2. Proves the beach_common approach works
3. Gives you a working model to inspect visually
4. Only 30 more minutes of work
5. Then we can decide: continue with joists, or adjust approach

**Next command from you**:
- **"Complete foundation"** → I'll finish blocking/mid-boards/notching
- **"Keep going to joists"** → I'll add joist helper + refactor floor
- **"Let's test foundation first"** → I'll finish foundation, we test, then continue
- **"Let's review the plan"** → We discuss approach before continuing

---

**Your call, Bruce!** What works best for your workflow?
