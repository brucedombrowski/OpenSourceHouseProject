#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
beam_assemblies.py - LVL beam assemblies for 950 Surf foundation.

Assembly types:
  1. LVL_Beam_20ft - Two-ply laminated LVL beam (1.75" × depth × 240")

Construction sequence:
  1. Place ply 1 (west ply, centered on pile)
  2. Place ply 2 (east ply, 1.75" offset from ply 1)
  3. Field-laminate with construction adhesive + nails (per manufacturer spec)

Geometry:
  - LVL stock: 1.75" × depth × 240" (configurable depth: 9.25", 11.875", 14", 16", 24")
  - Assembly: 2 plies laminated together = 3.5" total width
  - No blocking (LVL plies form continuous laminated unit)
  - Single notch per pile: 3.5" wide × depth deep

Design rationale:
  - LVL spans 20' over 3 piles (10' OC) vs. old 2x12 doubled beams (16' over 2 piles at 8' OC)
  - Single notch per pile (3.5" wide) vs. old double notches (two 1.5" notches)
  - Fewer beam segments: 3 segments per girder line vs. old continuous fill
  - Higher strength: LVL 2.0E vs. #2 PT lumber

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


def create_lvl_beam_assembly_20ft(
    doc,
    catalog,
    x_girder_ft,
    y_start_ft,
    y_end_ft,
    z_base_in,
    lvl_label="lvl_1.75x11.875x240",
    assembly_idx=0,
    side="west",
    pile_y_positions_ft=None,
):
    """
    Create a 20-foot two-ply LVL beam assembly.

    Args:
        doc: FreeCAD document
        catalog: Catalog list (from beach_common.load_beach_catalog)
        x_girder_ft: X position of girder centerline (pile center X, feet)
        y_start_ft: Y starting position (south pile center, feet)
        y_end_ft: Y ending position (north pile center, feet)
        z_base_in: Z base elevation (inches above datum)
        lvl_label: LVL catalog label (default: 1.75"×11.875"×240")
        assembly_idx: Index for unique naming (default 0)
        side: Which side of pile to place LVL ("west" or "east")

    Returns:
        App::Part assembly containing both LVL plies

    Construction Notes:
        - LVL assembly placed on specified side of pile (west or east)
        - Total assembly width: 3.5" (two 1.75" plies)
        - West side: LVL west face aligned to pile west face (cantilevers west)
        - East side: LVL east face aligned to pile east face (cantilevers east)
        - Beam length: y_end_ft - y_start_ft (typically 20' = 240")
        - Plies are laminated together (field-applied adhesive + nails)

    Pile Notching:
        - Single notch per pile: 3.5" wide (full assembly width)
        - Notch depth: LVL depth (e.g., 11.875", 24", etc.)
        - Notch positioned at pile face (west or east depending on side parameter)
    """
    # Lookup LVL stock
    lvl_stock = bc.find_stock(catalog, lvl_label)
    ply_thick_in = float(lvl_stock["actual_thickness_in"])  # 1.75"
    lvl_depth_in = float(lvl_stock["actual_width_in"])  # Variable (9.25" to 24")
    lvl_len_in = float(lvl_stock["length_in"])  # 240"

    # Calculate assembly geometry
    total_width_in = ply_thick_in * 2  # 3.5" (2 plies)
    beam_length_ft = y_end_ft - y_start_ft
    beam_length_in = beam_length_ft * 12.0

    # Validate beam length doesn't exceed stock length
    if beam_length_in > lvl_len_in:
        App.Console.PrintWarning(
            f'[beam_assemblies] WARNING: Beam length {beam_length_in:.1f}" '
            f'exceeds LVL stock length {lvl_len_in:.1f}" for assembly {assembly_idx}\n'
        )

    # Create assembly container (App::Part has spatial properties)
    assembly_name = f"LVL_Girder_20ft_{assembly_idx}"
    existing = doc.getObject(assembly_name)
    if existing:
        doc.removeObject(existing.Name)
        App.Console.PrintMessage(f"[beam_assemblies] Removed existing assembly: {assembly_name}\n")

    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    App.Console.PrintMessage(
        f"[beam_assemblies] Creating LVL assembly: {assembly_name} "
        f'({ply_thick_in:.2f}"×{lvl_depth_in:.2f}"×{beam_length_ft:.1f}\', 2 plies)\n'
    )

    created = []

    # ====================
    # PLY PLACEMENT - DEPENDS ON SIDE PARAMETER
    # ====================
    # Design: LVL assembly placed on specified side of pile
    # - "west": LVL west face aligned to pile west face (cantilevers west)
    # - "east": LVL east face aligned to pile east face (cantilevers east)

    pile_width_in = 11.25  # Actual pile dimension (from catalog)

    if side == "west":
        # WEST SIDE: LVL west face aligned to pile west face
        pile_west_face_ft = x_girder_ft - (pile_width_in / 12.0 / 2.0)
        # Ply 1 (west ply) has its west face at pile west face
        x_ply1_ft = pile_west_face_ft + (ply_thick_in / 12.0 / 2.0)
        # Ply 2 (east ply) is offset east by one ply thickness
        x_ply2_ft = x_ply1_ft + (ply_thick_in / 12.0)
    elif side == "east":
        # EAST SIDE: LVL east face aligned to pile east face
        pile_east_face_ft = x_girder_ft + (pile_width_in / 12.0 / 2.0)
        # Ply 2 (east ply) has its east face at pile east face
        x_ply2_ft = pile_east_face_ft - (ply_thick_in / 12.0 / 2.0)
        # Ply 1 (west ply) is offset west by one ply thickness
        x_ply1_ft = x_ply2_ft - (ply_thick_in / 12.0)
    else:
        raise ValueError(f"Invalid side parameter: {side}. Must be 'west' or 'east'.")

    ply1_name = f"{assembly_name}_Ply1"
    ply1 = bc.make_beam(
        doc,
        catalog,
        lvl_label,
        ply1_name,
        x_ply1_ft,
        y_start_ft,
        z_base_in,
        beam_length_in,
        orientation="Y",
    )
    created.append(ply1)

    # ====================
    # PLY 2 (EAST PLY)
    # ====================
    # East face aligns with pile west face (calculated above)
    # x_ply2_ft already calculated above

    ply2_name = f"{assembly_name}_Ply2"
    ply2 = bc.make_beam(
        doc,
        catalog,
        lvl_label,
        ply2_name,
        x_ply2_ft,
        y_start_ft,
        z_base_in,
        beam_length_in,
        orientation="Y",
    )
    created.append(ply2)

    # ====================
    # THROUGH-BOLTS (connect two plies together)
    # ====================
    # Design: 1/2" × 10" carriage bolts with washers and nuts
    # Spacing: IRC requires bolts every 4' OC max for laminated beams
    # Pattern: Stagger bolts in 2 rows (top/bottom) at 2' OC
    # Position: Bolts run horizontally through both plies (X direction)

    # IRC R502.1.6: Built-up beams require bolts at 4' OC max
    # For LVL beams with construction adhesive, bolts are mainly for clamping during cure
    # Use 4' OC spacing (IRC max) since adhesive does most of the work
    bolt_spacing_ft = 4.0  # 4' OC (IRC max spacing for laminated beams)
    bolt_z_offset_top_in = 2.0  # Top row: 2" from top of beam
    bolt_z_offset_bottom_in = 2.0  # Bottom row: 2" from bottom of beam
    num_bolts = int(beam_length_ft / bolt_spacing_ft) + 1  # At least one bolt per 4'

    # Lookup hardware from catalog
    bolt_stock = bc.find_stock(catalog, "bolt_carriage_0.5x10")
    washer_stock = bc.find_stock(catalog, "washer_0.5")
    nut_stock = bc.find_stock(catalog, "nut_hex_0.5")

    bolt_dia_in = float(bolt_stock["actual_thickness_in"])  # 0.5"
    washer_thick_in = float(washer_stock["actual_thickness_in"])  # 0.065"
    nut_thick_in = float(nut_stock["actual_thickness_in"])  # 0.4375"
    # Note: bolt_len_in and washer_dia_in available from catalog if needed

    # Create bolts in staggered pattern (alternating top/bottom rows)
    # Skip bolts near pile locations (vertical anchor bolts go there instead)
    pile_clearance_ft = 1.0  # 1' clearance around each pile

    for i in range(num_bolts):
        y_bolt_ft = y_start_ft + (i * bolt_spacing_ft)
        if y_bolt_ft > y_end_ft:
            break  # Don't exceed beam length

        # Check if bolt is too close to any pile
        if pile_y_positions_ft:
            too_close_to_pile = False
            for pile_y_ft in pile_y_positions_ft:
                if abs(y_bolt_ft - pile_y_ft) < pile_clearance_ft:
                    too_close_to_pile = True
                    break
            if too_close_to_pile:
                continue  # Skip this bolt position

        # Alternate between top and bottom rows
        is_top_row = i % 2 == 0
        if is_top_row:
            z_bolt_in = z_base_in + lvl_depth_in - bolt_z_offset_top_in
        else:
            z_bolt_in = z_base_in + bolt_z_offset_bottom_in

        # Bolt position: center of LVL assembly (between ply1 and ply2)
        x_bolt_center_ft = (x_ply1_ft + x_ply2_ft) / 2.0

        # Create bolt cylinder (simplified - just visual representation)
        bolt_name = f"{assembly_name}_Bolt_{i+1}"
        bolt = doc.addObject("Part::Feature", bolt_name)
        bolt_shape = Part.makeCylinder(
            bc.inch(bolt_dia_in / 2.0),  # radius
            bc.inch(
                total_width_in + washer_thick_in * 2 + nut_thick_in
            ),  # length (through both plies + washers + nut)
        )
        # Rotate to run in X direction (horizontally through plies)
        bolt_shape.Placement = App.Placement(
            App.Vector(
                bc.ft(x_bolt_center_ft) - bc.inch((total_width_in + washer_thick_in * 2) / 2.0),
                bc.ft(y_bolt_ft) - bc.inch(bolt_dia_in / 2.0),
                bc.inch(z_bolt_in),
            ),
            App.Rotation(App.Vector(0, 1, 0), 90),  # Rotate around Y axis to orient along X
        )
        bolt.Shape = bolt_shape

        # Attach BOM metadata to bolt (each bolt object represents qty=1)
        bc.attach_beach_metadata(bolt, bolt_stock, label="bolt_carriage_0.5x10")
        created.append(bolt)

        # NOTE: Washers and nuts are tracked via BOM metadata but not modeled geometrically
        # (too small to visualize clearly at building scale)
        # BOM will show: 1 bolt + 2 washers + 1 nut per bolt location

    App.Console.PrintMessage(f"[beam_assemblies]   Added {num_bolts} through-bolts to assembly\n")

    # Add all parts to assembly
    App.Console.PrintMessage(f"[beam_assemblies] Adding {len(created)} parts to assembly...\n")
    for obj in created:
        assembly.addObject(obj)

    App.Console.PrintMessage(
        f"[beam_assemblies] ✓ LVL assembly complete: {assembly_name} "
        f"(X={x_girder_ft:.2f}', Y={y_start_ft:.2f}'-{y_end_ft:.2f}', "
        f'width={total_width_in:.2f}", depth={lvl_depth_in:.2f}")\n'
    )

    return assembly


def create_lvl_beam_segments_for_girder(
    doc,
    catalog,
    x_girder_ft,
    y_pile_positions_ft,
    z_base_in,
    lvl_label="lvl_1.75x11.875x240",
    girder_idx=0,
    side="west",
):
    """
    Create three 20' LVL beam segments for a single girder line.

    This is a convenience function that creates the standard 3-segment pattern
    for a girder spanning 7 piles (rows 1-3, 3-5, 5-7).

    Args:
        doc: FreeCAD document
        catalog: Catalog list
        x_girder_ft: X position of girder centerline (feet)
        y_pile_positions_ft: List of pile Y positions (7 piles, feet)
        z_base_in: Z base elevation (inches above datum)
        lvl_label: LVL catalog label (default: 1.75"×11.875"×240")
        girder_idx: Girder line index for naming (default 0)
        side: Which side of pile to place LVL ("west" or "east")

    Returns:
        List of 3 App::Part assemblies (one per segment)

    Raises:
        ValueError: If y_pile_positions_ft doesn't have exactly 7 positions
    """
    if len(y_pile_positions_ft) != 7:
        raise ValueError(
            f"Expected 7 pile positions for 3 segments, got {len(y_pile_positions_ft)}"
        )

    assemblies = []

    # Segment pairs: (row_start, row_end) using 1-based indexing
    # Row 1 = pile 0, Row 3 = pile 2, Row 5 = pile 4, Row 7 = pile 6
    segment_pairs = [(0, 2), (2, 4), (4, 6)]  # Indices into y_pile_positions_ft

    for seg_idx, (start_idx, end_idx) in enumerate(segment_pairs):
        y_start_ft = y_pile_positions_ft[start_idx]
        y_end_ft = y_pile_positions_ft[end_idx]

        # Global assembly index: girder_idx * 3 + seg_idx
        assembly_idx = girder_idx * 3 + seg_idx

        assembly = create_lvl_beam_assembly_20ft(
            doc,
            catalog,
            x_girder_ft,
            y_start_ft,
            y_end_ft,
            z_base_in,
            lvl_label,
            assembly_idx,
            side,
            y_pile_positions_ft,  # Pass full pile Y list for bolt clearance checking
        )
        assemblies.append(assembly)

    App.Console.PrintMessage(
        f"[beam_assemblies] Created {len(assemblies)} LVL segments for girder at X={x_girder_ft:.2f}'\n"
    )

    return assemblies


if __name__ == "__main__":
    print("[beam_assemblies] This module provides LVL beam assembly creation helpers.")
    print("[beam_assemblies] Import into your macro: import beam_assemblies as ba")
