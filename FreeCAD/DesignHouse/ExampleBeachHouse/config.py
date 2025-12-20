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

FOUNDATION = {
    # Pile grid (calculated: grid_x × grid_y = total piles, footprint spans)
    "pile_spacing_x_ft": 8.0,  # Pile spacing in X direction
    "pile_spacing_y_ft": 8.0,  # Pile spacing in Y direction
    "pile_grid_x": 5,  # Number of piles in X direction
    "pile_grid_y": 8,  # Number of piles in Y direction (includes rear deck row)
    "pile_size_in": 12.0,  # Pile cross-section nominal
    "pile_actual_size_in": 11.25,  # Pile actual dimensions
    "pile_length_ft": 40.0,  # Pile length
    "pile_embed_depth_ft": 20.0,  # Embed depth below grade (local code + storm surge + safety factor)
    # Beams (double-beam assemblies with blocking)
    "beam_stock": "2x12x192",  # Beam stock label (16' beams)
    "beam_stock_short": "2x12x96",  # Short beam stock (8' beams)
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
    "module_16x16_width_in": 195.0,  # 16' module + rims
    "module_8x16_width_in": 99.0,  # 8' module + rims
    "module_16x16_depth_in": 192.0,  # 16' module + rims
    "module_16x8_depth_in": 96.0,  # 8' module + rims
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
    # Front deck (south side)
    "front_deck_depth_ft": 8.0,  # Deck projects south from front wall
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
    "stair_x_ft": 44.0
    - (
        (5.5 + 1.5) / 12.0
    ),  # X position shifted 7.0" west for deck board width (5.5") + rim joist thickness (1.5") = 43.417'
    "stair_y_snap_ft": 28.125,  # Y position where top tread south edge meets rim north edge (28' + 1.5")
    "tread_rise_in": 7.25,  # Riser height (7.25" per IRC R311.7.5.1 max 7-3/4")
    "tread_run_in": 10.0,  # Tread depth (10" minimum per IRC R311.7.5.2)
    "tread_width_ft": 3.0,  # Stair width (36" minimum per IRC R311.7.1)
    "tread_stock": "2x12x96_PT",  # Tread material (2x12 PT lumber)
    "descending_direction": "north",  # Stairs descend toward north (-Y direction)
    # Stair opening in floor joists (joists to remove for stair clearance)
    "opening_joists_to_remove": [
        "Floor_Front_Right_16x16_Joist_1",  # Conflicts with stair opening
        # Additional joists will be added as identified
    ],
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
    "include_septic_system": True,  # Septic tank, leach field, drain lines
    "include_utilities": True,  # Concrete slab, plumbing/electrical stub-ups
    "include_driveway": True,  # Driveway slab with rebar
    "include_elevator": True,  # Beach house elevator (open metal lift)
    "include_foundation": True,
    "include_deck_joists": True,  # Deck joists, rims, hangers (installed BEFORE sheathing)
    "include_first_floor": True,
    "include_walls": True,  # Front and rear walls (4 x 8' modules each: Window | Door | Door | Window)
    "include_deck_surface": True,  # Deck boards and posts (installed AFTER walls)
    "include_second_floor": False,  # Not yet implemented
    "include_stairs": True,  # Exterior stairs from slab to first floor
    "include_roof": False,  # Not yet implemented
    # Output options
    "save_fcstd": True,
    "export_bom": True,
    "create_snapshots": True,
}
