# BeachHouse Build Macro Refactoring Plan

**Date**: 2025-12-19
**Author**: Claude Code
**Status**: In Progress
**Target**: Build_950Surf.FCMacro

---

## Executive Summary

The current `Build_950Surf.FCMacro` (2,363 lines) contains significant code duplication, inconsistent patterns, and manual implementations of functionality already available in the shared `lumber_common` module. This refactoring will improve maintainability, reduce technical debt, and establish clean coding standards for the BeachHouse project.

**Key Metrics**:
- Current LOC: 2,363
- Estimated target LOC: ~1,600-1,800 (30-40% reduction)
- Code duplication instances: 20+ manual catalog lookups, 15+ grouping patterns
- Missing features: Color palette, consistent metadata attachment

---

## Design Principles

### 1. **DRY (Don't Repeat Yourself)**
   - **Problem**: Manual catalog lookup code repeated 20+ times
   - **Solution**: Use `lumber_common.attach_metadata()` helper
   - **Benefit**: Single source of truth, easier maintenance

### 2. **Separation of Concerns**
   - **Problem**: Monolithic 2,363-line macro mixing foundation, floors, walls, stairs
   - **Solution**: Extract logical sections into well-documented functions
   - **Benefit**: Testable, reusable, understandable components

### 3. **Consistent Abstraction Levels**
   - **Problem**: Mixed levels of abstraction (low-level Part.makeBox alongside high-level module assembly)
   - **Solution**: Create clear hierarchy: primitives → components → assemblies → building
   - **Benefit**: Code reads like architecture, not geometry

### 4. **Single Responsibility Principle**
   - **Problem**: Functions that create objects, add metadata, position, AND group
   - **Solution**: Each function does one thing well
   - **Benefit**: Easier to test, debug, and modify

### 5. **API Consistency**
   - **Problem**: FreeCAD grouping uses 3 different patterns across the macro
   - **Solution**: Standardize on one proven pattern from lumber/ macros
   - **Benefit**: Predictable behavior, fewer bugs

---

## Current Architecture Issues

### Issue 1: Manual Catalog Lookups (Anti-Pattern)

**Current Code** (repeated 20+ times):
```python
obj.label = module_joist_label
if module_joist_label in catalog:
    row = catalog[module_joist_label]
    for prop in ("supplier", "sku", "url"):
        val = row.get(prop)
        if val and prop not in obj.PropertiesList:
            obj.addProperty("App::PropertyString", prop)
        if val:
            obj.__setattr__(prop, val)
```

**Problems**:
- 8 lines of boilerplate per object
- No error handling if catalog entry malformed
- No support for color palette
- Missing fields: `sku_lowes`, `url_lowes`, `sku_hd`, `url_hd`
- Inconsistent property names vs lumber/ macros

**Target Code**:
```python
from lumber_common import attach_metadata, find_stock

row = find_stock(catalog_rows, module_joist_label)
attach_metadata(obj, row, module_joist_label, supplier="lowes")
```

**Benefits**:
- 2 lines vs 8 lines (75% reduction)
- Consistent with lumber/ macros
- Automatic color palette application
- Error handling built-in
- Future-proof (changes to metadata format happen once)

---

### Issue 2: No Color Palette

**Current State**: All objects use default gray FreeCAD colors

**Target State**: Palette-based coloring like lumber/ macros:
- Nominal size → base color (2x4=red, 2x6=orange, 2x12=blue, etc.)
- Length → shade factor (8'=bright, 16'=dark)
- Hardware → gray

**Implementation**:
```python
from lumber_common import color_for_row

row = find_stock(catalog_rows, label)
attach_metadata(obj, row, label)  # Applies color automatically
```

**Benefits**:
- Visual debugging (spot wrong stock at a glance)
- Consistent with main house project
- Professional appearance

---

### Issue 3: Inconsistent Grouping Patterns

**Pattern A** (found 15 times):
```python
grp = doc.addObject("App::DocumentObjectGroup", "Name")
grp.addObject(obj1)
grp.addObject(obj2)
```

**Pattern B** (found 8 times):
```python
grp = doc.addObject("App::DocumentObjectGroup", "Name")
grp.Group = []
grp.addObject(obj1)
```

**Pattern C** (found 5 times):
```python
grp = doc.addObject("App::DocumentObjectGroup", "Name")
objs = [obj1, obj2]
for o in objs:
    grp.addObject(o)
grp.Group = objs
```

**Standard Pattern** (from lumber/ macros):
```python
# Create all objects first
created = []
created.append(make_joist(...))
created.append(make_rim(...))

# Create group and attach
group = doc.addObject("App::DocumentObjectGroup", "Module_Name")
group.Label = "Module_Name"
for obj in created:
    group.addObject(obj)
group.Group = created  # Optional but explicit
```

**Benefits**:
- Predictable: objects created, then grouped
- Explicit: `Group` property set at end
- Debuggable: `created` list shows what should be grouped
- Proven: Works reliably in lumber/ macros

---

### Issue 4: Monolithic Structure

**Current**: 2,363 lines in one file organized as:
1. Parameters (lines 1-80)
2. Lot setup (lines 106-138)
3. Foundation/piles (lines 140-330)
4. Joist modules inline (lines 1121-1245, 1251-1362, 1443-1528, 1563-1680)
5. Sheathing inline (lines 1376-1438)
6. Walls inline (lines 1689-1775, 1822-1920)
7. Stairs inline (lines 492-893)
8. Second floor (lines 2136-2310)

**Problems**:
- Hard to navigate (where does "foundation" end and "floor" begin?)
- Hard to test (can't test joist module in isolation)
- Hard to reuse (want to use joist module elsewhere? Copy/paste)
- Hard to understand (mental model of 2,363 lines is difficult)

**Target Structure**:
```python
# Clear sections with headers
# ============================================================
# SECTION 1: FOUNDATION (Piles, Beams, Blocking)
# ============================================================
def create_foundation(doc, catalog, params):
    """Build pile foundation with beams and blocking.

    Args:
        doc: FreeCAD document
        catalog: List of catalog rows from lumber_catalog.csv
        params: Dict with pile_label, beam_label, positions, etc.

    Returns:
        foundation_grp: DocumentObjectGroup containing all foundation parts
    """
    foundation_grp = doc.addObject("App::DocumentObjectGroup", "Foundation")
    # ... implementation
    return foundation_grp

# ============================================================
# SECTION 2: FLOOR JOISTS (Modules, Sheathing)
# ============================================================
def create_floor_joists(doc, catalog, params):
    """Build floor joist modules with hardware and sheathing."""
    # ... implementation
    return floor_grp

# Main assembly
foundation_grp = create_foundation(doc, catalog, foundation_params)
floor_grp = create_floor_joists(doc, catalog, floor_params)
# ...
```

**Benefits**:
- Each section has clear purpose
- Functions are testable in isolation
- Easy to navigate (jump to `create_floor_joists`)
- Easy to understand (function name = intent)
- Reusable (call `create_foundation()` in other macros)

---

## Refactoring Strategy

### Phase 1: Documentation & Standards (Current)
- [x] Create REFACTORING_PLAN.md (this document)
- [ ] Create CODING_STANDARDS.md for BeachHouse
- [ ] Document current architecture issues
- [ ] Design target architecture

### Phase 2: Helper Module
- [ ] Create `FreeCAD/BeachHouse/macros/beach_common.py`
- [ ] Extract repeated helper functions
- [ ] Import lumber_common properly
- [ ] Add docstrings to all helpers

### Phase 3: Incremental Refactoring
- [ ] Section 1: Refactor foundation code
- [ ] Section 2: Refactor floor joist modules
- [ ] Section 3: Refactor walls
- [ ] Section 4: Refactor stairs
- [ ] Section 5: Refactor second floor
- [ ] Test after each section (visual comparison)

### Phase 4: Quality & Testing
- [ ] Add comprehensive docstrings
- [ ] Add inline comments for complex logic
- [ ] Visual regression test (compare old vs new model)
- [ ] BOM comparison (ensure identical part counts)
- [ ] Performance benchmark

### Phase 5: Documentation
- [ ] Update BeachHouse README.md
- [ ] Create architecture diagram
- [ ] Document module responsibilities
- [ ] Update AGENT_MEMORY.md

---

## Success Criteria

### Functional Requirements (Must Have)
1. ✅ Refactored macro produces **identical 3D model** (visual comparison)
2. ✅ BOM output matches original (part counts, labels, suppliers)
3. ✅ All groups created with correct hierarchy
4. ✅ No errors or warnings during execution

### Code Quality Requirements (Must Have)
1. ✅ Zero code duplication for catalog lookups
2. ✅ Consistent grouping pattern (100% of groups)
3. ✅ All functions have docstrings
4. ✅ Inline comments for non-obvious logic
5. ✅ Clear section headers with visual separators

### Performance Requirements (Should Have)
1. ✅ Macro execution time within 10% of original
2. ✅ Memory usage similar to original

### Maintainability Requirements (Must Have)
1. ✅ Functions follow Single Responsibility Principle
2. ✅ No function exceeds 100 lines
3. ✅ Maximum indentation depth: 4 levels
4. ✅ Clear separation between parameters, logic, and assembly

---

## Risk Assessment

### High Risk
**Risk**: Refactored code produces different geometry
**Mitigation**:
- Incremental refactoring (one section at a time)
- Visual comparison after each section
- Save old macro as `Build_950Surf.FCMacro.backup`

### Medium Risk
**Risk**: Breaking existing build scripts
**Mitigation**:
- Keep macro filename identical
- Maintain same environment variables
- Test `run_beach_house.sh` after refactoring

### Low Risk
**Risk**: Catalog structure incompatible with lumber_common
**Mitigation**:
- Review catalog.csv format early
- Ensure labels match lumber_common expectations
- Add missing fields if needed

---

## Timeline & Milestones

### Milestone 1: Documentation Complete (Current)
- REFACTORING_PLAN.md created ✅
- CODING_STANDARDS.md created (next)
- Architecture review complete (next)

### Milestone 2: Helper Module Ready
- beach_common.py created with docstrings
- All helpers tested individually
- Integration with lumber_common verified

### Milestone 3: Foundation Refactored
- Foundation section extracted to function
- Visual test passes
- BOM test passes

### Milestone 4: All Sections Refactored
- All code sections extracted
- All tests passing
- Performance benchmarks acceptable

### Milestone 5: Documentation & Polish
- All docstrings complete
- README updated
- AGENT_MEMORY updated

---

## Appendix A: Grouping Pattern Standard

**Recommended Pattern** (from Joist_Module_2x12_16x16.FCMacro):

```python
# 1. Create all parts first
created = []
created.append(make_rim("Rim_Left", thick / 2.0, module_width))
created.append(make_rim("Rim_Right", module_length - (thick / 2.0), module_width))

for idx, y_pos in enumerate(positions, start=1):
    created.append(make_joist(f"Joist_{idx}", y_pos, stock_length))

# 2. Create nested groups if needed
hanger_grp = doc.addObject("App::DocumentObjectGroup", "Joist_Hardware")
for h in hanger_objs:
    hanger_grp.addObject(h)

# 3. Create main group and attach all
group = doc.addObject("App::DocumentObjectGroup", "Joist_Module_2x12_16x16")
group.Label = "Joist_Module_2x12_16x16"
group.addObject(hanger_grp)
for obj in created:
    group.addObject(obj)
group.Group = created + [hanger_grp]  # Explicit assignment

# 4. Recompute
doc.recompute()
```

**Why This Works**:
1. Clear separation: create, nest, group, finalize
2. Explicit list management (`created`, `hanger_objs`)
3. Both `addObject()` AND `Group = list` for maximum compatibility
4. Single `recompute()` at end for performance

---

## Appendix B: File Structure After Refactoring

```
FreeCAD/BeachHouse/
├── macros/
│   ├── Build_950Surf.FCMacro          # Main assembly (refactored, ~1600 lines)
│   ├── beach_common.py                # Shared helpers (NEW)
│   ├── export_bom_beach.FCMacro       # BOM export
│   ├── snapshot_pile_spacing.FCMacro  # Visualization
│   └── catalog.csv                    # BeachHouse-specific catalog
├── docs/
│   ├── REFACTORING_PLAN.md            # This document
│   ├── CODING_STANDARDS.md            # Coding standards (NEW)
│   ├── ARCHITECTURE.md                # Architecture diagram (NEW)
│   ├── requirements.md                # Existing
│   └── decisions.md                   # Existing
├── builds/                            # Build outputs
├── README.md                          # Project overview
└── run_beach_house.sh                 # Build script
```

---

## Next Steps

1. Create `CODING_STANDARDS.md` with detailed examples
2. Create `beach_common.py` with extracted helpers
3. Begin incremental refactoring of foundation section
4. Document decisions in AGENT_MEMORY.md

---

**Dedication**: This work honors Luke Dombrowski. Stay Alive.
