#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
beam_assemblies.py - Double beam assemblies with blocking for 950 Surf foundation.

Assembly types:
  1. Double_Beam_2x12x16 - Two 16' beams with blocking at 24" OC
  2. Double_Beam_2x12x8 - Two 8' beams with blocking at 24" OC

Construction sequence (IRC R502.7 lateral bracing):
  1. Place left beam (notched into piles)
  2. Install blocking pieces (24" OC, right face aligns to left beam's left face)
  3. Place right beam (notched into piles)

Geometry:
  - Beam stock: 2x12 (actual: 1.5" x 11.25")
  - Blocking: 2x12 (actual: 1.5" x 11.25")
  - Blocking length: 11.25" - 3" = 8.25" (architectural detail)
  - Blocking spacing: 24" OC (every 2 feet along beam length)
  - Gap between beams: ~11.75" (pile width 12" - 2×beam thickness 1.5" = 9")

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


def create_double_beam_assembly(
    doc,
    catalog,
    beam_label,
    assembly_name,
    x_left_beam_ft,
    y_start_ft,
    z_base_in,
    beam_length_ft,
    pile_width_in=12.0,
    pile_y_positions_ft=None,
):
    """
    Create a double beam assembly with blocking.

    Args:
        doc: FreeCAD document
        catalog: Catalog list (from beach_common.load_beach_catalog)
        beam_label: Stock label for beams (e.g., "2x12x192" for 16', "2x12x96" for 8')
        assembly_name: Name for the assembly group
        x_left_beam_ft: X position of left beam's center (feet)
        y_start_ft: Y starting position (feet)
        z_base_in: Z base elevation (inches above datum)
        beam_length_ft: Beam length in feet (16 or 8)
        pile_width_in: Pile cross-section width in inches (default 12")
        pile_y_positions_ft: List of pile Y positions to avoid when placing blocking

    Returns:
        Group object containing all parts (left beam, blocking, right beam)
    """
    beam_stock = bc.find_stock(catalog, beam_label)
    beam_thick_in = float(beam_stock["actual_thickness_in"])
    beam_depth_in = float(beam_stock["actual_width_in"])
    beam_len_in = beam_length_ft * 12.0

    # Blocking parameters
    blocking_len_in = beam_depth_in - 3.0  # 11.25" - 3" = 8.25"
    blocking_thick_in = beam_thick_in  # Same as beam (1.5")
    blocking_depth_in = beam_depth_in  # Same as beam (11.25")
    blocking_spacing_ft = 2.0  # 24" OC

    # Create assembly (App::Part, not DocumentObjectGroup)
    # Clear existing assembly if rerunning
    existing = doc.getObject(assembly_name)
    if existing:
        doc.removeObject(existing.Name)
        App.Console.PrintMessage(f"[beam_assemblies] Removed existing assembly: {assembly_name}\n")

    # Create assembly container (App::Part has spatial properties)
    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    App.Console.PrintMessage(
        f"[beam_assemblies] Created assembly: {assembly.Name} (type: {assembly.TypeId})\n"
    )

    created = []

    # 1. Left beam (notched into left side of piles)
    # Note: make_beam() centers the beam on x_ft, so add beam_thick/2 to get left face alignment
    name_left = f"{assembly_name}_Beam_L"
    beam_left = bc.make_beam(
        doc,
        catalog,
        beam_label,
        name_left,
        x_left_beam_ft,
        y_start_ft,
        z_base_in,
        beam_len_in,
        orientation="Y",
    )
    created.append(beam_left)

    # Get left beam bounding box for blocking placement
    beam_left_bb = beam_left.Shape.BoundBox

    # 2. Blocking pieces (24" OC along beam length)
    # Left face of blocking aligns to right face of left beam
    # Skip blocking at pile positions (piles sit at beam/pile intersections)
    num_blocking = int(beam_length_ft / blocking_spacing_ft) + 1
    pile_tolerance_ft = 1.0  # Avoid blocking within 1' of piles

    for i in range(num_blocking):
        y_offset_ft = i * blocking_spacing_ft
        y_pos_ft = y_start_ft + y_offset_ft

        # Skip if blocking would extend past beam end
        if y_offset_ft > beam_length_ft - (blocking_thick_in / 12.0):
            continue

        # Skip if blocking would interfere with piles
        if pile_y_positions_ft:
            skip_this_blocking = False
            for pile_y_ft in pile_y_positions_ft:
                if abs(y_pos_ft - pile_y_ft) < pile_tolerance_ft:
                    skip_this_blocking = True
                    break
            if skip_this_blocking:
                continue

        # Create blocking piece
        # Left face of blocking aligns to right face of left beam
        # So blocking's X position is: beam_left.XMax
        blocking_name = f"{assembly_name}_Blocking_{i}"
        blocking = doc.addObject("Part::Feature", blocking_name)
        blocking.Shape = Part.makeBox(
            bc.inch(blocking_len_in), bc.inch(blocking_thick_in), bc.inch(blocking_depth_in)
        )
        blocking.Placement.Base = App.Vector(beam_left_bb.XMax, bc.ft(y_pos_ft), bc.inch(z_base_in))
        bc.attach_beach_metadata(blocking, beam_stock, beam_label)
        created.append(blocking)

    # 3. Right beam (notched into right side of piles)
    # Right beam's RIGHT FACE aligns with right side of pile
    # Pile center is at xi_ft (passed as x_left_beam_ft + pile_width/2 - beam_thick/2)
    # So pile center xi_ft = x_left_beam_ft + beam_thick/2 - pile_width/2 + pile_width/2 + beam_thick/2
    # Actually simpler: right face = left face + pile_width
    # Right beam: x_right_beam_ft + beam_thick/2 = x_left_beam_ft - beam_thick/2 + pile_width
    # Therefore: x_right_beam_ft = x_left_beam_ft + pile_width/12 - beam_thick/12
    x_right_beam_ft = x_left_beam_ft + (pile_width_in / 12.0) - (beam_thick_in / 12.0)
    name_right = f"{assembly_name}_Beam_R"
    beam_right = bc.make_beam(
        doc,
        catalog,
        beam_label,
        name_right,
        x_right_beam_ft,
        y_start_ft,
        z_base_in,
        beam_len_in,
        orientation="Y",
    )
    created.append(beam_right)

    # Add all parts to assembly (App::Part uses addObject, not Group)
    App.Console.PrintMessage(f"[beam_assemblies] Adding {len(created)} parts to assembly...\n")
    for obj in created:
        assembly.addObject(obj)

    App.Console.PrintMessage(
        f"[beam_assemblies] ✓ Assembly complete: {assembly_name} ({len(created)} parts)\n"
    )

    return assembly


def create_double_beam_16ft(
    doc,
    catalog,
    x_left_beam_ft,
    y_start_ft,
    z_base_in,
    assembly_idx=0,
    pile_width_in=12.0,
    pile_y_positions_ft=None,
):
    """
    Create a 16-foot double beam assembly with blocking.

    Args:
        doc: FreeCAD document
        catalog: Catalog list
        x_left_beam_ft: X position of left beam's center (feet)
        y_start_ft: Y starting position (feet)
        z_base_in: Z base elevation (inches)
        assembly_idx: Index for unique naming (default 0)
        pile_width_in: Pile cross-section width (default 12")
        pile_y_positions_ft: List of pile Y positions to avoid

    Returns:
        Group object containing assembly
    """
    beam_label = "2x12x192"  # 16' beam
    beam_length_ft = 16.0
    assembly_name = f"Double_Beam_16ft_{assembly_idx}"

    return create_double_beam_assembly(
        doc,
        catalog,
        beam_label,
        assembly_name,
        x_left_beam_ft,
        y_start_ft,
        z_base_in,
        beam_length_ft,
        pile_width_in,
        pile_y_positions_ft,
    )


def create_double_beam_8ft(
    doc,
    catalog,
    x_left_beam_ft,
    y_start_ft,
    z_base_in,
    assembly_idx=0,
    pile_width_in=12.0,
    pile_y_positions_ft=None,
):
    """
    Create an 8-foot double beam assembly with blocking.

    Args:
        doc: FreeCAD document
        catalog: Catalog list
        x_left_beam_ft: X position of left beam's center (feet)
        y_start_ft: Y starting position (feet)
        z_base_in: Z base elevation (inches)
        assembly_idx: Index for unique naming (default 0)
        pile_width_in: Pile cross-section width (default 12")
        pile_y_positions_ft: List of pile Y positions to avoid

    Returns:
        Group object containing assembly
    """
    beam_label = "2x12x96"  # 8' beam
    beam_length_ft = 8.0
    assembly_name = f"Double_Beam_8ft_{assembly_idx}"

    return create_double_beam_assembly(
        doc,
        catalog,
        beam_label,
        assembly_name,
        x_left_beam_ft,
        y_start_ft,
        z_base_in,
        beam_length_ft,
        pile_width_in,
        pile_y_positions_ft,
    )


if __name__ == "__main__":
    print("[beam_assemblies] This module provides beam assembly creation helpers.")
    print("[beam_assemblies] Import into your macro: import beam_assemblies as ba")
