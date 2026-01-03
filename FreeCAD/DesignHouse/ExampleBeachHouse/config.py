#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
950 Surf Beach House - Design Configuration
All design parameters in one place.

For Luke Dombrowski. Stay Alive.
"""

# ============================================================
# COORDINATE SYSTEM (FreeCAD Top-Down View)
# ============================================================
#
# Think of the lot as a 6-sided die viewed from above:
#
#   TOP/BOTTOM → Z axis (vertical, up/down)
#   FRONT/REAR → Y axis (horizontal, north/south)
#   LEFT/RIGHT → X axis (horizontal, east/west)
#
# Origin: (0, 0, 0) at southwest corner of lot, grade level
#
# X axis: Increases EAST (left → right when viewing from above)
# Y axis: Increases NORTH (front → rear when viewing from above, facing north)
# Z axis: Increases UP (bottom → top, grade → sky)
#
# Lot Centerlines:
#   EW Centerline: X = lot_width_ft / 2.0 = 25.0'
#                  (runs north-south down middle of lot)
#   NS Centerline: Y = lot_depth_ft / 2.0 = 50.0'
#                  (runs east-west across middle of lot)
#   Lot Center Point: (25', 50', 0) where both centerlines intersect
#
# Setback Naming (from property lines):
#   front_setback_ft → South edge (Y = front_setback_ft)
#   rear_setback_ft  → North edge (Y = lot_depth_ft - rear_setback_ft)
#   left_setback_ft  → West edge (X = left_setback_ft)
#   right_setback_ft → East edge (X = lot_width_ft - right_setback_ft)
#
# ============================================================
# LOT SURVEY
# ============================================================

LOT = {
    "width_ft": 50.0,  # Lot width (X direction, east-west)
    "depth_ft": 100.0,  # Lot depth (Y direction, north-south)
    "front_setback_ft": 20.0,  # Front (south) setback from property line
    "left_setback_ft": 5.0,  # Left (west) setback from property line
    "right_setback_ft": 5.0,  # Right (east) setback from property line
    "rear_setback_ft": 10.0,  # Rear (north) setback from property line
    "origin_marker_size_ft": 1.0,  # Origin cross marker size
}

# ============================================================
# FOUNDATION
# ============================================================
#
# DESIGN RATIONALE - Pile Placement Strategy
# ==========================================
#
# Goals:
#   1. Maximize house size for lot width (40' usable between setbacks)
#   2. Support 4' deck overhangs on east and west sides
#   3. Maximize pile spacing for ground-level usability (covered patio)
#   4. Maintain structural integrity for 2-story, 40'×60' house with 9' walls
#
# House Dimensions:
#   - Total footprint: 40' wide × 60' deep (east-west × north-south)
#   - Two stories with 9' ceiling height per floor
#   - 4' decking extends beyond pile line on east and west sides
#   - Foundation spans from front setback (Y=20') to rear setback area
#
# Pile Placement Logic (X direction - East/West):
#   - Outside faces of outermost pile columns align with setback lines
#   - West pile column: west face at X = left_setback_ft (5')
#   - East pile column: east face at X = lot_width - right_setback_ft (45')
#   - Interior piles evenly spaced between edge columns
#   - 5 pile columns total → 4 bays @ ~9.76' each (calculated at runtime)
#
#   Calculation:
#     pile_half_thickness = 11.25" / 24 = 0.46875'
#     west_pile_center = left_setback + pile_half = 5.46875'
#     east_pile_center = lot_width - right_setback - pile_half = 44.53125'
#     usable_span = east_center - west_center = 39.0625'
#     x_spacing = usable_span / (num_piles_x - 1) = 39.0625 / 4 = 9.765625'
#
# Pile Placement Logic (Y direction - North/South):
#   - Front pile row: front face at front setback line (Y=20')
#   - 7 pile rows at 10' O.C. for 20' LVL beam spans
#   - Total pile field depth: 60' (rows 1-7 spanning Y=20' to Y=80')
#
# Structural Considerations:
#   - LVL beams (1.75"×11.875"×20') span 20' between piles (3 piles per span)
#   - Each girder line has 3 segments: rows 1-3, 3-5, 5-7
#   - Piles at segment boundaries (rows 3, 5) get full-width notches
#   - Endpoint piles (rows 1, 7) get corner notches
#   - Through-bolts connect beams to piles (2 bolts per connection)
#
# Covered Patio Usability:
#   - ~10' pile spacing in Y direction provides clear spans for parking/patio
#   - ~10' pile spacing in X direction minimizes visual obstruction
#   - 20' clear height under house (40' piles - 20' embedment)
#
FOUNDATION = {
    # Pile grid (calculated: grid_x × grid_y = total piles, footprint spans)
    # NOTE: pile_spacing_x_ft is CALCULATED at runtime based on setbacks and pile count
    # Outside pile faces align with setback lines, interior piles evenly spaced
    "pile_spacing_x_ft": 9.765625,  # CALCULATED: ~9' 9-3/16" (see rationale above)
    "pile_spacing_y_ft": 10.0,  # Pile spacing in Y direction (10' OC for 20' LVL beams)
    "pile_grid_x": 5,  # Number of piles in X direction (east-west)
    "pile_grid_y": 7,  # Number of piles in Y direction (7 rows for LVL beam system)
    "pile_size_in": 12.0,  # Pile cross-section nominal
    "pile_actual_size_in": 11.25,  # Pile actual dimensions
    "pile_length_ft": 40.0,  # Pile length
    "pile_embed_depth_ft": 20.0,  # Embed depth below grade (local code + storm surge + safety factor)
    # LVL beams (2-ply laminated assemblies)
    "lvl_label": "lvl_1.75x11.875x240",  # LVL catalog key (1.75"×11.875"×20')
    "beam_stock": "2x12x192",  # OLD: Beam stock label (16' beams) - DEPRECATED
    "beam_stock_short": "2x12x96",  # OLD: Short beam stock (8' beams) - DEPRECATED
    "beam_pressure_treated": True,  # Use PT lumber for beams
    "beam_row_interval": 3,  # Every Nth pile row gets beams
    "beam_gap_in": 0.0,  # Gap between double beams (0 = tight to pile faces)
    "blocking_offsets_ft": [4.0, 12.0],  # Blocking positions per IRC R502.7 (lateral support)
    # Mid-span boards (additional support between pile rows)
    "mid_board_offset_left_in": 1.5,  # Left side offset
    "mid_board_offset_right_in": -3.0,  # Right side offset
    # Elevation
    "grade_z_ft": 0.0,  # Grade level (datum)
    # NOTE: above_grade_ft is CALCULATED (pile_length_ft - pile_embed_depth_ft) in BeachHouse Template.FCMacro
}

# ============================================================
# FIRST FLOOR
# ============================================================

FIRST_FLOOR = {
    # Joists
    "joist_stock": "2x12x192",  # Joist stock label
    "joist_depth_in": 11.25,  # Joist actual depth (from catalog)
    "joist_first_spacing_in": 14.5,  # Front rim to first joist
    "joist_spacing_oc_in": 16.0,  # Joist spacing on-center
    "joist_pressure_treated": False,
    # Sheathing
    "sheathing_stock": "panel_advantech_4x8",
    "sheathing_thickness_in": 0.75,  # 3/4" Advantech
    "sheathing_deck_exclusion_ft": 4.375,  # Exclude for deck areas (4' 4.5")
    # Joist hangers (Simpson LU210 or equivalent for 2x12)
    "hanger_thickness_in": 0.06,
    "hanger_height_in": 7.8125,
    "hanger_seat_depth_in": 2.0,
    # Floor module dimensions (actual with rims)
    # 3×3 grid of 16'×16' modules = 48' × 48' total floor area
    "module_16x16_width_in": 195.0,  # 16' module + rims (192" + 3" for rim overlap)
    "module_16x16_depth_in": 192.0,  # 16' module depth
    # Layout (assembly-based, no hard-coded offsets!)
    "start_x_ft": 9.0,  # X position for first module (centered on lot)
    "start_y_ft": 20.0,  # Y position (front setback)
    # NOTE: base_z_ft is CALCULATED (= above_grade_ft) in BeachHouse Template.FCMacro
}

# ============================================================
# WALLS
# ============================================================

WALLS = {
    # Framing
    "stud_stock": "2x4x96",  # Wall stud stock
    "plate_stock": "2x4x96",  # Top/bottom plate stock
    "wall_height_in": 96.0,  # Wall height
    "wall_thickness_in": 3.5,  # 2x4 actual thickness
    # Positioning (relative to sheathing)
    "front_wall_offset_from_sheathing_ft": 8.0,  # Wall starts 8' east of sheathing left edge
    "wall_module_width_ft": 8.0,  # Standard wall module width
}

# ============================================================
# DECKS
# ============================================================

DECKS = {
    # Front deck (south side) - 16x12 modules with joists running N-S
    "front_deck_depth_ft": 12.0,  # Deck projects south from front wall (12' for 16x12 modules)
    "front_deck_rim_offset_in": 1.5,  # Rim alignment offset with front wall
    # Rear deck (north side)
    "rear_deck_depth_ft": 4.0,  # Deck projects north from rear wall (TEST: 4' instead of 8')
    # Deck module dimensions (with rims)
    "module_16_width_in": 195.0,  # 16' module with rims
    "module_8_width_in": 99.0,  # 8' module with rims
    "center_module_width_in": 105.0,  # 8'9" center cut from 10' stock
    "module_depth_ft": 8.0,  # Module depth
    # NOTE: Deck board dimensions come from lumber_catalog.csv (single source of truth)
    # See: deckboard_5_4x6x192_PT for thickness, width, etc.
    #
    # STAIR OPENING in Front_Deck_Right_16x12
    # =======================================
    # For double-L stair access through front deck:
    #   - Joists 3-8 are shortened (cut at front rim, replaced with shorter joists)
    #   - Header joist runs E-W to frame the opening and support shortened joists
    #   - Opening allows stair Run 1 (descending east) to clear the deck framing
    #
    "stair_opening": {
        "module": "Front_Deck_Right_16x12",  # Which deck module has the opening
        "shortened_joists": [3, 4, 5, 6, 7, 8],  # Joist indices to shorten (1-based, joist names)
        "header_between_joists": [2, 9],  # Header spans between Joist_2 and Joist_9
        # Joists 3-8 connect to front rim (south) and header (north)
        # Instead of running full length to back rim
    },
}

# ============================================================
# SECOND FLOOR (20' LVL rims × 12' 2x12 joists)
# ============================================================
#
# DESIGN RATIONALE - Second Floor Joist Modules
# ==============================================
#
# Goals:
#   1. Match first floor footprint (40' × 48')
#   2. Use LVL beams as rim joists for 20' spans (E-W)
#   3. Use 2x12 joists at 12' spans (N-S)
#   4. Modular grid: 2 columns × 4 rows = 8 modules
#
# Module Dimensions:
#   - 20' wide (E-W) × 12' deep (N-S) per module
#   - LVL rims: 1.75" × 11.875" × 20' (lvl_1.75x11.875x240)
#   - 2x12 joists: 1.5" × 11.25" × 12' at 16" OC
#   - Total floor: 40' × 48' (2 × 20' wide, 4 × 12' deep)
#
# Grid Layout (viewed from above, north up):
#   +----------+----------+
#   | Row 4 L  | Row 4 R  |  <- North (Y = 20' + 48' = 68')
#   +----------+----------+
#   | Row 3 L  | Row 3 R  |
#   +----------+----------+
#   | Row 2 L  | Row 2 R  |
#   +----------+----------+
#   | Row 1 L  | Row 1 R  |  <- South (Y = 20')
#   +----------+----------+
#   ^          ^          ^
#   X=5'       X=25'      X=45' (approx, depends on rim thicknesses)
#
# Z Position:
#   - Second floor sits on top of first floor walls
#   - Base Z = first floor Z + joist depth + sheathing + wall height
#   - Typically: 20' (above grade) + 11.25" (joist) + 0.75" (sheathing) + 8' (wall) = ~29' above grade
#

SECOND_FLOOR = {
    # Module layout (2 columns × 4 rows = 8 modules)
    "grid_columns": 2,  # Columns in X direction (E-W)
    "grid_rows": 4,  # Rows in Y direction (N-S)
    # Module dimensions
    "module_width_ft": 20.0,  # Module width (E-W, LVL rim direction)
    "module_depth_ft": 12.0,  # Module depth (N-S, joist direction)
    # LVL rim joists (run E-W, front/back of each module)
    "rim_stock": "lvl_1.75x11.875x240",  # 20' LVL beams
    "rim_thickness_in": 1.75,  # LVL actual thickness
    "rim_depth_in": 11.875,  # LVL actual depth
    # 2x12 joists (run N-S at 16" OC)
    "joist_stock": "2x12x144",  # 12' joists
    "joist_thickness_in": 1.5,  # 2x12 actual thickness
    "joist_depth_in": 11.25,  # 2x12 actual depth
    "joist_spacing_oc_in": 16.0,  # Joist spacing on-center
    "joist_first_spacing_in": 14.5,  # First joist at 14.5" for sheathing alignment
    "joist_pressure_treated": False,
    # Sheathing
    "sheathing_stock": "panel_advantech_4x8",
    "sheathing_thickness_in": 0.75,  # 3/4" Advantech
    # Joist hangers
    "hanger_label": "hanger_LU210",
    # Positioning (relative to first floor walls)
    # Second floor aligns with first floor wall edges (not sheathing)
    # Left wall X = sheathing_x_start = floor_start_x + deck_exclusion = 0.625 + 4.375 = 5.0'
    # First floor Y start = front_setback + y_spacing = 20 + 10 = 30'
    "start_x_ft": 5.0,  # X position = left wall west face (aligns LVL rim to wall)
    "start_y_ft": 30.0,  # Y position = front_setback (20') + y_spacing (10')
    # NOTE: base_z_ft is CALCULATED in BeachHouse Template.FCMacro:
    #   base_z_ft = first_floor_z + joist_depth + sheathing + wall_height
}

# ============================================================
# ROOF
# ============================================================

ROOF = {
    # Rafters
    "rafter_stock": "2x6x144",  # Rafter stock (12')
    "rafter_spacing_oc_in": 24.0,  # Rafter spacing
    # Pitch
    "pitch_rise": 6,  # Roof pitch rise (6:12)
    "pitch_run": 12,  # Roof pitch run
    # Sheathing
    "sheathing_stock": "plywood_0.5x4x8",
}

# ============================================================
# SEPTIC SYSTEM (Northern/back part of lot)
# ============================================================

SEPTIC_SYSTEM = {
    # Septic tank position (northern back part of lot)
    # Tank is centered on the north-south drainage run at X=37.0' (gap middle between pile columns 4 and 5)
    "tank_x_ft": 37.0,  # Aligned with north-south drainage run (gap middle)
    "tank_y_ft": 88.0,  # Northern (back) part of lot (moved north to clear rear deck piles)
    "tank_length_ft": 10.0,  # Typical 1000-1500 gallon tank (runs along Y direction)
    "tank_width_ft": 5.0,  # Tank width (runs along X direction, centered at X=37.0')
    "tank_depth_ft": 5.0,  # Underground
    # Leach field (drain field)
    "leach_field_x_start_ft": 10.0,  # West side of tank
    # NOTE: leach_field_y_start_ft is CALCULATED in BeachHouse Template.FCMacro:
    #   - Derived from last pile Y position + pile_half_thickness + 2' clearance
    #   - This ensures leach field is always north of piles regardless of pile grid config
    "leach_field_y_start_ft": 82.5,  # Placeholder - overridden at runtime (2' north of last pile row)
    "leach_field_length_ft": 30.0,  # 3 trenches × 5' spacing (fits within lot)
    "leach_field_width_ft": 20.0,  # Trench width + spacing
    "leach_field_trench_count": 3,
    "leach_field_trench_spacing_ft": 5.0,  # Reduced from 10' to 5' to fit within lot (rear setback at Y=90')
    # Drain line from house to tank (routed around piles)
    "drain_line_diameter_in": 4.0,  # 4" PVC drain
    "drain_line_depth_in": 24.0,  # 2' below grade (frost line + code)
    # NOTE: stub_up_x_ft and stub_up_y_ft are CALCULATED in BeachHouse Template.FCMacro:
    #   - Derived from pile [3,4] (0-based) position + east face offset + pipe radius
    #   - This ensures drain stub is always at pile east face regardless of pile grid config
    #   - Aligns with stair module at Floor_Middle_Right_16x8
    "stub_up_x_ft": 33.635,  # Placeholder - overridden at runtime
    "stub_up_y_ft": 52.46875,  # Placeholder - overridden at runtime
    # Drain line routing strategy:
    # 1. Vertical stub-up through concrete slab at pile 4,5 east face: (33.635, 52.46875)
    # 2. Underground 90-degree elbow at slab bottom (Z=-24")
    # 3. Underground horizontal run EAST (with slope) to gap middle: (33.635, 52.46875) → (37.0, 52.46875)
    # 4. Underground 90-degree elbow at gap middle
    # 5. Underground horizontal run NORTH (with slope) in pile gap to tank: (37.0, 52.46875) → (37.0, 88.0)
    # Tank is centered at X=37.0' so north-south run goes straight into tank inlet
    "drain_line_lateral_x_ft": 37.0,  # X position for vertical drop (gap middle between pile columns 4 and 5)
    "drain_line_waypoint_x_ft": 37.0,  # Same as lateral (no turn needed - straight run to tank)
    "drain_line_waypoint_y_ft": 88.0,  # North to tank Y position (tank inlet)
}

# ============================================================
# UTILITIES (Plumbing and Electrical Stub-Ups)
# ============================================================

UTILITIES = {
    # Concrete slab (under house - covers pile area within setbacks)
    "slab_thickness_in": 6.0,  # 6" concrete (driveway grade)
    # NOTE: slab_x_start_ft, slab_y_start_ft, slab_width_ft, slab_depth_ft are CALCULATED
    #   in BeachHouse Template.FCMacro based on setback lines:
    #   - Slab MUST stay within setback lines (cannot protrude into 5' side setbacks)
    #   - West/East edges: align with left/right setback lines
    #   - South edge: aligns with front setback line
    #   - North edge: 6" north of last pile row
    "slab_x_start_ft": 5.0,  # Placeholder - overridden at runtime
    "slab_y_start_ft": 20.0,  # Placeholder - overridden at runtime
    "slab_width_ft": 40.0,  # Placeholder - overridden at runtime
    "slab_depth_ft": 60.0,  # Placeholder - overridden at runtime
    # Water supply (from street, south side Y=0)
    "water_service_line_diameter_in": 1.0,  # 1" PVC water supply (typical residential)
    "water_service_depth_in": 42.0,  # 3.5' below grade (below frost line per IRC P2603.6)
    # NOTE: water_stub_x_ft and water_stub_y_ft are CALCULATED in BeachHouse Template.FCMacro:
    #   - Derived from pile [4,3] (0-based) position + west face offset - pipe radius
    #   - This ensures water stub is always at pile west face regardless of pile grid config
    "water_stub_x_ft": 40.49,  # Placeholder - overridden at runtime
    "water_stub_y_ft": 44.46875,  # Placeholder - overridden at runtime
    "water_entry_from_street_y_ft": 0.0,  # Street connection point (lot south edge)
    # Route: north-south in pile gap at X=37.0' (middle between pile columns 4 and 5)
    "water_lateral_x_ft": 37.0,  # X position for north-south run (gap middle)
    # Electrical service (from street, south side Y=0)
    "electrical_service_conduit_diameter_in": 2.5,  # 2.5" Schedule 40 PVC conduit (200A service per NEC 310.12)
    "electrical_service_depth_in": 24.0,  # 2' below grade (min depth per NEC 300.5 for PVC conduit under concrete)
    # NOTE: electrical_stub_x_ft, electrical_stub_y_ft, electrical_equipment_x_ft, electrical_equipment_y_ft
    #   are CALCULATED in BeachHouse Template.FCMacro:
    #   - Derived from pile [3,3] (0-based) position + east face offset
    #   - electrical_stub is offset 6" north from pile center for spacing from water
    #   - electrical_equipment is centered on pile for meter/disconnect/panel mounting
    "electrical_stub_x_ft": 33.51,  # Placeholder - overridden at runtime
    "electrical_stub_y_ft": 44.96875,  # Placeholder - overridden at runtime
    "electrical_entry_from_street_y_ft": 0.0,  # Street connection point
    # Route: north-south in pile gap at X=37.0' (middle between pile columns 4 and 5)
    "electrical_lateral_x_ft": 37.0,  # X position for north-south run (gap middle)
    # Electrical infrastructure (meter -> disconnect -> panel) - stacked vertically at pile [3,3]
    # Equipment mounted on pile east face, centered on pile (not on offset stub-up)
    "electrical_equipment_x_ft": 33.51,  # Placeholder - overridden at runtime
    "electrical_equipment_y_ft": 44.46875,  # Placeholder - overridden at runtime
    # Meter box: 200A residential meter, bottom at 4' above slab
    "meter_box_offset_z_in": 48.0,  # Bottom at 4' above slab (accessible height)
    # Disconnect: 200A service disconnect, stacked above meter (NEC 230.70)
    # Position calculated: meter_bottom(48") + meter_height(28") + gap(2") = 78" bottom
    # Panel: 200A main breaker, 40-circuit load center, stacked above disconnect (temporary)
    # Position calculated: disconnect_bottom(78") + disconnect_height(20") + gap(2") = 100" bottom
    # NOTE: Panel will be relocated to interior wall in house later (NEC 110.26)
    # Plumbing stub-ups (drain/waste/vent for 3 zones)
    # DISABLED: All waste drains route to the main septic drain at pile 4,5
    "plumbing_stub_positions": [
        # {"name": "Kitchen", "x_ft": 15.0, "y_ft": 30.0, "diameter_in": 4.0},
        # {"name": "Bath", "x_ft": 35.0, "y_ft": 40.0, "diameter_in": 4.0},
        # {"name": "Laundry", "x_ft": 25.0, "y_ft": 50.0, "diameter_in": 4.0},
    ],
}

# ============================================================
# STAIRS (from concrete slab to house floor)
# ============================================================
#
# DOUBLE-L STAIR DESIGN - Wraps around east side of front deck
# =============================================================
#
# Design: Double-L stair with 3 runs and 2 landings (east -> north -> west)
#
#   DECK SURFACE (Z=252.25")
#   |
#   | 4' deck landing (walkway from elevator to stair opening)
#   |
#   v
#   [Tread 0] -----> EAST (Run 1: descend east, oriented N-S)
#   [Tread 1]
#   ...
#   [Tread N]
#   |
#   [Landing 1] <--- 90° left turn (to north)
#   |
#   [Tread N+1] ---> NORTH (Run 2: descend north, oriented E-W)
#   ...
#   [Tread 2N]
#   |
#   [Landing 2] <--- 90° left turn (to west)
#   |
#   [Remaining] <--- WEST (Run 3: descend to slab, oriented N-S)
#   ...
#   SLAB (Z=0")
#
# Tread 0 orientation:
#   - Runs N-S (3' wide in Y direction)
#   - Descends EAST (+X direction)
#   - WEST face aligns with EAST face of Front_Deck_Right_16x12_Joist_2
#

# Stair parameters defined before STAIRS dict for use in calculations
_STAIR_TREAD_WIDTH_FT = 3.0  # Stair width (36" minimum per IRC R311.7.1)
_STAIR_DECK_LANDING_FT = 4.0  # Deck landing depth (from elevator to stair opening)
_STAIR_LANDING_SIZE_FT = 3.0  # Turn landing size (36" x 36" per IRC R311.7.6)

# Calculate tread 0 X position:
# Front_Deck_Right origin X = floor_start_x + 2 * 192" (two 16' deck modules)
# floor_start_x = (50' - 3*16.25')/2 = 0.625'
# Front_Deck_Right origin = 0.625' + 32' = 32.625' = 391.5"
# Joist_2 center = origin + 15.25" (first joist) + 16" (one spacing) = origin + 31.25"
# Joist_2 east face = origin + 31.25" + 0.75" (half thickness) = origin + 32"
# Absolute: 391.5" + 32" = 423.5" = 35.292'
_FLOOR_START_X_FT = (LOT["width_ft"] - 3 * (FIRST_FLOOR["module_16x16_width_in"] / 12.0)) / 2.0
_FRONT_DECK_RIGHT_ORIGIN_X_FT = _FLOOR_START_X_FT + 2 * 16.0  # Two 16' modules
_JOIST_2_EAST_FACE_IN = (
    _FRONT_DECK_RIGHT_ORIGIN_X_FT * 12.0
) + 32.0  # 31.25 + 0.75 from module origin
_STAIR_TREAD0_X_FT = _JOIST_2_EAST_FACE_IN / 12.0  # Tread 0 west face at joist 2 east face

STAIRS = {
    # Double-L stairs from first floor (Z=20') down to slab (Z=0')
    # East side of front deck, wrapping around toward west
    #
    # Tread 0 X alignment:
    # - Tread 0 WEST face aligns with EAST face of Front_Deck_Right_16x12_Joist_2
    #
    # Tread 0 Y alignment:
    # - South face at 4' deck landing north of front deck front rim (for elevator walkway)
    #
    "stair_x_ft": _STAIR_TREAD0_X_FT,  # Tread 0 west face X position
    "stair_y_snap_ft": (
        LOT["front_setback_ft"]  # Front setback line (Y=20')
        + FOUNDATION["pile_spacing_y_ft"]  # Plus pile spacing (10')
        - DECKS["front_deck_depth_ft"]  # Minus deck depth (12')
        - DECKS["front_deck_rim_offset_in"] / 12.0  # Minus rim offset (0.125')
        + _STAIR_DECK_LANDING_FT  # Plus deck landing depth (4' from front rim)
    ),  # Tread 0 south face at 4' north of front deck front rim
    "tread_rise_in": 7.25,  # Riser height (7.25" per IRC R311.7.5.1 max 7-3/4")
    "tread_run_in": 11.25,  # Tread depth (11.25" = 2x12 actual width)
    "tread_width_ft": _STAIR_TREAD_WIDTH_FT,  # Stair width (36" minimum per IRC R311.7.1)
    "tread_stock": "2x12x96_PT",  # Tread material (2x12 PT lumber)
    # Headroom clearance (IRC R311.7.2 requires minimum 80" vertical clearance)
    "headroom_clearance_in": 80.0,  # 6'8" minimum headroom from tread to joist bottom
    #
    # DOUBLE-L STAIR CONFIGURATION
    # ============================
    "stair_type": "double_L",  # "straight", "L", or "double_L"
    #
    # Run 1: Descends EAST from deck opening
    # - Treads oriented N-S (3' in Y direction)
    # - Descending toward +X (east)
    "run1_direction": "east",  # Descending direction for Run 1
    "run1_tread_count": 6,  # Number of treads in Run 1
    #
    # Landing 1: 90° left turn (east -> north)
    "landing1_size_ft": _STAIR_LANDING_SIZE_FT,  # 3' x 3'
    "landing1_turn": "left",  # 90° left = from east to north
    #
    # Run 2: Descends NORTH
    # - Treads oriented E-W (3' in X direction)
    # - Descending toward +Y (north)
    # - Only 2 treads to stay within pile box
    "run2_direction": "north",  # Descending direction for Run 2
    "run2_tread_count": 2,  # Number of treads in Run 2 (short run to stay in pile box)
    #
    # Landing 2: 90° left turn (north -> west)
    "landing2_size_ft": _STAIR_LANDING_SIZE_FT,  # 3' x 3'
    "landing2_turn": "left",  # 90° left = from north to west
    #
    # Run 3: Descends WEST (short run before L-turn)
    # - Treads oriented N-S (3' in Y direction)
    # - Descending toward -X (west)
    "run3_direction": "west",  # Descending direction for Run 3
    "run3_tread_count": 4,  # 4 treads before Landing 3 (tread 5 becomes landing)
    #
    # Landing 3: 90° left turn (west -> south)
    "landing3_size_ft": _STAIR_LANDING_SIZE_FT,  # 3' x 3'
    "landing3_turn": "left",  # 90° left = from west to south
    #
    # Run 4: Descends SOUTH (3 treads)
    # - Treads oriented E-W (3' in X direction)
    # - Descending toward -Y (south)
    "run4_direction": "south",  # Descending direction for Run 4
    "run4_tread_count": 3,  # 3 treads before Landing 4
    #
    # Landing 4: 90° left turn (south -> east)
    "landing4_size_ft": _STAIR_LANDING_SIZE_FT,  # 3' x 3'
    "landing4_turn": "left",  # 90° left = from south to east
    #
    # Run 5: Descends EAST (4 treads before Landing 5)
    # - Treads oriented N-S (3' in Y direction)
    # - Descending toward +X (east)
    "run5_direction": "east",  # Descending direction for Run 5
    "run5_tread_count": 4,  # 4 treads before Landing 5
    #
    # Landing 5: 90° left turn (east -> north)
    "landing5_size_ft": _STAIR_LANDING_SIZE_FT,  # 3' x 3'
    "landing5_turn": "left",  # 90° left = from east to north
    #
    # Run 6: Descends NORTH to slab (remaining treads)
    # - Treads oriented E-W (3' in X direction)
    # - Descending toward +Y (north)
    "run6_direction": "north",  # Descending direction for Run 6
    # run6_tread_count is CALCULATED at runtime
}

# ============================================================
# DRIVEWAY
# ============================================================

DRIVEWAY = {
    # Driveway slab position (full buildable width from street)
    "slab_x_start_ft": 5.0,  # Start at buildable area (west side setback)
    "slab_y_start_ft": 0.0,  # Start at street (lot south edge)
    "slab_width_ft": 40.0,  # 40' wide (full buildable width)
    "slab_depth_ft": 20.0,  # 20' deep (from street toward house, stops at front setback)
    "slab_thickness_in": 6.0,  # 6" thick concrete (driveway grade, ACI 332)
    # Rebar
    "rebar_spacing_in": 12.0,  # #4 rebar @ 12" OC both ways
    "rebar_diameter_in": 0.5,  # #4 rebar (1/2" diameter)
}

# ============================================================
# MATERIALS
# ============================================================

MATERIALS = {
    # Default suppliers
    "default_supplier": "lowes",
    # Pressure treatment
    "foundation_pt": True,  # Foundation lumber is PT
    "floor_pt": False,  # Floor joists not PT
    "wall_pt": False,  # Wall framing not PT
}

# ============================================================
# ELEVATOR
# ============================================================

ELEVATOR = {
    # Position (south face of house, east edge - SE corner)
    # elevator_x_ft is the APPROXIMATE center X position (user-specified)
    # The deck railing code will snap the elevator to align with railing post positions
    # so that removing sections creates a clean opening
    "elevator_x_ft": 42.0,  # Approximate X position (will be centered in railing opening)
    # NOTE: elevator_y_ft is CALCULATED in BeachHouse Template.FCMacro:
    #   - North face of elevator POSTS aligns with south face of front deck rim
    # Platform dimensions
    "platform_width_ft": 4.0,  # 4' wide (ADA accessible, 48" min for wheelchair)
    "platform_depth_ft": 5.0,  # 5' deep
    # NOTE: travel_height_ft is CALCULATED (= above_grade_ft) in beach_elevator.py
}

# ============================================================
# BUILD OPTIONS
# ============================================================

BUILD = {
    # What to include in build (reduced set for faster iteration)
    "include_lot_survey": True,
    "include_septic_system": False,  # Septic tank, leach field, drain lines
    "include_utilities": False,  # Water/electrical service lines, stub-ups, meters, hose bibs
    "include_driveway": False,  # Driveway slab with rebar
    "include_elevator": True,  # Beach house elevator (open metal lift)
    "include_foundation": True,  # LVL beam system on pilings (piles only, no beams)
    "include_concrete_slab": True,  # Concrete slab under house
    "include_deck_joists": True,  # Deck joists, rims, hangers (installed BEFORE sheathing)
    "include_first_floor": True,  # 3×3 grid: 40' × 48'
    "include_stairs": True,  # Exterior stairs from slab to first floor (built early for access)
    "include_walls": False,  # Front and rear walls
    "include_deck_surface": False,  # Deck boards (installed AFTER stairs)
    "include_deck_railings": False,  # Deck railing posts
    "include_second_floor": False,  # 20' LVL rims × 12' 2x12 joists
    "include_roof": False,  # Not yet implemented
    # Output options
    "save_fcstd": True,
    "export_bom": True,
    "create_snapshots": True,
}
