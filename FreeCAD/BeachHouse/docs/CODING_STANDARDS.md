# BeachHouse Coding Standards

**Date**: 2025-12-19
**Purpose**: Construction-Grade Code for Real-World Building
**Users**: Human builders, future robotic fabrication systems

---

## Core Philosophy: Code as Construction Documents

> "This code generates real construction documents that real people will use to build a real house. Every line must be as clear as architectural drawings, as precise as shop drawings, and as reliable as engineering specifications."

### Guiding Principles

1. **Code Clarity = Builder Safety**
   - Confusing code → confusing BOMs → wrong materials → construction failures
   - Every object name must match what a builder would call it
   - Comments explain WHY (design intent), not WHAT (obvious from code)

2. **Metadata = Supply Chain**
   - Every part needs: supplier, SKU, URL, dimensions
   - Missing metadata = builder can't order parts
   - Catalog is single source of truth (like a spec book)

3. **Grouping = Assembly Instructions**
   - FreeCAD groups = construction phases
   - Group hierarchy mirrors build sequence
   - Foundation → Floor → Walls → Roof (in that order)

4. **BOM Accuracy = Cost Accuracy**
   - BOM must be 100% accurate for bidding
   - One missing joist hanger = construction stop
   - Part counts must match model exactly

5. **Future-Proof for Robotics**
   - Clean hierarchy enables automated fabrication
   - Precise positioning enables robotic assembly
   - Consistent naming enables AI interpretation

---

## Naming Conventions

### Rule 1: Use Construction Terminology

**Good** (builder understands immediately):
```python
rim_joist = make_rim_joist("Rim_Front", x=0, length=192)
top_plate = make_plate("Top_Plate_Front", height=108.125)
stud_king = make_stud("King_Stud_Left", height=104.625)
```

**Bad** (programmer jargon):
```python
obj1 = make_box("Object_1", 0, 192)
element = create_element("Elem_Top", 108.125)
vertical = make_vertical("V_Left", 104.625)
```

### Rule 2: Encode Location in Name

**Format**: `{ComponentType}_{Location}_{Index}`

**Examples**:
```python
"Pile_25_20"           # Pile at X=25', Y=20'
"Beam_East_Row3"       # East beam, 3rd row
"Joist_Front_12"       # 12th joist in front module
"Stud_Wall_Left_5"     # 5th stud in left wall
```

**Why**: Builder can locate part in model, identify it on site, verify placement.

### Rule 3: Group Names = Build Phases

**Hierarchy**:
```
Foundation
├── Piles
├── Beams
└── Blocking

First_Floor_Joists
├── Module_Front_Right
│   ├── Joists
│   └── Hardware
├── Module_Front_Left
└── Sheathing

First_Floor_Walls
├── Front_Walls
├── Back_Walls
├── Left_Walls
└── Right_Walls

Roofing
├── Rafters
├── Ridge_Beam
└── Sheathing
```

**Why**: Matches construction sequence. Subcontractor can find their scope immediately.

---

## Documentation Standards

### Function Docstrings (Construction Spec Format)

```python
def create_foundation(doc, catalog, params):
    """Build pile foundation with double beams and blocking.

    Construction Sequence:
        1. Install pilings (12x12x40 PT, embedded 20' below grade)
        2. Install double 2x12x16 beams on pile caps (both sides)
        3. Install blocking between beams at 4' and 12' from beam start
        4. Install mid-span boards at row transitions

    Materials (from catalog):
        - Pilings: 12x12x40_piling_PT (qty: 30, based on 5x6 grid)
        - Beams: beam_2x12x192_PT (qty: 30, double-beam config)
        - Blocking: beam_2x12x192_PT (cut to fit between beams)
        - Fasteners: Simpson strong-tie connectors per structural engineer

    Args:
        doc (FreeCAD.Document): Active FreeCAD document
        catalog (list): Catalog rows from lumber_catalog.csv + overrides
        params (dict): Foundation parameters:
            - pile_positions_ft: List of (x, y) pile coordinates
            - beam_rows: Which pile rows get beams
            - blocking_offsets_ft: Distance from beam start for blocking

    Returns:
        foundation_grp (DocumentObjectGroup): All foundation parts grouped by type:
            - Piles subgroup
            - Beams subgroup
            - Blocking subgroup

    Raises:
        ValueError: If pile_label or beam_label not found in catalog

    Notes:
        - Pile tops align at +20' above grade (above max flood elevation)
        - Beam top aligns with pile top (connection via Simpson cap)
        - Blocking provides lateral beam support per IRC R502.7
    """
    pass
```

**Why Each Section Matters**:
- **Construction Sequence**: Builder knows order of operations
- **Materials**: Builder can verify they have right parts before starting
- **Args**: Programmer knows inputs; builder knows what's configurable
- **Returns**: Programmer knows structure; builder knows how to find parts in model
- **Notes**: Critical build details (code, flood elevation, IRC references)

### Inline Comments (Build Notes Format)

```python
# Foundation Strategy:
# Pile grid: 5 columns (X) x 6 rows (Y) = 30 piles total
# X spacing: 8' OC (standard module width)
# Y spacing: 8' OC (matches joist module depth)
# Embed depth: 20' below grade (local code + storm surge + safety factor)
pile_base_z_in = -240.0  # -20' in inches

# Beam Placement:
# Every 3rd row gets double beams (rows 0, 3, 6, etc.)
# Double beam = one on each pile face (±0.75" from center)
# Spans 3 rows = 16' span (2x12 PT rated for 20' residential floor load)
beam_row_step = 3
beam_gap_in = 0.0  # Tight to pile faces; no gap

# Critical: beam top MUST align with pile top for Simpson cap connection
beam_top_z_in = pile_base_z_in + pile_len_in
beam_base_z_in = beam_top_z_in - beam_depth_in

# Blocking Strategy:
# Blocks installed at 4' and 12' along 16' beam (per IRC R502.7)
# Prevents beam twist under uneven floor loads
# Same 2x12 stock as beams; cut to fit between beam pair
blocking_offsets_ft = [4.0, 12.0]
```

**Why This Works**:
- **Context**: Explains design decisions (why 3 rows? IRC requirement)
- **Dimensions**: Called out explicitly (20', 16', 2x12)
- **Build Details**: Simpson cap, IRC code, load ratings
- **Traceability**: Can verify built house matches design

---

## Catalog Integration Standards

### Rule: Every Part MUST Have Catalog Entry

**Required Catalog Fields**:
```csv
label,nominal,actual_thickness_in,actual_width_in,length_in,supplier,sku_lowes,url_lowes,sku_hd,url_hd
12x12x40_piling_PT,12x12,11.25,11.25,480,lowes,SKU123,https://...,SKU456,https://...
beam_2x12x192_PT,2x12,1.5,11.25,192,lowes,SKU789,https://...,SKU012,https://...
```

**Why Each Field Matters**:
- `label`: Unique ID for code lookup
- `nominal`: What builders call it ("two by twelve")
- `actual_*`: Real dimensions for BOM accuracy
- `length_in`: Cut list generation
- `supplier`, `sku_*`, `url_*`: Purchasing (builders can click → buy)

### Catalog Lookup Pattern (Standard)

```python
from lumber_common import find_stock, attach_metadata

# 1. Look up part in catalog
row = find_stock(catalog_rows, "beam_2x12x192_PT")
if not row:
    raise ValueError(f"Part beam_2x12x192_PT not in catalog - cannot build")

# 2. Get actual dimensions (never hardcode dimensions!)
thick_in = float(row["actual_thickness_in"])
depth_in = float(row["actual_width_in"])
length_in = float(row["length_in"])

# 3. Create geometry
beam = Part.makeBox(inch(thick_in), inch(length_in), inch(depth_in))
obj = doc.addObject("Part::Feature", "Beam_East_Row3")
obj.Shape = beam

# 4. Attach metadata (supplier, SKU, color)
attach_metadata(obj, row, "beam_2x12x192_PT", supplier="lowes")
```

**Why This Pattern**:
- **Single source of truth**: Change catalog → all dimensions update
- **BOM accuracy**: Dimensions match catalog exactly
- **Supply chain**: Metadata enables automated ordering
- **Future-proof**: Adding new fields (weight, cost) requires no code changes

### Color Palette (Visual QA)

Colors encode part type for **visual quality assurance**:

```python
# lumber_common applies these automatically via attach_metadata()
NOMINAL_COLORS = {
    "2x4": (0.9, 0.35, 0.35),    # Red family
    "2x6": (0.95, 0.55, 0.25),   # Orange family
    "2x8": (0.95, 0.75, 0.2),    # Gold family
    "2x10": (0.4, 0.7, 0.35),    # Green family
    "2x12": (0.3, 0.5, 0.85),    # Blue family
    "4x8_panel": (0.25, 0.8, 0.9), # Cyan (panels)
    "hardware": (0.7, 0.7, 0.7),  # Gray (metal)
}
```

**Length Shading**:
- 8' stock = bright shade
- 12' stock = medium shade
- 16' stock = dark shade

**Builder Benefit**: Spot wrong part instantly
- All 2x12s are blue? ✅ Correct
- See red 2x4 where blue 2x12 should be? ❌ Fix model before cutting lumber

---

## Grouping Standards (Assembly Sequence)

### Rule: Groups Mirror Build Phases

**Why**: Subcontractor opens model → finds their phase → sees their parts.

```python
# Foundation subcontractor sees this:
Foundation
├── Piles (30 ea, installed first)
├── Beams (30 ea, installed after piles cure)
└── Blocking (20 ea, installed with beams)

# Framing subcontractor sees this:
First_Floor_Joists
├── Module_Front_Right (16x16 section)
│   ├── Joists (13 ea @ 16" OC)
│   └── Hardware (24 ea Simpson LU210 hangers)
├── Module_Front_Left (16x16 section, mirrored)
└── Sheathing (AdvanTech 4x8 panels)
```

### Standard Grouping Pattern

```python
def create_foundation(doc, catalog, params):
    # Create subgroups first (by trade/phase)
    piles_grp = doc.addObject("App::DocumentObjectGroup", "Piles")
    beams_grp = doc.addObject("App::DocumentObjectGroup", "Beams")
    blocking_grp = doc.addObject("App::DocumentObjectGroup", "Blocking")

    # Create all parts (accumulate in lists)
    piles = []
    for pos in pile_positions:
        pile = make_pile(f"Pile_{pos[0]}_{pos[1]}", pos)
        piles.append(pile)
        piles_grp.addObject(pile)

    beams = []
    for beam_def in beam_defs:
        beam = make_beam(beam_def.name, beam_def.pos)
        beams.append(beam)
        beams_grp.addObject(beam)

    # ... similar for blocking ...

    # Create parent group and attach subgroups
    foundation_grp = doc.addObject("App::DocumentObjectGroup", "Foundation")
    foundation_grp.addObject(piles_grp)
    foundation_grp.addObject(beams_grp)
    foundation_grp.addObject(blocking_grp)

    # Explicit group assignment (FreeCAD compatibility)
    foundation_grp.Group = [piles_grp, beams_grp, blocking_grp]

    return foundation_grp
```

**Why This Pattern**:
1. **Predictable**: Always create, group, attach, assign
2. **Compatible**: Works across FreeCAD versions
3. **Navigable**: Builder expands Foundation → sees Piles, Beams, Blocking
4. **Correct**: Parts appear in tree exactly where expected

---

## BOM Standards (Material Ordering)

### Rule: BOM Must Be 100% Accurate for Bidding

**BOM Format** (beach_bom.csv):
```csv
label,nominal,qty,length_in,supplier,sku,url,unit_cost,total_cost
12x12x40_piling_PT,12x12,30,480,lowes,SKU123,https://...,145.00,4350.00
beam_2x12x192_PT,2x12,30,192,lowes,SKU789,https://...,42.00,1260.00
hanger_LU210,hardware,156,N/A,lowes,SKU999,https://...,3.50,546.00
```

**Why Each Field**:
- `qty`: Exact count from model (builder orders this many)
- `length_in`: For cut list (which stock to order)
- `sku` / `url`: Click → add to cart
- `unit_cost` / `total_cost`: Accurate bidding

**BOM Generation Rules**:
1. Count every object in model (no manual counts)
2. Consolidate by label (30 piles with same label = qty 30)
3. Panels: round up to whole sheets (area-based, not piece count)
4. Hardware: count individually (156 hangers = 156 ea)

---

## Error Handling (Construction Failures)

### Rule: Fail Fast with Clear Messages

```python
# Good: Builder knows exactly what's wrong and how to fix it
row = find_stock(catalog_rows, pile_label)
if not row:
    raise ValueError(
        f"Pile part '{pile_label}' not found in catalog.\n"
        f"Check FreeCAD/BeachHouse/macros/catalog.csv.\n"
        f"Available pile labels: {[r['label'] for r in catalog_rows if 'piling' in r['label']]}"
    )

# Good: Validate construction logic
if embed_depth_ft < 15.0:
    raise ValueError(
        f"Pile embed depth {embed_depth_ft}' is less than minimum 15' required by local code.\n"
        f"Increase embed_depth_ft parameter to at least 15.0."
    )

# Bad: Silent failure or cryptic message
if not row:
    return None  # Builder has no idea what went wrong

if embed_depth_ft < 15.0:
    print("Warning: shallow piles")  # Prints to console, builder never sees it
```

**Why**:
- **Fast feedback**: Know immediately if model is unbuildable
- **Actionable**: Error message tells you how to fix it
- **Safe**: Better to refuse to generate bad model than generate unbuildable one

---

## Performance Standards

### Rule: Optimize for Large Models (Real Houses Are Big)

**Techniques**:
1. **Batch object creation**: Create all parts, then group (not create-group-create-group)
2. **Single recompute**: Call `doc.recompute()` once at end, not after every object
3. **Avoid redundant lookups**: Load catalog once, not per object

```python
# Good: Fast (one catalog load, batch creation, one recompute)
catalog_rows = load_catalog([catalog_path])
created = []
for i in range(100):
    row = find_stock(catalog_rows, label)  # Lookup from in-memory list
    obj = make_joist(f"Joist_{i}", row)
    created.append(obj)
doc.recompute()  # Once at end

# Bad: Slow (repeated file I/O, repeated recomputes)
for i in range(100):
    catalog_rows = load_catalog([catalog_path])  # Reload file 100 times!
    row = find_stock(catalog_rows, label)
    obj = make_joist(f"Joist_{i}", row)
    doc.recompute()  # 100 recomputes!
```

**Why**: 100-joist model takes 2 seconds vs 20 seconds. Scale to 500 parts = 10x faster.

---

## Testing Standards (Construction Verification)

### Visual Regression Test

```bash
# 1. Generate old model
LUMBER_SAVE_FCSTD=old_model.fcstd freecad Build_950Surf.FCMacro

# 2. Refactor code

# 3. Generate new model
LUMBER_SAVE_FCSTD=new_model.fcstd freecad Build_950Surf.FCMacro

# 4. Compare visually (human inspection)
freecad old_model.fcstd  # Rotate, inspect
freecad new_model.fcstd  # Rotate, inspect
# Should be IDENTICAL geometry
```

### BOM Verification Test

```bash
# 1. Generate old BOM
freecad export_bom_beach.FCMacro  # → beach_bom_old.csv

# 2. Refactor code

# 3. Generate new BOM
freecad export_bom_beach.FCMacro  # → beach_bom_new.csv

# 4. Diff BOMs
diff beach_bom_old.csv beach_bom_new.csv
# Should show ZERO differences in part counts
```

---

## Checklist: Code Review (Builder's Inspection)

Before committing refactored code:

- [ ] **Naming**: All objects use construction terminology?
- [ ] **Catalog**: All parts have catalog entries with SKU/URL?
- [ ] **Colors**: All parts have correct color palette?
- [ ] **Grouping**: Groups mirror construction phases?
- [ ] **Docstrings**: Functions document construction sequence?
- [ ] **Comments**: Complex logic has "why" comments?
- [ ] **BOM**: export_bom produces identical counts?
- [ ] **Visual**: Model looks identical to before refactoring?
- [ ] **Errors**: All errors have actionable messages?
- [ ] **Performance**: Model builds in similar time?

---

## Appendix: Real-World Build Constraints

### Constraint 1: Material Availability
- **Reality**: Not all lumber lengths available in all regions
- **Code Impact**: Catalog must support regional variations
- **Solution**: `catalog.csv` can be overridden per location

### Constraint 2: Code Compliance
- **Reality**: Building codes vary by jurisdiction (IRC, IBC, local amendments)
- **Code Impact**: Design decisions must reference code sections
- **Solution**: Comments cite code (e.g., "IRC R502.7 requires blocking")

### Constraint 3: Fabrication Tolerances
- **Reality**: Wood dimensions vary (2x12 is actually 1.5" x 11.25")
- **Code Impact**: Use actual dimensions from catalog, not nominal
- **Solution**: `attach_metadata()` pulls actual_thickness_in, actual_width_in

### Constraint 4: Weather/Durability
- **Reality**: Coastal house needs PT lumber below grade + above flood line
- **Code Impact**: Material selection must consider environment
- **Solution**: Catalog labels encode treatment (e.g., `_PT` suffix)

### Constraint 5: Robotic Fabrication (Future)
- **Reality**: CNC routers, robotic assemblers need precise coordinates
- **Code Impact**: Object placement must be programmatically accessible
- **Solution**: Clean hierarchy + consistent naming enables AI parsing

---

**Dedication**: Building for Luke. Stay Alive.
