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
    "rear_deck_depth_ft": 8.0,  # Deck projects north from rear wall
    # Deck module dimensions (with rims)
    "module_16_width_in": 195.0,  # 16' module with rims
    "module_8_width_in": 99.0,  # 8' module with rims
    "center_module_width_in": 105.0,  # 8'9" center cut from 10' stock
    "module_depth_ft": 8.0,  # Module depth
}

# ============================================================
# SECOND FLOOR
# ============================================================

SECOND_FLOOR = {
    # Joists
    "joist_stock": "2x12x192",
    "joist_spacing_oc_in": 16.0,
    "joist_pressure_treated": False,
    # Sheathing
    "sheathing_stock": "panel_advantech_4x8",
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
    "leach_field_y_start_ft": 80.0,  # Behind rear deck piles (back pile at Y=76.9375', clearance ~3')
    "leach_field_length_ft": 30.0,  # 3 trenches × 5' spacing (fits within lot)
    "leach_field_width_ft": 20.0,  # Trench width + spacing
    "leach_field_trench_count": 3,
    "leach_field_trench_spacing_ft": 5.0,  # Reduced from 10' to 5' to fit within lot (rear setback at Y=90')
    # Drain line from house to tank (routed around piles)
    "drain_line_diameter_in": 4.0,  # 4" PVC drain
    "drain_line_depth_in": 24.0,  # 2' below grade (frost line + code)
    # Stub-up location (east face of pile at X=33', Y=52.46875' - aligned with stair module at Floor_Middle_Right_16x8)
    # Pile center: X=33.0', Y=52.46875' (pile index 3,4 in 0-based grid)
    # Pile size: 12" × 12" (11.25" actual)
    # East face of pile: X = 33.0 + (11.25"/2)/12 = 33.0 + 0.46875 = 33.46875'
    # Pipe OD: 4", so pipe center at east face: X = 33.46875 + (4"/2)/12 = 33.46875 + 0.16667 = 33.635'
    "stub_up_x_ft": 33.635,  # Pipe center at east face of pile (X=33.0', Y=52.46875')
    "stub_up_y_ft": 52.46875,  # Pile center Y position
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
    # Concrete slab (driveway thickness with stub-ups)
    "slab_thickness_in": 6.0,  # 6" concrete (driveway grade)
    "slab_x_start_ft": 5.0,  # Under house footprint
    "slab_y_start_ft": 20.0,  # Front setback
    "slab_width_ft": 40.0,  # Match house width
    "slab_depth_ft": 48.0,  # Match house depth
    # Water supply (from street, south side Y=0)
    # Stub-up at west face of pile 5,4 (X=41', Y=44.46875')
    "water_service_line_diameter_in": 1.0,  # 1" PVC water supply (typical residential)
    "water_service_depth_in": 42.0,  # 3.5' below grade (below frost line per IRC P2603.6)
    # Pile 5,4 center: X=41.0', Y=44.46875' (pile index 4,3 in 0-based grid)
    # West face: X = 41.0 - (11.25"/2)/12 = 40.53125'
    # Pipe center at west face: X = 40.53125 - (1"/2)/12 = 40.53125 - 0.04167 = 40.49'
    "water_stub_x_ft": 40.49,  # Pipe center at west face of pile 5,4
    "water_stub_y_ft": 44.46875,  # Pile center Y position
    "water_entry_from_street_y_ft": 0.0,  # Street connection point (lot south edge)
    # Route: north-south in pile gap at X=37.0' (middle between pile columns 4 and 5)
    "water_lateral_x_ft": 37.0,  # X position for north-south run (gap middle)
    # Electrical service (from street, south side Y=0)
    # Stub-up at east face of pile 4,4 (same location as water, spaced apart)
    "electrical_service_conduit_diameter_in": 2.5,  # 2.5" Schedule 40 PVC conduit (200A service per NEC 310.12)
    "electrical_service_depth_in": 24.0,  # 2' below grade (min depth per NEC 300.5 for PVC conduit under concrete)
    # Conduit center at east face, offset 6" from water line
    "electrical_stub_x_ft": 33.51,  # Same X as water (side-by-side)
    "electrical_stub_y_ft": 44.96875,  # Offset 6" north from water stub (44.46875 + 0.5)
    "electrical_entry_from_street_y_ft": 0.0,  # Street connection point
    # Route: north-south in pile gap at X=37.0' (middle between pile columns 4 and 5)
    "electrical_lateral_x_ft": 37.0,  # X position for north-south run (gap middle)
    # Electrical infrastructure (meter → disconnect → panel) - stacked vertically at pile 4,4
    # Equipment mounted on pile east face, centered on pile (not on offset stub-up)
    "electrical_equipment_x_ft": 33.51,  # East face of pile 4,4 (same as stub-up X)
    "electrical_equipment_y_ft": 44.46875,  # Center of pile 4,4 (NOT offset like stub-up)
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

STAIRS = {
    # Exterior stairs from first floor (Z=20') down to slab (Z=0')
    # Running along east side of house, descending north (south to north)
    # Top tread south edge snaps to north edge of Floor_Front_Right_16x16 Rim_Front
    # Finished floor to finished floor (slab top to joist top, excludes deck boards)
    # Foundation alignment (critical for load transfer):
    # - Stair rim joist left face aligns with pile east face (X = 41.46875' global, minus 2x thick for joist clearance)
    # - Shortened joists end at pile east face - 2x thickness (creating stair opening)
    # - Stair rim joist sits at pile east face (west face at X = 41.34375', east face at X = 41.46875')
    # - Stair tread west face snaps to rim joist east face (X = 41.46875', pile east face)
    # - Load path: treads → stringers → rim joist → pile (direct attachment at pile face)
    #
    # Calculated positions (global coordinates):
    #   Pile_41_28 center: X = 41' (pile grid position)
    #   Pile_41_28 east face: X = 41.46875' (pile center + width/2 = 41' + 11.25"/24)
    #   Shortened joist right end: X = 41.34375' (pile east face - thick = 41.46875' - 1.5"/12)
    #   Stair rim joist left face: X = 41.34375' (flush with shortened joist ends)
    #   Stair rim joist center: X = 41.40625' (left face + thick/2 = 41.34375' + 0.75"/12)
    #   Stair rim joist east face: X = 41.46875' (aligned with pile east face)
    #   Stair tread west face: X = 41.46875' (snapped to rim east face = pile east face)
    "stair_x_ft": 41.0
    + (
        11.25 / 24.0
    ),  # West face aligned with Pile_41_28 east face = 41.46875' (pile center + width/2)
    "stair_y_snap_ft": 28.125,  # Y position where top tread south edge meets rim north edge (28' + 1.5")
    "tread_rise_in": 7.25,  # Riser height (7.25" per IRC R311.7.5.1 max 7-3/4")
    "tread_run_in": 10.0,  # Tread depth (10" minimum per IRC R311.7.5.2)
    "tread_width_ft": 3.0,  # Stair width (36" minimum per IRC R311.7.1)
    "tread_stock": "2x12x96_PT",  # Tread material (2x12 PT lumber)
    "descending_direction": "north",  # Stairs descend toward north (-Y direction)
    # Headroom clearance (IRC R311.7.2 requires minimum 80" vertical clearance)
    "headroom_clearance_in": 80.0,  # 6'8" minimum headroom from tread to joist bottom
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
    # Positioned at front of house for ground-level access
    # South face = front setback line (Y=20'), east edge = right side
    "elevator_x_ft": 42.0,  # East edge of house (SE corner)
    "elevator_y_ft": 17.0,  # Just south of front face, accessible from grade
    # Platform dimensions
    "platform_width_ft": 4.0,  # 4' wide (ADA accessible, 48" min for wheelchair)
    "platform_depth_ft": 5.0,  # 5' deep (north face at Y=12.0', south face at Y=7.0')
    # NOTE: travel_height_ft is CALCULATED (= above_grade_ft) in beach_elevator.py create_beach_elevator()
}

# ============================================================
# BUILD OPTIONS
# ============================================================

BUILD = {
    # What to include in build
    "include_lot_survey": True,
    "include_septic_system": False,  # DISABLED FOR TESTING: Septic tank, leach field, drain lines
    "include_utilities": False,  # DISABLED FOR TESTING: Concrete slab, plumbing/electrical stub-ups
    "include_driveway": False,  # DISABLED FOR TESTING: Driveway slab with rebar
    "include_elevator": False,  # DISABLED FOR TESTING: Beach house elevator (open metal lift)
    "include_foundation": True,  # TEST LVL BEAM SYSTEM
    "include_deck_joists": False,  # DISABLED FOR TESTING: Deck joists, rims, hangers (installed BEFORE sheathing)
    "include_first_floor": True,  # 3×3 grid: 40' × 48'
    "include_walls": True,  # Front and rear walls (5 x 8' modules each: Window | Window | Door | Window | Window = 40')
    "include_deck_surface": False,  # DISABLED FOR TESTING: Deck boards and posts (installed AFTER walls)
    "include_second_floor": False,  # Not yet implemented
    "include_stairs": False,  # DISABLED FOR TESTING: Exterior stairs from slab to first floor
    "include_roof": False,  # Not yet implemented
    # Output options
    "save_fcstd": True,
    "export_bom": True,
    "create_snapshots": True,
}
