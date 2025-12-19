#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
950 Surf Beach House - Design Configuration
All design parameters in one place.

For Luke Dombrowski. Stay Alive.
"""

# ============================================================
# LOT SURVEY
# ============================================================

LOT = {
    "width_ft": 50.0,  # Lot width (X direction)
    "depth_ft": 100.0,  # Lot depth (Y direction)
    "front_setback_ft": 20.0,  # Front setback from property line
    "side_setback_ft": 7.5,  # Side setback from property line
    "rear_setback_ft": 10.0,  # Rear setback from property line
}

# ============================================================
# FOUNDATION
# ============================================================

FOUNDATION = {
    # Pile grid (40' x 48' footprint, 5×7 = 35 piles total)
    "pile_spacing_x_ft": 8.0,  # Pile spacing in X direction
    "pile_spacing_y_ft": 8.0,  # Pile spacing in Y direction
    "pile_grid_x": 5,  # Number of piles in X direction (5 piles, 4 gaps × 8' = 32' span)
    "pile_grid_y": 7,  # Number of piles in Y direction (7 piles, 6 gaps × 8' = 48' span)
    "pile_size_in": 12.0,  # Pile cross-section (12x12)
    "pile_length_ft": 40.0,  # Pile length
    # Beams
    "beam_stock": "2x12x192",  # Beam stock label (16' beams)
    "beam_stock_short": "2x12x96",  # Short beam stock (8' beams)
    "beam_pressure_treated": True,  # Use PT lumber for beams
    # Elevation
    "grade_z_ft": 0.0,  # Grade level (datum)
    "above_grade_ft": 20.0,  # Top of foundation above grade
}

# ============================================================
# FIRST FLOOR
# ============================================================

FIRST_FLOOR = {
    # Joists
    "joist_stock": "2x12x192",  # Joist stock label
    "joist_spacing_oc_in": 16.0,  # Joist spacing on-center
    "joist_pressure_treated": False,
    # Sheathing
    "sheathing_stock": "panel_advantech_4x8",
    # Layout (assembly-based, no hard-coded offsets!)
    "start_x_ft": 9.0,  # X position for first module (centered on lot)
    "start_y_ft": 20.0,  # Y position (front setback)
    "base_z_ft": 20.0,  # Z position (top of foundation)
}

# ============================================================
# WALLS
# ============================================================

WALLS = {
    # Framing
    "stud_stock": "2x4x96",  # Wall stud stock
    "plate_stock": "2x4x96",  # Top/bottom plate stock
    "wall_height_in": 96.0,  # Wall height (8')
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
    "tank_x_ft": 25.0,  # Centered on lot width
    "tank_y_ft": 85.0,  # Northern (back) part of lot
    "tank_length_ft": 10.0,  # Typical 1000-1500 gallon tank
    "tank_width_ft": 5.0,
    "tank_depth_ft": 5.0,  # Underground
    # Leach field (drain field)
    "leach_field_x_start_ft": 10.0,  # West side of tank
    "leach_field_y_start_ft": 75.0,  # Behind tank
    "leach_field_length_ft": 30.0,  # 3 trenches × 10' spacing
    "leach_field_width_ft": 20.0,  # Trench width + spacing
    "leach_field_trench_count": 3,
    "leach_field_trench_spacing_ft": 10.0,
    # Drain line from house to tank
    "drain_line_diameter_in": 4.0,  # 4" PVC drain
    "drain_line_depth_in": 24.0,  # 2' below grade (frost line + code)
    # Stub-up location (rear of house, centered)
    "stub_up_x_ft": 25.0,  # Centered on lot
    "stub_up_y_ft": 68.0,  # Just behind rear piles (last pile at Y=68')
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
    "water_service_line_diameter_in": 1.0,  # 1" PVC water supply
    "water_service_depth_in": 36.0,  # 3' below grade (frost line)
    "water_stub_x_ft": 25.0,  # Centered on lot
    "water_stub_y_ft": 22.0,  # Just inside front setback
    "water_entry_from_street_y_ft": 0.0,  # Street connection point
    # Electrical service (from street, south side Y=0)
    "electrical_service_conduit_diameter_in": 2.0,  # 2" conduit (200A service)
    "electrical_service_depth_in": 24.0,  # 2' below grade
    "electrical_stub_x_ft": 30.0,  # Near front of house
    "electrical_stub_y_ft": 22.0,  # Just inside front setback
    "electrical_entry_from_street_y_ft": 0.0,  # Street connection point
    # Plumbing stub-ups (drain/waste/vent for 3 zones)
    "plumbing_stub_positions": [
        {"name": "Kitchen", "x_ft": 15.0, "y_ft": 30.0, "diameter_in": 4.0},
        {"name": "Bath", "x_ft": 35.0, "y_ft": 40.0, "diameter_in": 4.0},
        {"name": "Laundry", "x_ft": 25.0, "y_ft": 50.0, "diameter_in": 4.0},
    ],
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
# BUILD OPTIONS
# ============================================================

BUILD = {
    # What to include in build
    "include_lot_survey": True,
    "include_septic_system": True,  # Septic tank, leach field, drain lines
    "include_utilities": True,  # Concrete slab, plumbing/electrical stub-ups
    "include_foundation": True,
    "include_first_floor": True,
    "include_walls": False,  # Not yet implemented in refactored version
    "include_second_floor": False,  # Not yet implemented
    "include_stairs": False,  # Not yet implemented
    "include_roof": False,  # Not yet implemented
    # Output options
    "save_fcstd": True,
    "export_bom": True,
    "create_snapshots": True,
}
