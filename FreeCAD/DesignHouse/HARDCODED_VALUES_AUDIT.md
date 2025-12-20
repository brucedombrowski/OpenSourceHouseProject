# Hardcoded Values Audit - BeachHouse Template.FCMacro

**Date**: 2025-12-20
**Purpose**: Identify all hardcoded numbers in BeachHouse Template.FCMacro AND COMMENTS that should be config-driven
**Principle**: Template should be pure orchestration - all magic numbers from config
**Critical**: Comments with hardcoded dimensions become misleading when config changes

---

## COMMENTS WITH HARDCODED VALUES (Documentation Violations)

Comments that reference specific dimensions must derive those from config values, not hardcode them.

### 1. **Module Docstring Architecture Description** (Lines 5-11)
```python
"""
Architecture:
    - Foundation: 30 pilings (5x6 grid) with double beams and blocking
    - Floor: Two 16x16 joist modules with sheathing
    - Walls: 2x4 framing with window/door openings
"""
```
**Violation**: "30 pilings (5x6 grid)" hardcoded - should reference FOUNDATION["pile_grid_x"] × FOUNDATION["pile_grid_y"]
**Fix**: Use f-string or programmatic comment generation

### 2. **Foundation Docstring** (Lines 253-265)
```python
"""
Construction Sequence:
    1. Install pilings (30 ea, 12x12x40 PT, embedded 20' below grade)
    2. Install double beams on pile caps (2x12x16 PT, both sides of pile)
    3. Install blocking between beams at 4' and 12' (lateral support per IRC R502.7)
    ...
Design Rationale:
    - Pile grid: 5x6 = 30 piles @ 8' OC (matches joist module spacing)
    - Embed depth: 20' below grade (local code + storm surge + safety factor)
    - Above grade: 20' (elevated above max flood elevation per FEMA)
    - Beam span: 16' beam centered on 3 piles = 24' coverage
```
**Violations**:
- "30 ea, 12x12x40 PT, embedded 20' below grade" - all hardcoded
- "2x12x16 PT" - stock size hardcoded
- "at 4' and 12'" - blocking offsets hardcoded
- "5x6 = 30 piles @ 8' OC" - grid and spacing hardcoded
- "20' below grade" - embed depth hardcoded
- "20'" - above grade hardcoded
- "16' beam centered on 3 piles = 24' coverage" - beam length hardcoded

**Fix**: Replace with dynamic references or remove specific numbers from comments

### 3. **Lot Survey Comment** (Lines 107-118)
```python
# Calculate pile positions for 6x6 grid
# Center the pile grid on the lot (X direction)
# Total span: 5 gaps × 8' = 40'
pile_thickness_ft = 11.25 / 12.0  # 12x12 pile thickness in feet
```
**Violations**:
- "6x6 grid" - incorrect (should be 5x7 based on config)
- "5 gaps × 8' = 40'" - hardcoded calculation
- "12x12 pile thickness" - nominal size in comment (11.25 is correct actual size)

### 4. **Beam Parameters Comment** (Lines 120-126)
```python
# Beam parameters (2x12x16 PT, running along Y, double-beam config)
beam_row_step = 3          # Every 3rd row gets beams (spans 24' with 16' beam)
beam_gap_in = 0.0          # Gap between double beams (0 = tight to pile faces)

# Blocking parameters (between double beams, provides lateral support per IRC R502.7)
blocking_offsets_ft = [4.0, 12.0]  # Positions along 16' beam (4' and 12' from start)
```
**Violations**:
- "2x12x16 PT" - stock size hardcoded
- "spans 24' with 16' beam" - span and beam length hardcoded
- "along 16' beam" - beam length hardcoded

### 5. **Joist Module Comment** (Lines 133-138)
```python
# Joist module parameters (16x16 modules, 2x12 @ 16" OC)
module_x_ft = 16.0
module_y_ft = 16.0
module_joist_label = "joist_2x12_PT"
module_first_spacing_in = 14.5     # Front rim to first joist
module_joist_spacing_in = 16.0     # Remaining joists at 16" OC
```
**Violations**:
- "16x16 modules" - module size hardcoded
- "2x12 @ 16\" OC" - joist size and spacing hardcoded
- "14.5" - first spacing hardcoded
- "16.0" - OC spacing hardcoded

### 6. **Front Deck Comment** (Lines 566-577)
```python
# Front deck: 8' south of front setback, shifted 1.5" south to align house-side rim with front wall
front_deck_y_ft = front_setback_ft + y_spacing_ft - DECKS["front_deck_depth_ft"] - (1.5 / 12.0)
# Rear deck: starts at back edge of floor area
rear_deck_y_ft = front_setback_ft + y_spacing_ft + 40.0  # After 40' floor depth

# Deck X positioning: snap top-left corner of deck to bottom-left corner of first floor joists
# First floor joists start at floor_start_x_ft (calculated as (lot_x_ft - floor_width_ft) / 2.0)
# Deck layout: Left 16' + Center 8'9" + Right 16' = 40'9" total (40.75')
# Using 8'9" (105") center module cut from 10' stock (120" boards)
# Floor width: 16x16 + 8x16 + 16x16 = (195 + 99 + 195)/12 = 40.75' (including rim thicknesses)
floor_width_ft_local = (195.0 + 99.0 + 195.0) / 12.0  # ~40.75'
```
**Violations**:
- "8' south" - offset hardcoded
- "1.5\" south" - rim offset hardcoded
- "40' floor depth" - depth hardcoded
- "Left 16' + Center 8'9\" + Right 16' = 40'9\"" - all module sizes hardcoded
- "8'9\" (105\")" - center module width hardcoded
- "10' stock (120\" boards)" - stock length hardcoded
- "16x16 + 8x16 + 16x16 = (195 + 99 + 195)/12 = 40.75'" - all module dimensions hardcoded

### 7. **Floor Layout Comments** (Lines 732-791)
```python
# FRONT ROW (Y=20'): 16x16 + 8x16 + 16x16 = 40' wide × 16' deep
# Middle module width: 8' + 2 rims @ 1.5" each = 99"
# MIDDLE ROW (Y=36'): 16x8 + 8x8 + 16x8 = 40' wide × 8' deep
# BACK ROW (Y=44'): 16x16 + 8x16 + 16x16 = 40' wide × 16' deep
```
**Violations**:
- All row Y positions hardcoded (20', 36', 44')
- All module sizes hardcoded (16x16, 8x16, 16x8, 8x8)
- "8' + 2 rims @ 1.5\" each = 99\"" - calculation hardcoded
- Total widths and depths hardcoded (40', 16', 8')

### 8. **Floor Joist Z Position Comment** (Lines 879, 935)
```python
floor_z_top_mm = bc.ft(floor_params["floor_base_z_ft"]) + bc.inch(11.25)  # Top of joists
wall_z_base_in = (floor_params["floor_base_z_ft"] * 12.0) + 11.25 + 0.75  # Floor base + joist depth + sheathing
```
**Violations**:
- "11.25" - joist depth hardcoded in comment
- "0.75" - sheathing thickness hardcoded

### 9. **Sheathing Exclusion Comment** (Lines 900-902)
```python
# Create sheathing panels (exclude leftmost and rightmost 4' 4.5" for deck areas)
# 4' 4.5" = 4.375' exactly (52.5")
deck_exclusion_ft = 4.0 + (4.5 / 12.0)  # 4.375 feet
```
**Violations**:
- "4' 4.5\"" - exclusion dimension hardcoded in comment
- "4.375' exactly (52.5\")" - conversion hardcoded

### 10. **Wall Comment** (Lines 937-944)
```python
# Front wall: 32' wide (4 x 8' modules), aligned with sheathing
# Sheathing is 32' wide, centered on 40.75' floor
# Front wall shifts +8' east from sheathing left edge, bottom-left corners snap
...
front_wall_x_start_ft = sheathing_x_start_ft + 8.0
```
**Violations**:
- "32' wide (4 x 8' modules)" - wall width and module count/size hardcoded
- "32' wide, centered on 40.75' floor" - dimensions hardcoded
- "+8' east" - offset hardcoded

### 11. **Rear Wall Comment** (Lines 1046-1048)
```python
# Rear wall positioning: mirror of front wall, at back edge of sheathing
# Sheathing depth is 40' (480"), same as floor depth
sheathing_depth_ft = 40.0
```
**Violations**:
- "40' (480\")" - sheathing depth hardcoded

### 12. **Deck Surface Comments** (Lines 1147-1150, 1181-1222)
```python
# Front deck surface (3 x modules: left 16' + center 8'9" + right 16' = 40'9")
# Rear deck surface (3 modules: 16' + 8'9" + 16' = 40'9")
x_base=(deck_left_x_ft + 16.0 + (105.0 / 12.0)) * 12.0,  # 105" = 8.75'
```
**Violations**:
- "left 16' + center 8'9\" + right 16' = 40'9\"" - all module sizes hardcoded
- "105\" = 8.75'" - conversion hardcoded

---

## CODE HARDCODED VALUES (Should be in Config)

### 1. **Foundation Geometry** (Lines 97-117)
```python
embed_depth_ft = 20.0      # Below grade - SHOULD BE IN FOUNDATION config
pile_thickness_ft = 11.25 / 12.0  # 12x12 pile thickness - SHOULD USE pile_actual_size_in from config
```
**Fix**: Add to `FOUNDATION` config:
- `pile_embed_depth_ft`: 20.0
- Use existing `pile_actual_size_in` (11.25) instead of hardcoded value

---

### 2. **Beam Layout** (Lines 122-126)
```python
beam_row_step = 3          # Every 3rd row gets beams (spans 24' with 16' beam)
beam_gap_in = 0.0          # Gap between double beams (0 = tight to pile faces)
blocking_offsets_ft = [4.0, 12.0]  # Positions along 16' beam (4' and 12' from start)
```
**Fix**: Add to `FOUNDATION` config:
- `beam_row_interval`: 3 (every 3rd row)
- `beam_gap_in`: 0.0 (gap between double beams)
- `blocking_offsets_ft`: [4.0, 12.0] (blocking positions per IRC R502.7)

---

### 3. **Mid-Span Boards** (Lines 128-131)
```python
mid_board_offset_L_in = 1.5        # Left side offset
mid_board_offset_R_in = -(1.5 * 2.0)  # Right side offset
```
**Fix**: Add to `FOUNDATION` config:
- `mid_board_offset_left_in`: 1.5
- `mid_board_offset_right_in`: -3.0

---

### 4. **Joist Module Spacing** (Lines 137-138)
```python
module_first_spacing_in = 14.5     # Front rim to first joist
module_joist_spacing_in = 16.0     # Remaining joists at 16" OC
```
**Fix**: Add to `FIRST_FLOOR` config:
- `joist_first_spacing_in`: 14.5 (rim to first joist)
- `joist_oc_spacing_in`: 16.0 (standard on-center spacing)

---

### 5. **Sheathing Thickness** (Line 144)
```python
sheathing_thick_in = 0.75
```
**Fix**: Already partially in config as `sheathing_stock`, but thickness should be explicit:
- Add `sheathing_thickness_in`: 0.75 to `FIRST_FLOOR` config

---

### 6. **Joist Hanger Dimensions** (Lines 149-151)
```python
hanger_thickness_in = 0.06
hanger_height_in = 7.8125
hanger_seat_depth_in = 2.0
```
**Fix**: Add to `FIRST_FLOOR` config or new `HARDWARE` config:
- `hanger_thickness_in`: 0.06
- `hanger_height_in`: 7.8125 (for 2x12 joists)
- `hanger_seat_depth_in`: 2.0

---

### 7. **Lot Survey Origin Marker** (Lines 219-220)
```python
Part.makeLine(App.Vector(-bc.ft(1.0), 0, 0), App.Vector(bc.ft(1.0), 0, 0)),
Part.makeLine(App.Vector(0, -bc.ft(1.0), 0), App.Vector(0, bc.ft(1.0), 0)),
```
**Fix**: Add to `LOT` config:
- `origin_marker_size_ft`: 1.0

---

### 8. **Stairs Z Positions** (Line 538)
```python
stairs_grp = su.create_exterior_stairs(doc, STAIRS, floor_z_ft=above_grade_ft, slab_z_ft=0.0)
```
**Fix**: `slab_z_ft=0.0` is hardcoded - should come from `UTILITIES` or `CONCRETE_SLAB` config:
- `slab_z_ft`: 0.0 (grade level)

---

### 9. **Deck Positioning Offsets** (Lines 567, 569, 574-577)
```python
# Front deck shifted 1.5" south to align house-side rim with front wall
front_deck_y_ft = front_setback_ft + y_spacing_ft - DECKS["front_deck_depth_ft"] - (1.5 / 12.0)

rear_deck_y_ft = front_setback_ft + y_spacing_ft + 40.0  # After 40' floor depth

# Deck layout: Left 16' + Center 8'9" + Right 16' = 40'9" total
# Using 8'9" (105") center module cut from 10' stock (120" boards)
floor_width_ft_local = (195.0 + 99.0 + 195.0) / 12.0  # ~40.75'
```
**Fix**: Add to `DECKS` config:
- `front_deck_rim_offset_in`: 1.5 (alignment with front wall)
- `center_module_width_in`: 105.0 (8'9" center cut)
- `module_16_width_in`: 195.0 (16' module with rims)
- `module_8_width_in`: 99.0 (8' module with rims)

---

### 10. **Deck Module Coordinates** (Lines 588-646)
```python
x_base=deck_left_x_ft * 12.0,
y_base=front_deck_y_ft * 12.0,
...
x_base=(deck_left_x_ft + 16.0) * 12.0,
...
x_base=(deck_left_x_ft + 16.0 + (105.0 / 12.0)) * 12.0,  # 105" = 8.75'
```
**Fix**: These 16.0, 105.0 values should use the config values from item #9 above

---

### 11. **Floor Module Dimensions** (Lines 726-729, 835-836)
```python
middle_module_width_in = 99.0  # 8' + 2 rims @ 1.5" each = 99"
floor_width_ft = (195.0 + 99.0 + 195.0) / 12.0  # ~40.75'
floor_depth_ft = (192.0 + 96.0 + 192.0) / 12.0  # 40'
```
**Fix**: Add to `FIRST_FLOOR` config:
- `module_16x16_width_in`: 195.0
- `module_8x16_width_in`: 99.0
- `module_16x16_depth_in`: 192.0
- `module_16x8_depth_in`: 96.0

---

### 12. **Joist Depth for Floor Z Calculation** (Lines 879, 935)
```python
floor_z_top_mm = bc.ft(floor_params["floor_base_z_ft"]) + bc.inch(11.25)  # Top of joists
wall_z_base_in = (floor_params["floor_base_z_ft"] * 12.0) + 11.25 + 0.75  # Floor base + joist depth + sheathing
```
**Fix**: 11.25" is joist depth - should come from joist stock specs:
- Add `joist_depth_in`: 11.25 to `FIRST_FLOOR` config

---

### 13. **Deck Exclusion for Sheathing** (Lines 902, 910-911)
```python
# 4' 4.5" = 4.375' exactly (52.5")
deck_exclusion_ft = 4.0 + (4.5 / 12.0)  # 4.375 feet
...
exclude_left_ft=deck_exclusion_ft,  # Exclude leftmost 4' 4.5" for left deck
exclude_right_ft=deck_exclusion_ft,  # Exclude rightmost 4' 4.5" for right deck
```
**Fix**: Add to `FIRST_FLOOR` or `DECKS` config:
- `sheathing_deck_exclusion_ft`: 4.375 (4' 4.5")

---

### 14. **Wall Module Positioning** (Lines 944, 985-1030, 1080-1125)
```python
front_wall_x_start_ft = sheathing_x_start_ft + 8.0
...
rotate_wall_90(wall_left, x_offset_ft=0.0)
rotate_wall_90(wall_left_center, x_offset_ft=8.0)
rotate_wall_90(wall_right_center, x_offset_ft=16.0)
rotate_wall_90(wall_right, x_offset_ft=24.0)
```
**Fix**: Add to `WALLS` config:
- `front_wall_offset_from_sheathing_ft`: 8.0
- `wall_module_width_ft`: 8.0 (standard 8' module width)

---

### 15. **Wall Thickness** (Lines 960, 1060)
```python
wall.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), 90)
wall_y_ft_corner = rear_wall_y_ft - (3.5 / 12.0)  # Shift back by wall thickness
```
**Fix**: Add to `WALLS` config:
- `wall_thickness_in`: 3.5 (2x4 actual thickness)

---

### 16. **Sheathing Depth** (Line 1048)
```python
sheathing_depth_ft = 40.0
```
**Fix**: Should be calculated from module depths in config, not hardcoded

---

## Calculated Values (OK to remain - derived from config)

These are acceptable as they're **calculated from config values**, not hardcoded constants:

- Line 110: `total_pile_span_x_ft = (num_piles_x - 1) * x_spacing_ft` ✓
- Line 111: `pile_start_x_ft = (lot_x_ft - total_pile_span_x_ft) / 2.0` ✓
- Line 195-211: Lot boundary coordinates (derived from lot_x_ft, lot_y_ft, setbacks) ✓
- Line 332-333: Beam lengths from catalog ✓
- Line 360: Beam positioning math (derived from pile/beam dimensions) ✓
- Line 726: `lot_center_x_ft = params["lot_x_ft"] / 2.0` ✓
- Line 840: Floor centering calculation ✓

---

## Summary

**Total Hardcoded Values Found**: 16 categories
**Priority**: High - breaks parametric design principle

**Recommended Action**:
1. Create comprehensive config additions for all items above
2. Refactor template to use config values exclusively
3. Add validation to ensure all required config keys exist
4. Document calculations vs. constants in code comments

**Benefits of Fix**:
- True parametric design (change one number, update entire model)
- Easier to create variants (different foundation heights, deck layouts, etc.)
- Config becomes single source of truth
- Template becomes pure orchestration logic

---

**For Luke Dombrowski. Stay Alive.**
