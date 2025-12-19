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
