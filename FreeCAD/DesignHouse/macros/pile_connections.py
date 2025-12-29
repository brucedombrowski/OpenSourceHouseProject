#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pile_connections.py - Pile-to-beam connection hardware for foundation system.

This module handles the structural connections between piles and LVL beams:
  1. Notches - Cuts in piles where beams seat
  2. Through-rods - Horizontal threaded rods securing beams to piles

IMPORTANT: Connection details may need adjustment based on structural engineering
review. All dimensions are parameterized for easy modification.

Design Intent:
  - Notch allows beam to seat into pile (not just against face)
  - Through-rods with washers/nuts on both ends provide positive connection
  - Notch type depends on pile position:
    * Endpoint piles: corner notch (half pile thickness in Y)
    * Middle/boundary piles: full-width notch (full pile thickness in Y)

Connection Types:
  - Single-beam: Edge piles (columns 1 and 5) have beam on one side only
  - Double-beam: Interior piles (columns 2-4) have beams on both sides

For Luke Dombrowski. Stay Alive.
"""

import os
import sys

import Part

import FreeCAD as App

# Add macros directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import beach_common as bc  # noqa: E402

# ============================================================
# CONFIGURATION DEFAULTS (can be overridden via config)
# ============================================================

DEFAULT_CONNECTION_CONFIG = {
    # Rod/bolt configuration
    "rod_diameter_in": 0.5,  # Threaded rod diameter
    "rod_protrusion_in": 1.0,  # Protrusion past pile face on each end (for washer + nut)
    # Positioning tolerances
    "endpoint_tolerance_in": 1.0,  # Tolerance for detecting pile at beam endpoint
    # Bolt Z positioning uses equal thirds (bolts at 1/3 and 2/3 of beam depth)
    # This gives ~4" edge distance and ~4" between bolts for 11.875" LVL
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def is_segment_boundary_pile(
    pile_center_y_mm, lvl_assembly, all_lvl_assemblies, pile_bb, endpoint_tolerance_mm
):
    """
    Check if a pile at a beam endpoint is actually a segment boundary
    where another LVL segment connects.

    Args:
        pile_center_y_mm: Y coordinate of pile center (mm)
        lvl_assembly: The current LVL assembly being checked
        all_lvl_assemblies: List of all LVL assemblies
        pile_bb: Pile bounding box
        endpoint_tolerance_mm: Tolerance for endpoint detection (mm)

    Returns:
        bool: True if another segment connects at this pile
    """
    for other_lvl in all_lvl_assemblies:
        if other_lvl.Name == lvl_assembly.Name:
            continue  # Skip the current segment
        other_bb = other_lvl.Shape.BoundBox
        # Check if other segment is on same girder line (X overlap)
        other_x_overlap = other_bb.XMin <= pile_bb.XMax and other_bb.XMax >= pile_bb.XMin
        if not other_x_overlap:
            continue
        # Check if other segment starts or ends at this pile
        other_dist_south = abs(other_bb.YMin - pile_center_y_mm)
        other_dist_north = abs(other_bb.YMax - pile_center_y_mm)
        if other_dist_south < endpoint_tolerance_mm or other_dist_north < endpoint_tolerance_mm:
            return True
    return False


def determine_pile_position(
    pile_center_y_mm, lvl_bb, all_lvl_assemblies, lvl_assembly, pile_bb, endpoint_tolerance_mm
):
    """
    Determine if a pile is at an endpoint, middle, or segment boundary.

    Args:
        pile_center_y_mm: Y coordinate of pile center (mm)
        lvl_bb: LVL assembly bounding box
        all_lvl_assemblies: List of all LVL assemblies
        lvl_assembly: The current LVL assembly
        pile_bb: Pile bounding box
        endpoint_tolerance_mm: Tolerance for endpoint detection (mm)

    Returns:
        tuple: (is_endpoint, is_at_south_end, is_at_north_end)
    """
    dist_to_south_end = abs(lvl_bb.YMin - pile_center_y_mm)
    dist_to_north_end = abs(lvl_bb.YMax - pile_center_y_mm)
    is_at_south_end = dist_to_south_end < endpoint_tolerance_mm
    is_at_north_end = dist_to_north_end < endpoint_tolerance_mm

    # Check if this is a segment boundary pile
    is_boundary = False
    if is_at_south_end or is_at_north_end:
        is_boundary = is_segment_boundary_pile(
            pile_center_y_mm, lvl_assembly, all_lvl_assemblies, pile_bb, endpoint_tolerance_mm
        )

    # Endpoint only if at beam end AND no other segment continues
    is_endpoint = (is_at_south_end or is_at_north_end) and not is_boundary

    return is_endpoint, is_at_south_end, is_at_north_end


# ============================================================
# NOTCH FUNCTIONS
# ============================================================


def create_all_pile_notches(
    pile_objs,
    lvl_assemblies,
    pile_width_in,
    pile_thick_in,
    lvl_total_width_in,
    lvl_depth_in,
    beam_base_z_in,
    endpoint_tolerance_in=1.0,
):
    """
    Create notches in all piles for LVL beam seating.

    This is the main entry point for notching. It handles:
    - Detecting which piles need notches based on LVL positions
    - Determining notch type (endpoint corner vs middle full-width)
    - Preventing double-notching at segment boundaries

    Args:
        pile_objs: List of pile Part::Feature objects
        lvl_assemblies: List of LVL assembly objects
        pile_width_in: Pile width in X direction (inches)
        pile_thick_in: Pile thickness in Y direction (inches)
        lvl_total_width_in: LVL assembly width (inches, typically 3.5")
        lvl_depth_in: LVL beam depth (inches)
        beam_base_z_in: Z elevation of beam bottom (inches)
        endpoint_tolerance_in: Tolerance for endpoint detection (inches)

    Returns:
        tuple: (notch_count, notched_piles_set)
    """
    notch_count = 0
    notched_piles = set()  # Track which piles have been notched
    endpoint_tolerance_mm = bc.inch(endpoint_tolerance_in)
    y_tolerance_mm = bc.inch(1.0)  # Tolerance for Y overlap detection

    for pile in pile_objs:
        pile_bb = pile.Shape.BoundBox
        pile_center_x_mm = (pile_bb.XMin + pile_bb.XMax) / 2.0
        pile_center_y_mm = (pile_bb.YMin + pile_bb.YMax) / 2.0

        # Calculate pile face positions
        pile_west_face_mm = pile_center_x_mm - bc.inch(pile_width_in / 2.0)
        pile_east_face_mm = pile_center_x_mm + bc.inch(pile_width_in / 2.0)
        pile_south_face_mm = pile_center_y_mm - bc.inch(pile_thick_in / 2.0)

        for lvl_assembly in lvl_assemblies:
            # Skip if pile already notched
            if pile.Name in notched_piles:
                continue

            lvl_bb = lvl_assembly.Shape.BoundBox

            # Check if LVL's Y range contains pile center
            y_overlap = (
                (lvl_bb.YMin - y_tolerance_mm) <= pile_center_y_mm <= (lvl_bb.YMax + y_tolerance_mm)
            )

            # Check if LVL's X range overlaps pile's X range
            x_overlap = lvl_bb.XMin <= pile_bb.XMax and lvl_bb.XMax >= pile_bb.XMin

            if y_overlap and x_overlap:
                lvl_center_x_mm = (lvl_bb.XMin + lvl_bb.XMax) / 2.0

                # Determine pile position (endpoint vs middle)
                is_endpoint, is_at_south_end, is_at_north_end = determine_pile_position(
                    pile_center_y_mm,
                    lvl_bb,
                    lvl_assemblies,
                    lvl_assembly,
                    pile_bb,
                    endpoint_tolerance_mm,
                )

                # Notch dimensions depend on pile position
                if not is_endpoint:
                    # MIDDLE/BOUNDARY PILE: full-width notch
                    notch_depth_y_in = pile_thick_in
                    notch_y_mm = pile_south_face_mm
                else:
                    # ENDPOINT PILE: corner notch (half pile thickness)
                    notch_depth_y_in = pile_thick_in / 2.0
                    if is_at_south_end:
                        # Beam starts here, extends north - notch on north half
                        notch_y_mm = pile_center_y_mm
                    else:
                        # Beam ends here, extends south - notch on south half
                        notch_y_mm = pile_south_face_mm

                # Determine X position based on which side LVL is on
                if lvl_center_x_mm < pile_center_x_mm:
                    # LVL on WEST side
                    notch_x_mm = pile_west_face_mm
                else:
                    # LVL on EAST side
                    notch_x_mm = pile_east_face_mm - bc.inch(lvl_total_width_in)

                # Create and cut notch
                notch_box = Part.makeBox(
                    bc.inch(lvl_total_width_in), bc.inch(notch_depth_y_in), bc.inch(lvl_depth_in)
                )
                notch_box.Placement.Base = App.Vector(
                    notch_x_mm, notch_y_mm, bc.inch(beam_base_z_in)
                )

                try:
                    pile.Shape = pile.Shape.cut(notch_box)
                    notch_count += 1
                    notched_piles.add(pile.Name)
                except Exception as e:
                    App.Console.PrintWarning(
                        f"[pile_connections] Failed to notch {pile.Name}: {e}\n"
                    )

    App.Console.PrintMessage(f"[pile_connections] Created {notch_count} pile notches.\n")
    return notch_count, notched_piles


# ============================================================
# BOLT/ROD FUNCTIONS
# ============================================================


def create_all_pile_bolts(
    doc,
    catalog,
    pile_objs,
    lvl_assemblies,
    notched_piles,
    pile_width_in,
    pile_thick_in,
    lvl_depth_in,
    beam_base_z_in,
    config=None,
):
    """
    Create threaded rod connections for all notched piles.

    This is the main entry point for bolt creation. It handles:
    - Finding which LVL assemblies connect to each pile
    - Determining bolt Y position based on pile type (endpoint vs middle)
    - Creating rods with proper length and positioning

    Args:
        doc: FreeCAD document
        catalog: Lumber catalog for hardware lookup
        pile_objs: List of pile Part::Feature objects
        lvl_assemblies: List of LVL assembly objects
        notched_piles: Set of pile names that have been notched
        pile_width_in: Pile width in X direction (inches)
        pile_thick_in: Pile thickness in Y direction (inches)
        lvl_depth_in: LVL beam depth (inches)
        beam_base_z_in: Z elevation of beam bottom (inches)
        config: Optional configuration dict (uses defaults if None)

    Returns:
        list: List of created bolt Part::Feature objects
    """
    cfg = config or DEFAULT_CONNECTION_CONFIG

    # Get configuration values
    rod_diameter_in = cfg.get("rod_diameter_in", 0.5)
    rod_protrusion_in = cfg.get("rod_protrusion_in", 1.0)
    endpoint_tolerance_in = cfg.get("endpoint_tolerance_in", 1.0)
    endpoint_tolerance_mm = bc.inch(endpoint_tolerance_in)

    # Rod length: pile width + protrusion on each end
    rod_length_in = pile_width_in + (2 * rod_protrusion_in)

    # Bolt Z positions: equal thirds (1/3 and 2/3 of beam depth)
    bolt_z_positions_in = [
        beam_base_z_in + lvl_depth_in / 3.0,  # Lower bolt at 1/3
        beam_base_z_in + 2.0 * lvl_depth_in / 3.0,  # Upper bolt at 2/3
    ]

    # Quarter pile offset for endpoint bolt positioning
    quarter_pile_offset_mm = bc.inch(pile_thick_in / 4.0)

    anchor_bolts_created = []

    for pile in pile_objs:
        # Only add bolts to piles that have been notched
        if pile.Name not in notched_piles:
            continue

        pile_bb = pile.Shape.BoundBox
        pile_center_x_mm = (pile_bb.XMin + pile_bb.XMax) / 2.0
        pile_center_y_mm = (pile_bb.YMin + pile_bb.YMax) / 2.0
        pile_west_face_mm = pile_center_x_mm - bc.inch(pile_width_in / 2.0)

        # Find all LVL assemblies that connect to this pile
        connected_assemblies = []
        for lvl_assembly in lvl_assemblies:
            lvl_bb = lvl_assembly.Shape.BoundBox
            y_tolerance_mm = bc.inch(0.1)
            y_overlap = (
                (lvl_bb.YMin - y_tolerance_mm) <= pile_center_y_mm <= (lvl_bb.YMax + y_tolerance_mm)
            )
            x_overlap = lvl_bb.XMin <= pile_bb.XMax and lvl_bb.XMax >= pile_bb.XMin
            if y_overlap and x_overlap:
                connected_assemblies.append(lvl_assembly)

        # Create bolts for each connected assembly
        for lvl_assembly in connected_assemblies:
            lvl_bb = lvl_assembly.Shape.BoundBox

            # Determine pile position (endpoint vs middle)
            is_endpoint, is_at_south_end, is_at_north_end = determine_pile_position(
                pile_center_y_mm,
                lvl_bb,
                lvl_assemblies,
                lvl_assembly,
                pile_bb,
                endpoint_tolerance_mm,
            )

            # Calculate bolt Y position
            if is_endpoint:
                # ENDPOINT PILE: bolt centered on notched half
                if is_at_south_end:
                    # Notch on north half, bolt on north half
                    bolt_y_mm = pile_center_y_mm + quarter_pile_offset_mm
                else:
                    # Notch on south half, bolt on south half
                    bolt_y_mm = pile_center_y_mm - quarter_pile_offset_mm
            else:
                # MIDDLE/BOUNDARY PILE: bolt centered on pile
                bolt_y_mm = pile_center_y_mm

            # Rod X position: centered on pile (starts protrusion distance west of pile)
            rod_start_x_mm = pile_west_face_mm - bc.inch(rod_protrusion_in)

            # Create bolts at each Z position
            for bolt_idx, bolt_z_in in enumerate(bolt_z_positions_in):
                bolt_name = f"{pile.Name}_AnchorBolt_{bolt_idx+1}"
                anchor_bolt = doc.addObject("Part::Feature", bolt_name)

                anchor_bolt_shape = Part.makeCylinder(
                    bc.inch(rod_diameter_in / 2.0),
                    bc.inch(rod_length_in),
                )

                # Rotate to run horizontally (X direction)
                rotation = App.Rotation(App.Vector(0, 1, 0), 90)

                anchor_bolt_shape.Placement = App.Placement(
                    App.Vector(rod_start_x_mm, bolt_y_mm, bc.inch(bolt_z_in)), rotation
                )
                anchor_bolt.Shape = anchor_bolt_shape

                # Attach BOM metadata if catalog entry available
                try:
                    bolt_stock = bc.find_stock(catalog, "bolt_carriage_0.5x10")
                    bc.attach_beach_metadata(anchor_bolt, bolt_stock, label="bolt_carriage_0.5x10")
                except Exception:
                    pass  # Skip metadata if catalog entry not found

                anchor_bolts_created.append(anchor_bolt)

    App.Console.PrintMessage(
        f"[pile_connections] Created {len(anchor_bolts_created)} pile-to-beam anchor bolts "
        f"(2 per LVL-pile connection)\n"
    )
    return anchor_bolts_created


# ============================================================
# MAIN ENTRY POINT
# ============================================================


def create_all_pile_connections(
    doc,
    catalog,
    pile_objs,
    lvl_assemblies,
    pile_width_in,
    pile_thick_in,
    lvl_total_width_in,
    lvl_depth_in,
    beam_base_z_in,
    config=None,
):
    """
    Create all pile-to-beam connections (notches + bolts).

    This is the top-level function that coordinates notching and bolting.
    Call this from the main macro to handle all pile connections.

    Args:
        doc: FreeCAD document
        catalog: Lumber catalog for hardware lookup
        pile_objs: List of pile Part::Feature objects
        lvl_assemblies: List of LVL assembly objects
        pile_width_in: Pile width in X direction (inches)
        pile_thick_in: Pile thickness in Y direction (inches)
        lvl_total_width_in: LVL assembly width (inches, typically 3.5")
        lvl_depth_in: LVL beam depth (inches)
        beam_base_z_in: Z elevation of beam bottom (inches)
        config: Optional configuration dict (uses defaults if None)

    Returns:
        tuple: (notch_count, notched_piles_set, bolt_objects_list)
    """
    cfg = config or DEFAULT_CONNECTION_CONFIG
    endpoint_tolerance_in = cfg.get("endpoint_tolerance_in", 1.0)

    App.Console.PrintMessage("[pile_connections] Creating pile-to-beam connections...\n")

    # Step 1: Create notches
    App.Console.PrintMessage("[pile_connections]   Notching piles for LVL beam seating...\n")
    notch_count, notched_piles = create_all_pile_notches(
        pile_objs,
        lvl_assemblies,
        pile_width_in,
        pile_thick_in,
        lvl_total_width_in,
        lvl_depth_in,
        beam_base_z_in,
        endpoint_tolerance_in,
    )

    # Step 2: Create bolts
    App.Console.PrintMessage("[pile_connections]   Adding pile-to-beam anchor bolts...\n")
    bolt_objects = create_all_pile_bolts(
        doc,
        catalog,
        pile_objs,
        lvl_assemblies,
        notched_piles,
        pile_width_in,
        pile_thick_in,
        lvl_depth_in,
        beam_base_z_in,
        cfg,
    )

    App.Console.PrintMessage("[pile_connections] Pile connections complete.\n")
    return notch_count, notched_piles, bolt_objects


if __name__ == "__main__":
    print("[pile_connections] Pile-to-beam connection module.")
    print("[pile_connections] Import into your macro: import pile_connections as pc")
    print("[pile_connections] Main function: create_all_pile_connections()")
