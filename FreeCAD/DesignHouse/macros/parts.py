#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Joist module library - reusable functions for creating FreeCAD joist assemblies.

This module provides functions to create standardized joist assemblies (16x16, 16x8, etc.)
that can be instantiated multiple times without name conflicts or exec() issues.

For Luke Dombrowski. Stay Alive.
"""

import Part
from lumber_common import (
    attach_metadata,
    create_assembly,
    find_stock,
    get_assembly_bbox,
    inch,
    make_hanger_for_joist,
)
from lumber_common import (
    make_hanger as make_hanger_helper,
)

import FreeCAD as App

# ============================================================
# PARAMETERIZED JOIST MODULE FUNCTION
# ============================================================
# This is the base function that all size-specific wrappers use.
# Supports arbitrary module dimensions (e.g., 16x16, 16x12, 16x8, 8x8)


def create_joist_module(
    doc,
    catalog_rows,
    module_length_ft=16.0,
    module_width_ft=16.0,
    assembly_name="Joist_Module",
    joist_label="2x12x192",
    rim_label=None,
    make_pressure_treated=False,
    hanger_label="hanger_LU210",
):
    """
    Create a joist assembly (App::Part) with parameterized dimensions.

    This is the core function for creating floor/deck modules. Size-specific
    wrappers (create_joist_module_16x16, etc.) call this with preset dimensions.

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data (from load_catalog)
        module_length_ft: Module length in feet (X dimension, joist direction)
        module_width_ft: Module width in feet (Y dimension, rim direction)
        assembly_name: Unique name for this assembly instance
        joist_label: Stock label for joists (e.g., "2x12x192")
        rim_label: Stock label for rims (defaults to same as joist_label if None)
        make_pressure_treated: If True, append "_PT" to labels
        hanger_label: Hardware label (default: hanger_LU210)

    Returns:
        App::Part assembly object with bounding box ready for snapping

    Module Geometry:
        - Joists run in X direction (module_length)
        - Rims run in Y direction (module_width)
        - Left/Right rims are full module_width
        - Front/Back rims fit between left/right rims
        - Interior joists at 16" OC with first at 14.5" for sheathing alignment
    """
    # Convert feet to inches
    module_length_in = module_length_ft * 12.0 + 3.0  # Add 2 rims @ 1.5" each
    module_width_in = module_width_ft * 12.0

    # Parameters (inches)
    spacing_oc = 16.0  # On-center spacing for interior joists
    hanger_thickness = 0.06  # ~16ga
    hanger_height = 7.8125  # ~7-13/16"
    hanger_seat_depth = 2.0
    hanger_color = None

    # Default rim label to joist label if not specified
    if rim_label is None:
        rim_label = joist_label

    # Resolve stock
    joist_label_use = joist_label + "_PT" if make_pressure_treated else joist_label
    rim_label_use = rim_label + "_PT" if make_pressure_treated else rim_label

    joist_row = find_stock(catalog_rows, joist_label_use)
    rim_row = find_stock(catalog_rows, rim_label_use)
    if not joist_row:
        raise ValueError(f"Joist stock '{joist_label_use}' not found in catalog")
    if not rim_row:
        raise ValueError(f"Rim stock '{rim_label_use}' not found in catalog")

    thick = float(joist_row["actual_thickness_in"])  # 1.5"
    width = float(joist_row["actual_width_in"])  # 11.25" for 2x12
    joist_stock_length = float(joist_row["length_in"])

    # Helper functions
    def make_box(length, thickness, depth):
        return Part.makeBox(inch(length), inch(thickness), inch(depth))

    def make_joist(name, y_pos, length=joist_stock_length, depth=width, joist_thick=thick):
        box = make_box(length, joist_thick, depth)
        shape = doc.addObject("Part::Feature", name)
        shape.Shape = box
        # Place joists inside rims: start at X=thick (left rim's right face)
        shape.Placement.Base = App.Vector(inch(thick), inch(y_pos - joist_thick / 2.0), 0)
        attach_metadata(shape, joist_row, joist_label_use, supplier="lowes")
        return shape

    def make_rim(name, x_pos, length=module_width_in, depth=width, rim_thick=thick):
        box = Part.makeBox(inch(rim_thick), inch(length), inch(depth))
        shape = doc.addObject("Part::Feature", name)
        shape.Shape = box
        shape.Placement.Base = App.Vector(inch(x_pos - rim_thick / 2.0), 0, 0)
        attach_metadata(shape, rim_row, rim_label_use, supplier="lowes")
        return shape

    def make_hanger(name, x_pos, y_center, facing=1):
        h = make_hanger_helper(
            doc,
            name,
            x_pos,
            y_center,
            thick,
            hanger_thickness,
            hanger_height,
            hanger_seat_depth,
            hanger_label,
            direction=facing,
            color=hanger_color,
        )
        if facing < 0:
            pl = h.Placement
            pl.Rotation = App.Rotation(App.Vector(0, 0, 1), 180).multiply(pl.Rotation)
            h.Placement = pl
        return h

    created = []

    # Rims (4 sides)
    # Left/Right rims: run along Y direction (module_width_in)
    created.append(make_rim(f"{assembly_name}_Rim_Left", thick / 2.0, module_width_in))
    created.append(
        make_rim(f"{assembly_name}_Rim_Right", module_length_in - (thick / 2.0), module_width_in)
    )
    # Front/Back rims: run along X direction (module_length_in - 2*thick)
    front_back_length = module_length_in - 2 * thick
    created.append(make_joist(f"{assembly_name}_Rim_Front", thick / 2.0, length=front_back_length))
    created.append(
        make_joist(
            f"{assembly_name}_Rim_Back",
            module_width_in - (thick / 2.0),
            length=front_back_length,
        )
    )

    # Interior joists (special spacing for sheathing alignment)
    # First joist at 14.5" from front rim (allows 4x8 sheathing to land on centers)
    # Subsequent joists at 16" OC
    positions = []
    first_spacing = 14.5  # Distance from front rim center to first joist center
    first_center = thick / 2.0 + first_spacing
    positions.append(first_center)

    # Remaining joists at 16" OC
    y_pos = first_center + spacing_oc
    while y_pos <= module_width_in - thick / 2.0 - spacing_oc:
        positions.append(y_pos)
        y_pos += spacing_oc

    for idx, y_pos in enumerate(positions, start=1):
        created.append(make_joist(f"{assembly_name}_Joist_{idx}", y_pos, joist_stock_length))

    # Hangers on left/right rims
    left_base_x = thick  # Left rim's right face
    right_base_x = module_length_in - thick  # Right rim's left face
    hanger_objs = []
    for idx, y_pos in enumerate(positions, start=1):
        hanger_objs.append(
            make_hanger(f"{assembly_name}_Hanger_L_{idx}", left_base_x, y_pos, facing=1)
        )
        hanger_objs.append(
            make_hanger(f"{assembly_name}_Hanger_R_{idx}", right_base_x, y_pos, facing=-1)
        )

    created.extend(hanger_objs)

    # Create assembly
    App.Console.PrintMessage(f"[parts] Creating assembly '{assembly_name}'...\n")

    # Remove existing assembly if present
    existing = doc.getObject(assembly_name)
    if existing:
        doc.removeObject(existing.Name)
        App.Console.PrintMessage(f"[parts] Removed existing assembly '{assembly_name}'.\n")

    assembly = create_assembly(doc, assembly_name)

    # Add LCS markers for snapping
    lcs_origin = assembly.newObject("PartDesign::CoordinateSystem", f"{assembly_name}_LCS_Origin")
    lcs_origin.Label = "LCS_Origin"
    lcs_origin.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

    lcs_bottom_right = assembly.newObject(
        "PartDesign::CoordinateSystem", f"{assembly_name}_LCS_BottomRight"
    )
    lcs_bottom_right.Label = "LCS_BottomRight"
    lcs_bottom_right.Placement = App.Placement(
        App.Vector(inch(module_length_in), 0, 0), App.Rotation()
    )

    lcs_top_left = assembly.newObject(
        "PartDesign::CoordinateSystem", f"{assembly_name}_LCS_TopLeft"
    )
    lcs_top_left.Label = "LCS_TopLeft"
    lcs_top_left.Placement = App.Placement(App.Vector(0, inch(module_width_in), 0), App.Rotation())

    lcs_top_right = assembly.newObject(
        "PartDesign::CoordinateSystem", f"{assembly_name}_LCS_TopRight"
    )
    lcs_top_right.Label = "LCS_TopRight"
    lcs_top_right.Placement = App.Placement(
        App.Vector(inch(module_length_in), inch(module_width_in), 0), App.Rotation()
    )

    # Create hardware subgroup
    hanger_grp = assembly.newObject("App::DocumentObjectGroup", f"{assembly_name}_Hardware")
    hanger_grp.Label = "Hardware"
    for h in hanger_objs:
        hanger_grp.addObject(h)

    # Add all parts to assembly
    for obj in created:
        if obj not in hanger_objs:
            assembly.addObject(obj)

    # Add hardware group to assembly
    assembly.addObject(hanger_grp)

    doc.recompute()

    bbox = get_assembly_bbox(assembly)
    App.Console.PrintMessage(
        f'[parts] ✓ Assembly \'{assembly_name}\' complete: {bbox.XLength / 25.4:.2f}" x {bbox.YLength / 25.4:.2f}" x {bbox.ZLength / 25.4:.2f}"\n'
    )

    return assembly


# ============================================================
# FRONT DECK MODULE (joists run Y, rims run X)
# ============================================================


def create_deck_module_front(
    doc,
    catalog_rows,
    rim_length_ft=16.0,
    joist_length_ft=12.0,
    assembly_name="Deck_Module_Front",
    joist_label="2x12x144",
    rim_label="2x12x192",
    make_pressure_treated=True,
    hanger_label="hanger_LU210",
):
    """
    Create a front deck joist assembly with rotated orientation.

    For front decks where deck boards run parallel to the house (E-W):
    - Joists run north-south (Y direction) to support E-W deck boards
    - Rims run east-west (X direction) along house front and deck edge

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data
        rim_length_ft: Rim length in feet (X dimension, parallel to house)
        joist_length_ft: Joist length in feet (Y dimension, deck depth)
        assembly_name: Unique name for this assembly
        joist_label: Stock label for joists (e.g., "2x12x144" for 12')
        rim_label: Stock label for rims (e.g., "2x12x192" for 16')
        make_pressure_treated: If True, append "_PT" to labels (default True for decks)
        hanger_label: Hardware label

    Returns:
        App::Part assembly with LCS markers for snapping

    Module Geometry (rotated from standard):
        - Rims run in X direction (rim_length)
        - Joists run in Y direction (joist_length)
        - Front/Back rims are full rim_length
        - Left/Right rims fit between front/back rims
        - Interior joists at 16" OC with first at 14.5" for sheathing alignment
    """
    # Convert feet to inches
    module_x_in = rim_length_ft * 12.0  # X dimension (rim direction)
    module_y_in = joist_length_ft * 12.0 + 3.0  # Y dimension (joist direction + rim thicknesses)

    # Parameters (inches)
    spacing_oc = 16.0
    hanger_thickness = 0.06
    hanger_height = 7.8125
    hanger_seat_depth = 2.0

    # Resolve stock with PT suffix if needed
    joist_label_use = joist_label + "_PT" if make_pressure_treated else joist_label
    rim_label_use = rim_label + "_PT" if make_pressure_treated else rim_label

    joist_row = find_stock(catalog_rows, joist_label_use)
    rim_row = find_stock(catalog_rows, rim_label_use)
    if not joist_row:
        raise ValueError(f"Joist stock '{joist_label_use}' not found in catalog")
    if not rim_row:
        raise ValueError(f"Rim stock '{rim_label_use}' not found in catalog")

    thick = float(joist_row["actual_thickness_in"])  # 1.5"
    depth = float(joist_row["actual_width_in"])  # 11.25" for 2x12

    def make_box(x_len, y_len, z_len):
        return Part.makeBox(inch(x_len), inch(y_len), inch(z_len))

    def make_rim_x(name, y_pos, length=module_x_in):
        """Create rim running in X direction (front/back of deck)."""
        box = make_box(length, thick, depth)
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(0, inch(y_pos - thick / 2.0), 0)
        attach_metadata(obj, rim_row, rim_label_use, supplier="lowes")
        return obj

    def make_joist_y(name, x_pos, length_in):
        """Create joist running in Y direction."""
        box = make_box(thick, length_in, depth)
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        # Place joists inside rims: start at Y=thick (front rim's back face)
        obj.Placement.Base = App.Vector(inch(x_pos - thick / 2.0), inch(thick), 0)
        attach_metadata(obj, joist_row, joist_label_use, supplier="lowes")
        return obj

    def make_hanger_y_front(name, x_center):
        """Create hanger for Y-running joist at front rim (joist south end)."""
        # Joist starts at Y = thick (inside front rim)
        # Front rim face (south side) is at Y = thick
        return make_hanger_for_joist(
            doc,
            name,
            joist_x_in=x_center,
            joist_y_in=thick,  # Y where joist meets front rim
            joist_z_in=0.0,  # Joist bottom Z
            joist_thick_in=thick,
            joist_depth_in=depth,
            rim_face_position_in=thick,  # South face of front rim
            rim_axis="X",  # Front rim runs E-W
            rim_side="south",  # Joist is south of rim interior face
            hanger_thickness_in=hanger_thickness,
            hanger_height_in=hanger_height,
            hanger_seat_depth_in=hanger_seat_depth,
            hanger_label=hanger_label,
        )

    def make_hanger_y_back(name, x_center, module_y):
        """Create hanger for Y-running joist at back rim (joist north end)."""
        # Joist ends at Y = module_y - thick (inside back rim)
        # Back rim face (north side) is at Y = module_y - thick
        return make_hanger_for_joist(
            doc,
            name,
            joist_x_in=x_center,
            joist_y_in=module_y - thick,  # Y where joist meets back rim
            joist_z_in=0.0,  # Joist bottom Z
            joist_thick_in=thick,
            joist_depth_in=depth,
            rim_face_position_in=module_y - thick,  # North face of back rim
            rim_axis="X",  # Back rim runs E-W
            rim_side="north",  # Joist is north of rim interior face
            hanger_thickness_in=hanger_thickness,
            hanger_height_in=hanger_height,
            hanger_seat_depth_in=hanger_seat_depth,
            hanger_label=hanger_label,
        )

    created = []

    # Front and back rims (run in X direction)
    created.append(make_rim_x(f"{assembly_name}_Rim_Front", thick / 2.0))
    created.append(make_rim_x(f"{assembly_name}_Rim_Back", module_y_in - thick / 2.0))

    # Left and right end joists (run in Y direction, connect front/back rims)
    joist_run = module_y_in - 2 * thick  # Length between rims
    created.append(make_joist_y(f"{assembly_name}_Joist_Left", thick / 2.0, joist_run))
    created.append(
        make_joist_y(f"{assembly_name}_Joist_Right", module_x_in - thick / 2.0, joist_run)
    )

    # Interior joists at 16" OC (only if module is wide enough)
    positions = []
    first_spacing = 14.5  # First joist at 14.5" from left edge
    first_center = thick / 2.0 + first_spacing

    # Only add interior joists if they fit within the module bounds
    # Module must be wide enough to fit: left joist + first_spacing + interior joist + clearance + right joist
    min_width_for_interior = thick + first_spacing + thick + 3.0 + thick  # ~22.5"
    if module_x_in >= min_width_for_interior:
        positions.append(first_center)

        # Remaining joists at 16" OC
        next_center = first_center + spacing_oc
        while next_center < module_x_in - thick / 2.0 - 3.0:  # Leave 3" minimum to right joist
            positions.append(next_center)
            next_center += spacing_oc

    # Hardware group
    hanger_grp = doc.addObject("App::DocumentObjectGroup", f"{assembly_name}_Hangers")

    for i, x_center in enumerate(positions):
        joist = make_joist_y(f"{assembly_name}_Joist_{i+1}", x_center, joist_run)
        created.append(joist)
        # Hangers at front and back rims
        hanger_grp.addObject(make_hanger_y_front(f"{assembly_name}_Hanger_Front_{i+1}", x_center))
        hanger_grp.addObject(
            make_hanger_y_back(f"{assembly_name}_Hanger_Back_{i+1}", x_center, module_y_in)
        )

    # Create assembly
    assembly = create_assembly(doc, assembly_name)
    for obj in created:
        if hasattr(obj, "Shape"):
            assembly.addObject(obj)
    assembly.addObject(hanger_grp)

    # Add LCS markers for snapping
    # Origin at (0, 0, 0) - bottom-left-front corner
    lcs_origin = doc.addObject("PartDesign::CoordinateSystem", f"{assembly_name}_LCS_Origin")
    lcs_origin.Placement.Base = App.Vector(0, 0, 0)
    assembly.addObject(lcs_origin)

    # BottomRight at (module_x_in, 0, 0)
    lcs_br = doc.addObject("PartDesign::CoordinateSystem", f"{assembly_name}_LCS_BottomRight")
    lcs_br.Placement.Base = App.Vector(inch(module_x_in), 0, 0)
    assembly.addObject(lcs_br)

    # TopLeft at (0, module_y_in, 0)
    lcs_tl = doc.addObject("PartDesign::CoordinateSystem", f"{assembly_name}_LCS_TopLeft")
    lcs_tl.Placement.Base = App.Vector(0, inch(module_y_in), 0)
    assembly.addObject(lcs_tl)

    # TopRight at (module_x_in, module_y_in, 0)
    lcs_tr = doc.addObject("PartDesign::CoordinateSystem", f"{assembly_name}_LCS_TopRight")
    lcs_tr.Placement.Base = App.Vector(inch(module_x_in), inch(module_y_in), 0)
    assembly.addObject(lcs_tr)

    doc.recompute()

    bbox = get_assembly_bbox(assembly)
    App.Console.PrintMessage(
        f"[parts] ✓ Front deck '{assembly_name}' complete: "
        f'{bbox.XLength / 25.4:.2f}" x {bbox.YLength / 25.4:.2f}" x {bbox.ZLength / 25.4:.2f}"\n'
    )

    return assembly


def create_deck_module_front_16x12(
    doc,
    catalog_rows,
    assembly_name="Deck_Module_Front_16x12",
    make_pressure_treated=True,
    hanger_label="hanger_LU210",
):
    """
    Create a 16x12 front deck module (16' rims E-W, 12' joists N-S).

    This is the standard front deck module for beach houses:
    - 16' wide (parallel to house front)
    - 12' deep (perpendicular to house front)
    - Joists run N-S to support E-W deck boards
    """
    return create_deck_module_front(
        doc,
        catalog_rows,
        rim_length_ft=16.0,
        joist_length_ft=12.0,
        assembly_name=assembly_name,
        joist_label="2x12x144",  # 12' joists
        rim_label="2x12x192",  # 16' rims
        make_pressure_treated=make_pressure_treated,
        hanger_label=hanger_label,
    )


def create_deck_module_front_16x8(
    doc,
    catalog_rows,
    assembly_name="Deck_Module_Front_16x8",
    make_pressure_treated=True,
    hanger_label="hanger_LU210",
):
    """
    Create a 16x8 front deck module (16' rims E-W, 8' joists N-S).

    This is the standard rear deck module for beach houses:
    - 16' wide (parallel to house back)
    - 8' deep (perpendicular to house back)
    - Joists run N-S to support E-W deck boards
    """
    return create_deck_module_front(
        doc,
        catalog_rows,
        rim_length_ft=16.0,
        joist_length_ft=8.0,
        assembly_name=assembly_name,
        joist_label="2x12x96",  # 8' joists
        rim_label="2x12x192",  # 16' rims
        make_pressure_treated=make_pressure_treated,
        hanger_label=hanger_label,
    )


def create_deck_module_front_16x4(
    doc,
    catalog_rows,
    assembly_name="Deck_Module_Front_16x4",
    make_pressure_treated=True,
    hanger_label="hanger_LU210",
):
    """
    Create a 16x4 front deck module (16' rims E-W, 4' joists N-S).

    Compact rear deck module:
    - 16' wide (parallel to house back)
    - 4' deep (perpendicular to house back)
    - Joists run N-S to support E-W deck boards

    Field cut instructions:
    - 4' joists: cut from whichever stock gives best cost per foot
      (e.g., 8' yields 2 joists, 10' yields 2 + waste, 12' yields 3)
    - Compare $/LF for available stock lengths before ordering
    """
    return create_deck_module_front(
        doc,
        catalog_rows,
        rim_length_ft=16.0,
        joist_length_ft=4.0,
        assembly_name=assembly_name,
        joist_label="2x12x96",  # Use 8' stock for BOM; field cut to 4' (yields 2 per board)
        rim_label="2x12x192",  # 16' rims
        make_pressure_treated=make_pressure_treated,
        hanger_label=hanger_label,
    )


# ============================================================
# SIZE-SPECIFIC CONVENIENCE WRAPPERS
# ============================================================


def create_joist_module_16x12(
    doc,
    catalog_rows,
    assembly_name="Joist_Module_16x12",
    joist_label="2x12x192",
    rim_label="2x12x144",
    make_pressure_treated=False,
    hanger_label="hanger_LU210",
):
    """
    Create a 16x12 joist assembly (16' joists, 12' rims).
    Useful for front deck modules on beach houses.
    """
    return create_joist_module(
        doc,
        catalog_rows,
        module_length_ft=16.0,
        module_width_ft=12.0,
        assembly_name=assembly_name,
        joist_label=joist_label,
        rim_label=rim_label,
        make_pressure_treated=make_pressure_treated,
        hanger_label=hanger_label,
    )


def create_joist_module_16x16(
    doc,
    catalog_rows,
    assembly_name="Joist_Module_16x16",
    stock_label="2x12x192",
    make_pressure_treated=False,
    hanger_label="hanger_LU210",
):
    """
    Create a 16x16 joist assembly (App::Part) with deterministic geometry.

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data (from load_catalog)
        assembly_name: Unique name for this assembly instance
        stock_label: Stock label for joists (default: 2x12x192)
        make_pressure_treated: If True, append "_PT" to labels
        hanger_label: Hardware label (default: hanger_LU210)

    Returns:
        App::Part assembly object with bounding box ready for snapping
    """
    # Parameters (inches)
    module_length = 195.0  # Overall X dimension (16' + 2 rims @ 1.5" each)
    module_width = 192.0  # Overall Y dimension (16')
    spacing_oc = 16.0  # On-center spacing for interior joists
    hanger_thickness = 0.06  # ~16ga
    hanger_height = 7.8125  # ~7-13/16"
    hanger_seat_depth = 2.0
    hanger_color = None

    # Resolve stock
    label_to_use = stock_label + "_PT" if make_pressure_treated else stock_label
    row = find_stock(catalog_rows, label_to_use)
    if not row:
        raise ValueError(f"Stock '{label_to_use}' not found in catalog")

    thick = float(row["actual_thickness_in"])
    width = float(row["actual_width_in"])
    stock_length = float(row["length_in"])

    # Helper functions
    def make_box(length, thickness, depth):
        return Part.makeBox(inch(length), inch(thickness), inch(depth))

    def make_joist(name, y_pos, length=module_length, depth=width, thick=thick):
        box = make_box(length, thick, depth)
        shape = doc.addObject("Part::Feature", name)
        shape.Shape = box
        # Place joists inside rims: start at X=thick (left rim's right face)
        shape.Placement.Base = App.Vector(inch(thick), inch(y_pos - thick / 2.0), 0)
        attach_metadata(shape, row, label_to_use, supplier="lowes")
        return shape

    def make_rim(name, x_pos, length=module_width, depth=width, thick=thick):
        box = Part.makeBox(inch(thick), inch(length), inch(depth))
        shape = doc.addObject("Part::Feature", name)
        shape.Shape = box
        shape.Placement.Base = App.Vector(inch(x_pos - thick / 2.0), 0, 0)
        attach_metadata(shape, row, label_to_use, supplier="lowes")
        return shape

    def make_hanger(name, x_pos, y_center, facing=1):
        h = make_hanger_helper(
            doc,
            name,
            x_pos,
            y_center,
            thick,
            hanger_thickness,
            hanger_height,
            hanger_seat_depth,
            hanger_label,
            direction=facing,
            color=hanger_color,
        )
        if facing < 0:
            pl = h.Placement
            pl.Rotation = App.Rotation(App.Vector(0, 0, 1), 180).multiply(pl.Rotation)
            h.Placement = pl
        return h

    created = []

    # Rims (4 sides)
    # Left/Right rims: run along Y direction (module_width = 192")
    created.append(make_rim(f"{assembly_name}_Rim_Left", thick / 2.0, module_width))
    created.append(
        make_rim(f"{assembly_name}_Rim_Right", module_length - (thick / 2.0), module_width)
    )
    # Front/Back rims: run along X direction (module_length - 2*thick = 192")
    created.append(
        make_joist(f"{assembly_name}_Rim_Front", thick / 2.0, length=module_length - 2 * thick)
    )
    created.append(
        make_joist(
            f"{assembly_name}_Rim_Back",
            module_width - (thick / 2.0),
            length=module_length - 2 * thick,
        )
    )

    # Interior joists (special spacing for sheathing alignment)
    # First joist at 14.5" from front rim (allows 4x8 sheathing to land on centers)
    # Subsequent joists at 16" OC
    positions = []
    first_spacing = 14.5  # Distance from front rim center to first joist center
    first_center = thick / 2.0 + first_spacing
    positions.append(first_center)

    # Remaining joists at 16" OC
    y_pos = first_center + spacing_oc
    while y_pos <= module_width - thick / 2.0 - spacing_oc:
        positions.append(y_pos)
        y_pos += spacing_oc

    for idx, y_pos in enumerate(positions, start=1):
        created.append(make_joist(f"{assembly_name}_Joist_{idx}", y_pos, stock_length))

    # Hangers on left/right rims
    # Hanger positions: helper function adds/subtracts hanger_thickness based on direction
    left_base_x = thick  # Left rim's right face
    right_base_x = module_length - thick  # Right rim's left face
    hanger_objs = []
    for idx, y_pos in enumerate(positions, start=1):
        hanger_objs.append(
            make_hanger(f"{assembly_name}_Hanger_L_{idx}", left_base_x, y_pos, facing=1)
        )
        hanger_objs.append(
            make_hanger(f"{assembly_name}_Hanger_R_{idx}", right_base_x, y_pos, facing=-1)
        )

    created.extend(hanger_objs)

    # Create assembly
    App.Console.PrintMessage(f"[joist_modules] Creating assembly '{assembly_name}'...\n")

    # Remove existing assembly if present
    existing = doc.getObject(assembly_name)
    if existing:
        doc.removeObject(existing.Name)
        App.Console.PrintMessage(f"[joist_modules] Removed existing assembly '{assembly_name}'.\n")

    assembly = create_assembly(doc, assembly_name)

    # Add LCS markers
    lcs_origin = assembly.newObject("PartDesign::CoordinateSystem", f"{assembly_name}_LCS_Origin")
    lcs_origin.Label = "LCS_Origin"
    lcs_origin.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

    lcs_bottom_right = assembly.newObject(
        "PartDesign::CoordinateSystem", f"{assembly_name}_LCS_BottomRight"
    )
    lcs_bottom_right.Label = "LCS_BottomRight"
    lcs_bottom_right.Placement = App.Placement(
        App.Vector(inch(module_length), 0, 0), App.Rotation()
    )

    lcs_top_left = assembly.newObject(
        "PartDesign::CoordinateSystem", f"{assembly_name}_LCS_TopLeft"
    )
    lcs_top_left.Label = "LCS_TopLeft"
    lcs_top_left.Placement = App.Placement(App.Vector(0, inch(module_width), 0), App.Rotation())

    lcs_top_right = assembly.newObject(
        "PartDesign::CoordinateSystem", f"{assembly_name}_LCS_TopRight"
    )
    lcs_top_right.Label = "LCS_TopRight"
    lcs_top_right.Placement = App.Placement(
        App.Vector(inch(module_length), inch(module_width), 0), App.Rotation()
    )

    # Create hardware subgroup
    hanger_grp = assembly.newObject("App::DocumentObjectGroup", f"{assembly_name}_Hardware")
    hanger_grp.Label = "Hardware"
    for h in hanger_objs:
        hanger_grp.addObject(h)

    # Add all parts to assembly
    for obj in created:
        if obj not in hanger_objs:
            assembly.addObject(obj)

    # Add hardware group to assembly
    assembly.addObject(hanger_grp)

    doc.recompute()

    bbox = get_assembly_bbox(assembly)
    App.Console.PrintMessage(
        f'[joist_modules] ✓ Assembly \'{assembly_name}\' complete: {bbox.XLength / 25.4:.2f}" x {bbox.YLength / 25.4:.2f}" x {bbox.ZLength / 25.4:.2f}"\n'
    )

    return assembly


def create_joist_module_16x16_stair_cutout(
    doc,
    catalog_rows,
    assembly_name="Joist_Module_16x16_StairCutout",
    stock_label="2x12x192",
    make_pressure_treated=False,
    hanger_label="hanger_LU210",
    stair_config=None,
):
    """
    Create a 16x16 joist assembly with stair opening cutout.

    This is a specialized version of create_joist_module_16x16 that:
    - Shortens joists that conflict with stair headroom clearance (80" IRC min)
    - Adds a rim joist at the stair cutout edge to frame the opening
    - Removes hangers for shortened joists (they're no longer full-span)

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data
        assembly_name: Unique name for this assembly instance
        stock_label: Stock label for joists (default: 2x12x192)
        make_pressure_treated: If True, append "_PT" to labels
        hanger_label: Hardware label (default: hanger_LU210)
        stair_config: Dict with stair parameters (from config.STAIRS):
            - stair_y_snap_ft: Y position where stairs start (top tread south edge)
            - tread_run_in: Tread depth (10" typical)
            - tread_rise_in: Riser height (7.25" typical)
            - headroom_clearance_in: Required vertical clearance (80" IRC min)
            - stair_width_ft: Stair width (3.0' = 36" typical)

    Returns:
        App::Part assembly object
    """
    # Default headroom clearance if not specified
    if stair_config is None:
        stair_config = {}
    # Note: headroom_clearance_in available from stair_config if needed for future calculations

    # Parameters (inches) - same as create_joist_module_16x16
    module_length = 195.0  # Overall X dimension (16' + 2 rims @ 1.5" each)
    module_width = 192.0  # Overall Y dimension (16')
    spacing_oc = 16.0  # On-center spacing for interior joists
    hanger_thickness = 0.06  # ~16ga
    hanger_height = 7.8125  # ~7-13/16"
    hanger_seat_depth = 2.0
    hanger_color = None

    # Resolve stock
    label_to_use = stock_label + "_PT" if make_pressure_treated else stock_label
    row = find_stock(catalog_rows, label_to_use)
    if not row:
        raise ValueError(f"Stock '{label_to_use}' not found in catalog")

    thick = float(row["actual_thickness_in"])
    width = float(row["actual_width_in"])
    stock_length = float(row["length_in"])

    # Helper functions (same as create_joist_module_16x16)
    def make_box(length, thickness, depth):
        return Part.makeBox(inch(length), inch(thickness), inch(depth))

    def make_joist(name, y_pos, length=module_length, depth=width, thick=thick):
        box = make_box(length, thick, depth)
        shape = doc.addObject("Part::Feature", name)
        shape.Shape = box
        # Place joists inside rims: start at X=thick (left rim's right face)
        shape.Placement.Base = App.Vector(inch(thick), inch(y_pos - thick / 2.0), 0)
        attach_metadata(shape, row, label_to_use, supplier="lowes")
        return shape

    def make_rim(name, x_pos, length=module_width, depth=width, thick=thick):
        box = Part.makeBox(inch(thick), inch(length), inch(depth))
        shape = doc.addObject("Part::Feature", name)
        shape.Shape = box
        shape.Placement.Base = App.Vector(inch(x_pos - thick / 2.0), 0, 0)
        attach_metadata(shape, row, label_to_use, supplier="lowes")
        return shape

    def make_hanger(name, x_pos, y_center, facing=1):
        h = make_hanger_helper(
            doc,
            name,
            x_pos,
            y_center,
            thick,
            hanger_thickness,
            hanger_height,
            hanger_seat_depth,
            hanger_label,
            direction=facing,
            color=hanger_color,
        )
        if facing < 0:
            pl = h.Placement
            pl.Rotation = App.Rotation(App.Vector(0, 0, 1), 180).multiply(pl.Rotation)
            h.Placement = pl
        return h

    created = []

    # Rims (4 sides) - same as create_joist_module_16x16
    # Left/Right rims: run along Y direction (module_width = 192")
    created.append(make_rim(f"{assembly_name}_Rim_Left", thick / 2.0, module_width))
    created.append(
        make_rim(f"{assembly_name}_Rim_Right", module_length - (thick / 2.0), module_width)
    )
    # Front/Back rims: run along X direction (module_length - 2*thick = 192")
    created.append(
        make_joist(f"{assembly_name}_Rim_Front", thick / 2.0, length=module_length - 2 * thick)
    )
    created.append(
        make_joist(
            f"{assembly_name}_Rim_Back",
            module_width - (thick / 2.0),
            length=module_length - 2 * thick,
        )
    )

    # Calculate joist positions (same as create_joist_module_16x16)
    positions = []
    first_spacing = 14.5  # Distance from front rim center to first joist center
    first_center = thick / 2.0 + first_spacing
    positions.append(first_center)

    # Remaining joists at 16" OC
    y_pos = first_center + spacing_oc
    while y_pos <= module_width - thick / 2.0 - spacing_oc:
        positions.append(y_pos)
        y_pos += spacing_oc

    # Calculate which joists need to be shortened for stair headroom
    # Stairs descend north (in +Y direction from stair_y_snap_ft)
    # Need to check if joist bottom interferes with headroom envelope

    # Extract stair dimensions (some reserved for future headroom calculations)
    # stair_y_snap_ft = stair_config.get("stair_y_snap_ft", 28.125)  # Top tread south edge
    # tread_run_in = stair_config.get("tread_run_in", 10.0)  # For headroom envelope calc
    # tread_rise_in = stair_config.get("tread_rise_in", 7.25)  # For headroom envelope calc
    stair_width_ft = stair_config.get("stair_width_ft", 3.0)

    # Convert stair_y_snap_ft to inches (this is in the module's LOCAL coordinate system)
    # The module starts at Y=0, and the front rim is at Y=thick/2
    # We need to find where stair_y_snap_ft falls within this module
    # ASSUMPTION: stair_y_snap_ft is measured from the module's origin
    # So we need to convert it to module-local coordinates

    # Calculate how many joists need to be shortened for stair opening
    # Stairs descend diagonally, requiring headroom clearance along the entire descent path
    # With 80" headroom, 7.25" rise, and stairs descending north from Y=28.125'
    # Need to account for treads + headroom envelope extending into floor area

    stair_cutout_length_in = stair_width_ft * 12.0  # Width of stair opening (36")

    # Estimate joists to shorten based on headroom requirements
    # Each joist is 16" OC, first at 14.5" from front rim
    # For 80" headroom over ~20' descent, need approximately 7-8 joists shortened
    # This accounts for the diagonal headroom envelope as stairs descend
    joists_to_shorten_count = 8  # Shorten first 8 joists for adequate stair headroom

    # Calculate stair rim position FIRST (needed for shortened joist length)
    #
    # ALGORITHM (verified with user measurements):
    # 1. Shortened joists end 10 7/8" before the simple cutout calculation
    # 2. This positions the stair rim to align with pile structure below
    # 3. The offset accounts for pile grid geometry and structural load transfer
    #
    # Given:
    # - Module length: 195" (left rim center to right rim center)
    # - Stair opening width: 36" (stair_cutout_length_in)
    # - Left rim right face at X=thick (1.5")
    # - User-verified offset: 10.875" (10 7/8") for pile alignment
    #
    # Calculate positions:
    # - Base calculation: module_length - stair_cutout_length_in - thick = 157.5"
    # - Apply pile alignment offset: 157.5" - 10.875" = 146.625"
    # - This is where shortened joists end (their right face)

    # Pile alignment offset from user verification (10 7/8")
    pile_alignment_offset_in = 10.875

    # Shortened joist right end position (where they stop)
    shortened_joist_end_x = (
        module_length - stair_cutout_length_in - thick - pile_alignment_offset_in
    )

    # Shortened joist length (from left rim right face to their end)
    shortened_joist_length = shortened_joist_end_x - thick

    # Stair rim sits just after the shortened joists
    # Rim left face aligns with shortened joist right ends
    stair_rim_left_face_x = shortened_joist_end_x
    stair_rim_x = stair_rim_left_face_x  # Left face of rim (used directly in Placement.Base)

    App.Console.PrintMessage(
        f'[parts] Stair cutout: shortening first {joists_to_shorten_count} joists to {shortened_joist_length:.1f}" for stairs\n'
    )

    # Interior joists - shorten the ones that interfere with stairs
    hanger_objs = []
    left_base_x = thick  # Left rim's right face
    right_base_x = module_length - thick  # Right rim's left face

    for idx, y_pos in enumerate(positions, start=1):
        if idx <= joists_to_shorten_count:
            # Shortened joist for stair opening
            # Joist runs from left rim to stair cutout rim (shortened length)
            created.append(
                make_joist(
                    f"{assembly_name}_Joist_{idx}",
                    y_pos,
                    length=shortened_joist_length,
                )
            )
            # Add hanger only on LEFT rim (right end is open for stairs)
            hanger_objs.append(
                make_hanger(f"{assembly_name}_Hanger_L_{idx}", left_base_x, y_pos, facing=1)
            )
        else:
            # Full-length joist (not affected by stair opening)
            created.append(make_joist(f"{assembly_name}_Joist_{idx}", y_pos, stock_length))
            # Add hangers on both rims
            hanger_objs.append(
                make_hanger(f"{assembly_name}_Hanger_L_{idx}", left_base_x, y_pos, facing=1)
            )
            hanger_objs.append(
                make_hanger(f"{assembly_name}_Hanger_R_{idx}", right_base_x, y_pos, facing=-1)
            )

    created.extend(hanger_objs)

    # Add stair cutout rim joist (frames the stair opening)
    # CRITICAL: Stair rim position was calculated above (stair_rim_x) before creating joists
    # This ensures shortened joists end exactly at the rim's left face

    # Rim spans from front rim back face to first uncut joist front face
    # Front rim center is at Y=thick/2, so back face is at Y=thick
    # First uncut joist is at positions[joists_to_shorten_count], front face is thick/2 before center
    front_rim_back_face_y = thick  # Front rim back face
    first_uncut_joist_y = positions[
        joists_to_shorten_count
    ]  # 9th joist center (index 8, since we cut first 8)
    first_uncut_joist_front_face_y = (
        first_uncut_joist_y - thick / 2.0
    )  # Front face of first uncut joist

    # Rim starts at front rim back face and extends to first uncut joist front face
    stair_rim_y_start = front_rim_back_face_y
    stair_rim_y_end = first_uncut_joist_front_face_y
    stair_rim_length = stair_rim_y_end - stair_rim_y_start

    stair_rim = doc.addObject("Part::Feature", f"{assembly_name}_Rim_Stair")
    stair_rim_box = Part.makeBox(inch(thick), inch(stair_rim_length), inch(width))
    stair_rim.Shape = stair_rim_box
    stair_rim.Placement.Base = App.Vector(inch(stair_rim_x), inch(stair_rim_y_start), 0)
    attach_metadata(stair_rim, row, label_to_use, supplier="lowes")
    created.append(stair_rim)

    # Add hangers on stair rim
    # TWO sets of hangers:
    # 1. Hangers facing LEFT (-1) for the shortened joists (connect to their cut ends)
    # 2. Hangers facing RIGHT (+1) for the full-length joists (connect to their continuous span)

    # Hangers for shortened joists (face left toward cut ends)
    # Only the shortened joists connect to the stair rim
    for idx in range(1, joists_to_shorten_count + 1):
        y_pos = positions[idx - 1]
        hanger_objs.append(
            make_hanger(
                f"{assembly_name}_Hanger_StairLeft_{idx}",
                stair_rim_x,  # Left face of stair rim (connects to shortened joist ends)
                y_pos,
                facing=-1,  # Face left toward shortened joist ends
            )
        )

    # Full-length joists (9+) do NOT connect to stair rim - they already have hangers on left+right rims
    # Stair rim ends at first uncut joist's front face, creating the opening

    # Add hangers at stair rim ends to connect it to front rim and first uncut joist
    # South end: connects stair rim to front rim
    hanger_objs.append(
        make_hanger(
            f"{assembly_name}_Hanger_StairRim_South",
            stair_rim_x,  # Left face of stair rim
            stair_rim_y_start,  # South end (front rim connection)
            facing=-1,  # Face south toward front rim
        )
    )
    # North end: connects stair rim to first uncut joist
    hanger_objs.append(
        make_hanger(
            f"{assembly_name}_Hanger_StairRim_North",
            stair_rim_x,  # Left face of stair rim
            stair_rim_y_end,  # North end (first uncut joist connection)
            facing=1,  # Face north toward first uncut joist
        )
    )

    # ====================
    # STAIR RIM RIGHT (east side of stair opening, aligned with tread east edge)
    # ====================
    # Second stair rim on right (east) side of stair tread
    # Positioned so its EAST face aligns with tread east edge
    tread_width_ft = stair_config.get("tread_width_ft", 3.0)  # 3' stair width

    # Geometry (MODULE-LOCAL coordinates):
    # - Left stair rim left face: stair_rim_x
    # - Left stair rim east face: stair_rim_x + thick
    # - Tread west face: stair_rim_x + thick (aligns with left rim east face)
    # - Tread east face: stair_rim_x + thick + tread_width
    # - Right stair rim east face: stair_rim_x + thick + tread_width (aligns with tread east face)
    # - Right stair rim left face: stair_rim_x + thick + tread_width - thick = stair_rim_x + tread_width
    stair_rim_right_x = stair_rim_x + (tread_width_ft * 12.0)  # MODULE-LOCAL, left face position

    # Same length as left stair rim (spans from front rim to first uncut joist)
    stair_rim_right = doc.addObject("Part::Feature", f"{assembly_name}_Rim_Stair_Right")
    stair_rim_right_box = Part.makeBox(inch(thick), inch(stair_rim_length), inch(width))
    stair_rim_right.Shape = stair_rim_right_box
    stair_rim_right.Placement.Base = App.Vector(inch(stair_rim_right_x), inch(stair_rim_y_start), 0)
    attach_metadata(stair_rim_right, row, label_to_use, supplier="lowes")
    created.append(stair_rim_right)

    # Hangers at right stair rim ends
    hanger_objs.append(
        make_hanger(
            f"{assembly_name}_Hanger_StairRimRight_South",
            stair_rim_right_x,
            stair_rim_y_start,
            facing=-1,  # Face south toward front rim
        )
    )
    hanger_objs.append(
        make_hanger(
            f"{assembly_name}_Hanger_StairRimRight_North",
            stair_rim_right_x,
            stair_rim_y_end,
            facing=1,  # Face north toward first uncut joist
        )
    )

    # ====================
    # BABY JOISTS (between right stair rim and outer right rim)
    # ====================
    # Short joists spanning from right stair rim (east face) to outer right rim (left face)
    # These frame the right side of the stair opening
    baby_joist_start_x = stair_rim_right_x + thick  # Right stair rim east face
    baby_joist_end_x = right_base_x  # Outer right rim left face
    baby_joist_length = baby_joist_end_x - baby_joist_start_x

    # Create baby joists for the shortened joist positions (only the first joists_to_shorten_count)
    for idx in range(1, joists_to_shorten_count + 1):
        y_pos = positions[idx - 1]

        # Create baby joist
        baby_joist = doc.addObject("Part::Feature", f"{assembly_name}_BabyJoist_{idx}")
        baby_joist_box = Part.makeBox(inch(baby_joist_length), inch(thick), inch(width))
        baby_joist.Shape = baby_joist_box
        baby_joist.Placement.Base = App.Vector(
            inch(baby_joist_start_x),
            inch(y_pos - thick / 2.0),  # Center on Y position
            0,
        )
        attach_metadata(baby_joist, row, label_to_use, supplier="lowes")
        created.append(baby_joist)

    App.Console.PrintMessage(
        f'[parts] Added {joists_to_shorten_count} baby joists ({baby_joist_length:.1f}" long) between right stair rim and outer rim\n'
    )

    # Create assembly (same structure as create_joist_module_16x16)
    App.Console.PrintMessage(f"[parts] Creating stair-cutout assembly '{assembly_name}'...\n")

    # Remove existing assembly if present
    existing = doc.getObject(assembly_name)
    if existing:
        doc.removeObject(existing.Name)
        App.Console.PrintMessage(f"[parts] Removed existing assembly '{assembly_name}'.\n")

    assembly = create_assembly(doc, assembly_name)

    # Add LCS markers
    lcs_origin = assembly.newObject("PartDesign::CoordinateSystem", f"{assembly_name}_LCS_Origin")
    lcs_origin.Label = "LCS_Origin"
    lcs_origin.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

    lcs_bottom_right = assembly.newObject(
        "PartDesign::CoordinateSystem", f"{assembly_name}_LCS_BottomRight"
    )
    lcs_bottom_right.Label = "LCS_BottomRight"
    lcs_bottom_right.Placement = App.Placement(
        App.Vector(inch(module_length), 0, 0), App.Rotation()
    )

    lcs_top_left = assembly.newObject(
        "PartDesign::CoordinateSystem", f"{assembly_name}_LCS_TopLeft"
    )
    lcs_top_left.Label = "LCS_TopLeft"
    lcs_top_left.Placement = App.Placement(App.Vector(0, inch(module_width), 0), App.Rotation())

    lcs_top_right = assembly.newObject(
        "PartDesign::CoordinateSystem", f"{assembly_name}_LCS_TopRight"
    )
    lcs_top_right.Label = "LCS_TopRight"
    lcs_top_right.Placement = App.Placement(
        App.Vector(inch(module_length), inch(module_width), 0), App.Rotation()
    )

    # Create hardware subgroup
    hanger_grp = assembly.newObject("App::DocumentObjectGroup", f"{assembly_name}_Hardware")
    hanger_grp.Label = "Hardware"
    for h in hanger_objs:
        hanger_grp.addObject(h)

    # Add all parts to assembly
    for obj in created:
        if obj not in hanger_objs:
            assembly.addObject(obj)

    # Add hardware group to assembly
    assembly.addObject(hanger_grp)

    doc.recompute()

    bbox = get_assembly_bbox(assembly)
    App.Console.PrintMessage(
        f'[parts] ✓ Stair-cutout assembly \'{assembly_name}\' complete: {bbox.XLength / 25.4:.2f}" x {bbox.YLength / 25.4:.2f}" x {bbox.ZLength / 25.4:.2f}"\n'
    )

    return assembly


def create_joist_module_16x8(
    doc,
    catalog_rows,
    assembly_name="Joist_Module_16x8",
    stock_label="2x12x192",
    rim_label="2x12x96",
    make_pressure_treated=False,
    hanger_label="hanger_LU210",
):
    """
    Create a 16x8 joist assembly (App::Part) with deterministic geometry.

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data (from load_catalog)
        assembly_name: Unique name for this assembly instance
        stock_label: Stock label for joists (default: 2x12x192)
        rim_label: Stock label for rims (default: 2x12x96)
        make_pressure_treated: If True, append "_PT" to labels
        hanger_label: Hardware label (default: hanger_LU210)

    Returns:
        App::Part assembly object with bounding box ready for snapping
    """
    # Parameters (inches)
    module_length = 195.0  # Overall X dimension
    module_width = 96.0  # Overall Y dimension (8')
    spacing_oc = 16.0
    hanger_thickness = 0.06
    hanger_height = 7.8125
    hanger_seat_depth = 2.0
    hanger_color = None

    # Resolve stock
    label_to_use = stock_label + "_PT" if make_pressure_treated else stock_label
    rim_label_to_use = rim_label + "_PT" if make_pressure_treated else rim_label
    row = find_stock(catalog_rows, label_to_use)
    rim_row = find_stock(catalog_rows, rim_label_to_use)
    if not row:
        raise ValueError(f"Stock '{label_to_use}' not found in catalog")
    if not rim_row:
        raise ValueError(f"Rim stock '{rim_label_to_use}' not found in catalog")

    thick = float(row["actual_thickness_in"])
    width = float(row["actual_width_in"])
    stock_length = float(row["length_in"])

    # Helper functions
    def make_box(length, thickness, depth):
        return Part.makeBox(inch(length), inch(thickness), inch(depth))

    def make_joist(name, y_pos, length=module_length, depth=width, thick=thick):
        box = make_box(length, thick, depth)
        shape = doc.addObject("Part::Feature", name)
        shape.Shape = box
        # Place joists inside rims: start at X=thick (left rim's right face)
        shape.Placement.Base = App.Vector(inch(thick), inch(y_pos - thick / 2.0), 0)
        attach_metadata(shape, row, label_to_use, supplier="lowes")
        return shape

    def make_rim(name, x_pos, length=module_width, depth=width, thick=thick):
        box = Part.makeBox(inch(thick), inch(length), inch(depth))
        shape = doc.addObject("Part::Feature", name)
        shape.Shape = box
        shape.Placement.Base = App.Vector(inch(x_pos - thick / 2.0), 0, 0)
        attach_metadata(shape, rim_row, rim_label_to_use, supplier="lowes")
        return shape

    def make_hanger(name, x_pos, y_center, facing=1):
        h = make_hanger_helper(
            doc,
            name,
            x_pos,
            y_center,
            thick,
            hanger_thickness,
            hanger_height,
            hanger_seat_depth,
            hanger_label,
            direction=facing,
            color=hanger_color,
        )
        if facing < 0:
            pl = h.Placement
            pl.Rotation = App.Rotation(App.Vector(0, 0, 1), 180).multiply(pl.Rotation)
            h.Placement = pl
        return h

    created = []

    # Rims at ends - use 8' (96") stock for 16x8 module
    rim_stock_length = float(rim_row["length_in"])
    created.append(make_rim(f"{assembly_name}_Rim_Left", thick / 2.0, rim_stock_length))
    created.append(
        make_rim(f"{assembly_name}_Rim_Right", module_length - (thick / 2.0), rim_stock_length)
    )

    # Interior joists
    positions = []
    first_center = thick / 2.0
    second_center = first_center + 15.25
    positions = [first_center, second_center]

    next_center = second_center + spacing_oc
    while next_center < module_width - (thick / 2.0):
        positions.append(next_center)
        next_center += spacing_oc

    last_center = module_width - (thick / 2.0)
    if positions[-1] != last_center:
        positions.append(last_center)

    for idx, y_pos in enumerate(positions, start=1):
        created.append(make_joist(f"{assembly_name}_Joist_{idx}", y_pos, stock_length))

    # Hangers on rims (skip first/last joist)
    # Hanger positions: helper function adds/subtracts hanger_thickness based on direction
    left_base_x = thick  # Left rim's right face
    right_base_x = module_length - thick  # Right rim's left face
    hanger_objs = []
    for idx, y_pos in enumerate(positions, start=1):
        if idx == 1 or idx == len(positions):
            continue
        hanger_objs.append(
            make_hanger(f"{assembly_name}_Hanger_L_{idx}", left_base_x, y_pos, facing=1)
        )
        hanger_objs.append(
            make_hanger(f"{assembly_name}_Hanger_R_{idx}", right_base_x, y_pos, facing=-1)
        )

    created.extend(hanger_objs)

    # Create assembly
    App.Console.PrintMessage(f"[joist_modules] Creating assembly '{assembly_name}'...\n")

    existing = doc.getObject(assembly_name)
    if existing:
        doc.removeObject(existing.Name)
        App.Console.PrintMessage(f"[joist_modules] Removed existing assembly '{assembly_name}'.\n")

    assembly = create_assembly(doc, assembly_name)

    # Add LCS markers
    lcs_origin = assembly.newObject("PartDesign::CoordinateSystem", f"{assembly_name}_LCS_Origin")
    lcs_origin.Label = "LCS_Origin"
    lcs_origin.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

    lcs_bottom_right = assembly.newObject(
        "PartDesign::CoordinateSystem", f"{assembly_name}_LCS_BottomRight"
    )
    lcs_bottom_right.Label = "LCS_BottomRight"
    lcs_bottom_right.Placement = App.Placement(
        App.Vector(inch(module_length), 0, 0), App.Rotation()
    )

    lcs_top_left = assembly.newObject(
        "PartDesign::CoordinateSystem", f"{assembly_name}_LCS_TopLeft"
    )
    lcs_top_left.Label = "LCS_TopLeft"
    lcs_top_left.Placement = App.Placement(App.Vector(0, inch(module_width), 0), App.Rotation())

    lcs_top_right = assembly.newObject(
        "PartDesign::CoordinateSystem", f"{assembly_name}_LCS_TopRight"
    )
    lcs_top_right.Label = "LCS_TopRight"
    lcs_top_right.Placement = App.Placement(
        App.Vector(inch(module_length), inch(module_width), 0), App.Rotation()
    )

    # Create hardware subgroup
    hanger_grp = assembly.newObject("App::DocumentObjectGroup", f"{assembly_name}_Hardware")
    hanger_grp.Label = "Hardware"
    for h in hanger_objs:
        hanger_grp.addObject(h)

    # Add all parts to assembly
    for obj in created:
        if obj not in hanger_objs:
            assembly.addObject(obj)

    assembly.addObject(hanger_grp)

    doc.recompute()

    bbox = get_assembly_bbox(assembly)
    App.Console.PrintMessage(
        f'[joist_modules] ✓ Assembly \'{assembly_name}\' complete: {bbox.XLength / 25.4:.2f}" x {bbox.YLength / 25.4:.2f}" x {bbox.ZLength / 25.4:.2f}"\n'
    )

    return assembly


def create_joist_module_8x16(
    doc,
    catalog_rows,
    assembly_name="Joist_Module_8x16",
    stock_label="2x12x192",
    make_pressure_treated=False,
    hanger_label="hanger_LU210",
):
    """
    Create an 8x16 joist assembly (8' wide in X, 16' deep in Y).

    Module dimensions:
    - X (width): 96" = 8' (front/back rims use 8' stock)
    - Y (depth): 192" = 16' (left/right rims and joists use 16' stock)

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data
        assembly_name: Unique name for this assembly
        stock_label: Stock label for joists and long rims (default: 2x12x192)
        make_pressure_treated: If True, append "_PT" to labels
        hanger_label: Hardware label (default: hanger_LU210)

    Returns:
        App::Part assembly object
    """
    # Parameters (inches)
    module_length = 99.0  # Overall X dimension (8' + 2 rims @ 1.5" each)
    module_width = 192.0  # Overall Y dimension (16')
    spacing_oc = 16.0  # Joist spacing on-center
    hanger_thickness = 0.06  # ~16ga
    hanger_height = 7.8125  # ~7-13/16"
    hanger_seat_depth = 2.0
    hanger_color = None

    App.Console.PrintMessage(f"[joist_modules] Creating assembly '{assembly_name}'...\n")

    # Resolve stock for joists and long rims (16' stock)
    stock_key = stock_label + ("_PT" if make_pressure_treated else "")
    joist_stock = find_stock(catalog_rows, stock_key)
    if not joist_stock:
        raise ValueError(f"Stock '{stock_key}' not found in catalog")

    # Resolve stock for short rims (8' stock)
    short_rim_key = "2x12x96" + ("_PT" if make_pressure_treated else "")
    short_rim_stock = find_stock(catalog_rows, short_rim_key)
    if not short_rim_stock:
        raise ValueError(f"Stock '{short_rim_key}' not found in catalog")

    # Extract actual dimensions from catalog
    thick = float(joist_stock["actual_thickness_in"])  # 1.5" for 2x lumber
    depth = float(joist_stock["actual_width_in"])  # 11.25" for 2x12
    short_rim_length = float(short_rim_stock["length_in"])  # 96" for 8' stock

    # Helper functions for part creation
    def make_joist(name, y_pos, length_in):
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = Part.makeBox(inch(length_in), inch(thick), inch(depth))
        obj.Placement.Base = App.Vector(0, inch(y_pos - thick / 2.0), 0)
        attach_metadata(obj, joist_stock, stock_key)
        return obj

    def make_rim(name, x_pos, length_in):
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = Part.makeBox(inch(thick), inch(length_in), inch(depth))
        obj.Placement.Base = App.Vector(inch(x_pos - thick / 2.0), 0, 0)
        attach_metadata(obj, joist_stock, stock_key)
        return obj

    def make_short_rim(name, y_pos, length_in):
        """Create front/back rim using 8' stock, positioned between left/right rims"""
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = Part.makeBox(inch(length_in), inch(thick), inch(depth))
        # Start at X=thick (right face of left rim) to span interior width
        obj.Placement.Base = App.Vector(inch(thick), inch(y_pos - thick / 2.0), 0)
        attach_metadata(obj, short_rim_stock, short_rim_key)
        return obj

    def make_hanger(name, x_pos, y_center, facing=1):
        h = make_hanger_helper(
            doc,
            name,
            x_pos,
            y_center,
            thick,
            hanger_thickness,
            hanger_height,
            hanger_seat_depth,
            hanger_label,
            direction=facing,
            color=hanger_color,
        )
        if facing < 0:
            h.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), 180)
        return h

    # Create assembly container
    assembly = create_assembly(doc, assembly_name)

    # Create groups for organization
    joist_grp = doc.addObject("App::DocumentObjectGroup", f"{assembly_name}_Joists")
    rim_grp = doc.addObject("App::DocumentObjectGroup", f"{assembly_name}_Rims")
    hanger_grp = doc.addObject("App::DocumentObjectGroup", f"{assembly_name}_Hangers")

    created = []

    # Rims (4 sides)
    # Left/Right rims: run along Y direction (module_width length)
    created.append(make_rim(f"{assembly_name}_Rim_Left", thick / 2.0, module_width))
    created.append(
        make_rim(f"{assembly_name}_Rim_Right", module_length - (thick / 2.0), module_width)
    )
    # Front/Back rims: run along X direction using 96" stock
    created.append(make_short_rim(f"{assembly_name}_Rim_Front", thick / 2.0, short_rim_length))
    created.append(
        make_short_rim(f"{assembly_name}_Rim_Back", module_width - (thick / 2.0), short_rim_length)
    )

    # Interior joists (special spacing for sheathing alignment)
    # First joist at 14.5" from front rim (allows 4x8 sheathing to land on centers)
    # Subsequent joists at 16" OC
    positions = []
    first_spacing = 14.5  # Distance from front rim center to first joist center
    first_center = thick / 2.0 + first_spacing
    positions.append(first_center)

    # Remaining joists at 16" OC
    y_pos = first_center + spacing_oc
    while y_pos <= module_width - thick / 2.0 - spacing_oc:
        positions.append(y_pos)
        y_pos += spacing_oc

    # Create joists with proper X placement (inside rims)
    for idx, y_pos in enumerate(positions, start=1):
        shape = doc.addObject("Part::Feature", f"{assembly_name}_Joist_{idx}")
        shape.Shape = Part.makeBox(inch(module_length - 2 * thick), inch(thick), inch(depth))
        # Place joists inside rims: start at X=thick (left rim's right face)
        shape.Placement.Base = App.Vector(inch(thick), inch(y_pos - thick / 2.0), 0)
        attach_metadata(shape, joist_stock, stock_key)
        created.append(shape)

    # Hangers at left and right rim faces
    # Hanger positions: helper function adds/subtracts hanger_thickness based on direction
    left_base_x = thick  # Left rim's right face
    right_base_x = module_length - thick  # Right rim's left face
    hanger_objs = []
    for idx, y_pos in enumerate(positions, start=1):
        hanger_objs.append(
            make_hanger(f"{assembly_name}_Hanger_L_{idx}", left_base_x, y_pos, facing=1)
        )
        hanger_objs.append(
            make_hanger(f"{assembly_name}_Hanger_R_{idx}", right_base_x, y_pos, facing=-1)
        )

    # Add parts to groups
    for obj in created:
        if "Rim" in obj.Name:
            rim_grp.addObject(obj)
        else:
            joist_grp.addObject(obj)

    for obj in hanger_objs:
        hanger_grp.addObject(obj)

    # Add groups to assembly
    assembly.addObject(rim_grp)
    assembly.addObject(joist_grp)
    assembly.addObject(hanger_grp)

    doc.recompute()

    bbox = get_assembly_bbox(assembly)
    App.Console.PrintMessage(
        f'[joist_modules] ✓ Assembly \'{assembly_name}\' complete: {bbox.XLength / 25.4:.2f}" x {bbox.YLength / 25.4:.2f}" x {bbox.ZLength / 25.4:.2f}"\n'
    )

    return assembly


def create_joist_module_8x8(
    doc,
    catalog_rows,
    assembly_name="Joist_Module_8x8",
    stock_label="2x12x96",
    make_pressure_treated=False,
    hanger_label="hanger_LU210",
):
    """
    Create an 8x8 joist assembly (8' × 8').

    Module dimensions:
    - X (width): 99" = 1.5" (left rim) + 96" (8') + 1.5" (right rim)
    - Y (depth): 96" = 8'

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data
        assembly_name: Unique name for this assembly
        stock_label: Stock label for joists (default: 2x12x96 for 8' stock)
        make_pressure_treated: If True, append "_PT" to labels
        hanger_label: Hardware label (default: hanger_LU210)

    Returns:
        App::Part assembly object
    """
    # Parameters (inches)
    module_length = 99.0  # Overall X dimension (8' + 2 rims @ 1.5" each)
    module_width = 96.0  # Overall Y dimension (8')
    spacing_oc = 16.0  # Joist spacing on-center
    hanger_thickness = 0.06  # ~16ga
    hanger_height = 7.8125  # ~7-13/16"
    hanger_seat_depth = 2.0
    hanger_color = None

    App.Console.PrintMessage(f"[joist_modules] Creating assembly '{assembly_name}'...\n")

    # Resolve stock
    stock_key = stock_label + ("_PT" if make_pressure_treated else "")
    joist_stock = find_stock(catalog_rows, stock_key)
    if not joist_stock:
        raise ValueError(f"Stock '{stock_key}' not found in catalog")

    # Extract actual dimensions from catalog
    thick = float(joist_stock["actual_thickness_in"])  # 1.5" for 2x lumber
    depth = float(joist_stock["actual_width_in"])  # 11.25" for 2x12

    # Helper functions for part creation
    def make_joist(name, y_pos, length_in, x_offset=0.0):
        """Create joist or front/back rim. x_offset allows positioning between left/right rims."""
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = Part.makeBox(inch(length_in), inch(thick), inch(depth))
        obj.Placement.Base = App.Vector(inch(x_offset), inch(y_pos - thick / 2.0), 0)
        attach_metadata(obj, joist_stock, stock_key)
        return obj

    def make_rim(name, x_pos, length_in):
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = Part.makeBox(inch(thick), inch(length_in), inch(depth))
        obj.Placement.Base = App.Vector(inch(x_pos - thick / 2.0), 0, 0)
        attach_metadata(obj, joist_stock, stock_key)
        return obj

    def make_hanger(name, x_pos, y_center, facing=1):
        h = make_hanger_helper(
            doc,
            name,
            x_pos,
            y_center,
            thick,
            hanger_thickness,
            hanger_height,
            hanger_seat_depth,
            hanger_label,
            direction=facing,
            color=hanger_color,
        )
        if facing < 0:
            h.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), 180)
        return h

    # Create assembly container
    assembly = create_assembly(doc, assembly_name)

    # Create groups for organization
    joist_grp = doc.addObject("App::DocumentObjectGroup", f"{assembly_name}_Joists")
    rim_grp = doc.addObject("App::DocumentObjectGroup", f"{assembly_name}_Rims")
    hanger_grp = doc.addObject("App::DocumentObjectGroup", f"{assembly_name}_Hangers")

    created = []

    # Rims (4 sides)
    # Left/Right rims: run along Y direction (module_width = 96")
    created.append(make_rim(f"{assembly_name}_Rim_Left", thick / 2.0, module_width))
    created.append(
        make_rim(f"{assembly_name}_Rim_Right", module_length - (thick / 2.0), module_width)
    )
    # Front/Back rims: run along X direction, positioned between left/right rims (start at X=thick)
    created.append(
        make_joist(
            f"{assembly_name}_Rim_Front", thick / 2.0, module_length - 2 * thick, x_offset=thick
        )
    )
    created.append(
        make_joist(
            f"{assembly_name}_Rim_Back",
            module_width - (thick / 2.0),
            module_length - 2 * thick,
            x_offset=thick,
        )
    )

    # Interior joists (special spacing for sheathing alignment)
    # First joist at 14.5" from front rim
    # Subsequent joists at 16" OC
    positions = []
    first_spacing = 14.5
    first_center = thick / 2.0 + first_spacing
    positions.append(first_center)

    # Remaining joists at 16" OC
    y_pos = first_center + spacing_oc
    while y_pos <= module_width - thick / 2.0 - spacing_oc:
        positions.append(y_pos)
        y_pos += spacing_oc

    # Create joists with proper X placement (inside rims)
    for idx, y_pos in enumerate(positions, start=1):
        shape = doc.addObject("Part::Feature", f"{assembly_name}_Joist_{idx}")
        shape.Shape = Part.makeBox(inch(module_length - 2 * thick), inch(thick), inch(depth))
        # Place joists inside rims: start at X=thick (left rim's right face)
        shape.Placement.Base = App.Vector(inch(thick), inch(y_pos - thick / 2.0), 0)
        attach_metadata(shape, joist_stock, stock_key)
        created.append(shape)

    # Hangers at left and right rim faces
    left_base_x = thick  # Left rim's right face
    right_base_x = module_length - thick  # Right rim's left face
    hanger_objs = []
    for idx, y_pos in enumerate(positions, start=1):
        hanger_objs.append(
            make_hanger(f"{assembly_name}_Hanger_L_{idx}", left_base_x, y_pos, facing=1)
        )
        hanger_objs.append(
            make_hanger(f"{assembly_name}_Hanger_R_{idx}", right_base_x, y_pos, facing=-1)
        )

    # Add parts to groups
    for obj in created:
        if "Rim" in obj.Name:
            rim_grp.addObject(obj)
        else:
            joist_grp.addObject(obj)

    for obj in hanger_objs:
        hanger_grp.addObject(obj)

    # Add groups to assembly
    assembly.addObject(rim_grp)
    assembly.addObject(joist_grp)
    assembly.addObject(hanger_grp)

    doc.recompute()

    bbox = get_assembly_bbox(assembly)
    App.Console.PrintMessage(
        f'[joist_modules] ✓ Assembly \'{assembly_name}\' complete: {bbox.XLength / 25.4:.2f}" x {bbox.YLength / 25.4:.2f}" x {bbox.ZLength / 25.4:.2f}"\n'
    )

    return assembly


# ============================================================
# SECOND FLOOR JOIST MODULE (LVL rims E-W, 2x12 joists N-S)
# ============================================================


def create_second_floor_module_20x12(
    doc,
    catalog_rows,
    assembly_name="Second_Floor_Module_20x12",
    joist_label="2x12x144",
    rim_label="lvl_1.75x11.875x240",
    make_pressure_treated=False,
    hanger_label="hanger_LU210",
    target_module_width_in=None,
    target_module_depth_in=None,
):
    """
    Create a second floor joist module with LVL rim joists.

    Design:
    - 20' LVL beams as rim joists running E-W (X direction)
    - 12' 2x12 joists running N-S (Y direction) at 16" OC
    - Module dimensions: 20' wide (E-W) × 12' deep (N-S)
    - Designed for 2 columns × 4 rows = 8 modules to cover 40' × 48' floor

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data
        assembly_name: Unique name for this assembly
        joist_label: Stock label for joists (default: 2x12x144 for 12')
        rim_label: Stock label for LVL rims (default: lvl_1.75x11.875x240 for 20')
        make_pressure_treated: If True, append "_PT" to joist labels
        hanger_label: Hardware label (default: hanger_LU210)
        target_module_width_in: Target total module width in inches (including rims).
                                If provided, front/back LVL rims are trimmed to fit.
                                If None, uses full LVL stock length (240").
        target_module_depth_in: Target total module depth in inches (including rims).
                                If provided, left/right LVL rims are trimmed to fit.
                                If None, uses joist stock length + 2*rim_thick.

    Returns:
        App::Part assembly with LCS markers for snapping

    Module Geometry:
        - Front/Back rims (LVL): run in X direction (trimmed if target_module_width_in provided)
        - Left/Right rims (LVL): run in Y direction (trimmed if target_module_depth_in provided)
        - Joists (2x12): run in Y direction at 16" OC
        - First joist at 14.5" from left rim for sheathing alignment
    """
    # Resolve LVL rim stock first (need rim_thick for calculations)
    rim_row = find_stock(catalog_rows, rim_label)
    if not rim_row:
        raise ValueError(f"Rim stock '{rim_label}' not found in catalog")

    rim_thick = float(rim_row["actual_thickness_in"])  # 1.75" for LVL
    rim_depth = float(rim_row["actual_width_in"])  # 11.875" for LVL
    rim_stock_length = float(rim_row["length_in"])  # 240" for 20'

    # Resolve joist stock
    joist_label_use = joist_label + "_PT" if make_pressure_treated else joist_label
    joist_row = find_stock(catalog_rows, joist_label_use)
    if not joist_row:
        raise ValueError(f"Joist stock '{joist_label_use}' not found in catalog")

    joist_thick = float(joist_row["actual_thickness_in"])  # 1.5" for 2x12
    joist_depth = float(joist_row["actual_width_in"])  # 11.25" for 2x12
    joist_stock_length = float(joist_row["length_in"])  # 144" for 12'

    # Calculate module dimensions
    # Geometry: Front/back LVL rims span FULL module width
    #           Left/right rim joists and interior joists are ALL full-length 2x12s (144")
    #           All run N-S (Y direction), parallel to each other
    #
    #          <- total_x_in (module width) ->
    #     +------------------------------------------+
    #     |  Rim_Front (LVL, runs E-W, FULL WIDTH)   |  <- rim_thick (LVL 1.75")
    #     +------------------------------------------+
    #     |Rim |                                |Rim |
    #     |Left|      Joists (run N-S)         |Rght|  <- ALL are 2x12 full length (144")
    #     |2x12|      at 16" OC                |2x12|     running parallel between LVL rims
    #     +------------------------------------------+
    #     |  Rim_Back (LVL, runs E-W, FULL WIDTH)    |  <- rim_thick (LVL 1.75")
    #     +------------------------------------------+
    #
    # Front/back rim (LVL): length = total_x_in (full width)
    # Left/right rim joists (2x12): SAME length as interior joists (full 144" stock)
    # Interior joists (2x12): full 144" stock length

    if target_module_width_in is not None:
        # Target width = front/back LVL rim length (full width)
        total_x_in = target_module_width_in
        rim_front_back_length = total_x_in  # Front/back LVL rims span full width
        if rim_front_back_length > rim_stock_length:
            raise ValueError(
                f'Front/back rim length {rim_front_back_length}" exceeds stock length {rim_stock_length}"'
            )
    else:
        # Use full LVL stock length for front/back rims
        rim_front_back_length = rim_stock_length  # 240"
        total_x_in = rim_front_back_length  # 240" (no added rim thickness)

    if target_module_depth_in is not None:
        # Target depth for module (Y direction)
        # total_y_in = rim_thick (front LVL) + joist_length + rim_thick (back LVL)
        # All 2x12s (left/right rims AND joists) span between front/back LVL rims
        total_y_in = target_module_depth_in
        joist_run = total_y_in - 2 * rim_thick  # Joists span between front/back LVL rims
        if joist_run > joist_stock_length:
            raise ValueError(f'Joist run {joist_run}" exceeds stock length {joist_stock_length}"')
    else:
        # Use full joist stock length - joists are NOT cut
        # All 2x12s (left/right rims AND joists) are full 144" stock
        joist_run = joist_stock_length  # 144" (full length, no cutting)
        total_y_in = rim_thick + joist_run + rim_thick  # 1.75 + 144 + 1.75 = 147.5"

    # Log the calculated dimensions
    App.Console.PrintMessage(
        f"[parts] Module '{assembly_name}': total {total_x_in:.2f}\" x {total_y_in:.2f}\", "
        f'LVL front/back={rim_front_back_length:.2f}", joist run={joist_run:.2f}"\n'
    )

    # Parameters (inches)
    spacing_oc = 16.0
    hanger_thickness = 0.06
    hanger_height = 7.8125
    hanger_seat_depth = 2.0

    def make_box(x_len, y_len, z_len):
        return Part.makeBox(inch(x_len), inch(y_len), inch(z_len))

    def make_rim_front_back(name, y_pos):
        """Create LVL rim running in X direction (front/back of module, FULL WIDTH)."""
        box = make_box(rim_front_back_length, rim_thick, rim_depth)
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        # Position at X=0 (full width), Y=y_pos
        obj.Placement.Base = App.Vector(0, inch(y_pos), 0)
        attach_metadata(obj, rim_row, rim_label, supplier="lowes")
        return obj

    def make_rim_left_right(name, x_pos):
        """Create 2x12 rim joist running in Y direction (left/right sides, between front/back LVL)."""
        # Same length as interior joists - all are full 144" 2x12 stock
        box = make_box(joist_thick, joist_run, joist_depth)
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        # Position between front/back LVL rims, raised so top aligns with LVL top
        obj.Placement.Base = App.Vector(inch(x_pos), inch(rim_thick), inch(joist_z_offset))
        attach_metadata(obj, joist_row, joist_label_use, supplier="lowes")
        return obj

    # Calculate Z offset to align joist tops with LVL beam tops
    # LVL depth (11.875") - joist depth (11.25") = 0.625" offset
    # This gap needs plywood filler strips at the bottom for flush ceiling
    joist_z_offset = rim_depth - joist_depth
    filler_thickness = joist_z_offset  # 0.625" gap to fill

    # Resolve plywood stock for filler strips (use 3/4" ply, ripped to 0.625")
    filler_label = "plywood_0.75x4x8"
    filler_row = find_stock(catalog_rows, filler_label)
    if not filler_row:
        filler_row = find_stock(catalog_rows, "plywood_0.5x4x8")  # Fallback
        filler_label = "plywood_0.5x4x8"

    def make_joist_y(name, x_pos, length_in=None):
        """Create 2x12 joist running in Y direction."""
        # Default to calculated joist_run if not specified
        actual_length = length_in if length_in is not None else joist_run
        box = make_box(joist_thick, actual_length, joist_depth)
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        # Position inside front/back LVL rims and left/right 2x12 rims
        # Y position = rim_thick (after front LVL rim, joists start inside)
        # X position = x_pos centered on joist (already accounts for left 2x12 rim in first_center)
        obj.Placement.Base = App.Vector(
            inch(x_pos - joist_thick / 2.0), inch(rim_thick), inch(joist_z_offset)
        )
        attach_metadata(obj, joist_row, joist_label_use, supplier="lowes")
        return obj

    def make_filler_strip(name, x_pos, length_in=None):
        """Create plywood filler strip at bottom of joist to flush with LVL bottom.

        Leaves space at both ends for joist hangers (hanger_seat_depth on each end).
        """
        actual_length = length_in if length_in is not None else joist_run
        # Filler strip shorter than joist to leave room for hangers on each end
        hanger_clearance = hanger_seat_depth * 2  # 2" clearance on each end = 4" total
        filler_length = actual_length - hanger_clearance
        if filler_length <= 0:
            return None  # Too short for filler
        # Filler strip: same width as joist, shortened length, thickness = gap
        box = make_box(joist_thick, filler_length, filler_thickness)
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        # Position at bottom of joist space (Z=0), offset from front for hanger clearance
        obj.Placement.Base = App.Vector(
            inch(x_pos - joist_thick / 2.0), inch(rim_thick + hanger_seat_depth), 0
        )
        if filler_row:
            attach_metadata(obj, filler_row, filler_label, supplier="lowes")
        return obj

    created = []

    # Front and back rims (LVL, run in X direction, FULL WIDTH)
    created.append(make_rim_front_back(f"{assembly_name}_Rim_Front", 0))
    created.append(make_rim_front_back(f"{assembly_name}_Rim_Back", total_y_in - rim_thick))

    # Left and right rim joists (2x12, run in Y direction, between front/back LVL rims)
    created.append(make_rim_left_right(f"{assembly_name}_Rim_Left", 0))
    created.append(make_rim_left_right(f"{assembly_name}_Rim_Right", total_x_in - joist_thick))

    # Plywood filler strips for left/right rim joists (for flush ceiling with LVL)
    if filler_row and filler_thickness > 0:
        # Left rim filler - position at X = joist_thick/2 (center of left rim joist)
        left_filler = make_filler_strip(f"{assembly_name}_Filler_Rim_Left", joist_thick / 2.0)
        if left_filler:
            created.append(left_filler)
        # Right rim filler - position at X = total_x_in - joist_thick/2 (center of right rim joist)
        right_filler = make_filler_strip(
            f"{assembly_name}_Filler_Rim_Right", total_x_in - joist_thick / 2.0
        )
        if right_filler:
            created.append(right_filler)

    # Interior joists at 16" OC (only if module is wide enough)
    # Joists run N-S (Y direction), positioned along X axis
    # First joist starts after left 2x12 rim (joist_thick from module edge)
    positions = []
    first_spacing = 14.5  # First joist at 14.5" from left rim for sheathing alignment
    first_center = joist_thick + first_spacing  # After left 2x12 rim

    # Only add interior joists if they fit within the module bounds
    positions.append(first_center)

    # Remaining joists at 16" OC
    next_center = first_center + spacing_oc
    while next_center < (total_x_in - joist_thick - 3.0):  # Leave 3" min to right 2x12 rim
        positions.append(next_center)
        next_center += spacing_oc

    # Hardware group
    hanger_grp = doc.addObject("App::DocumentObjectGroup", f"{assembly_name}_Hangers")

    for i, x_center in enumerate(positions):
        joist = make_joist_y(f"{assembly_name}_Joist_{i+1}", x_center)
        created.append(joist)
        # Plywood filler strip at bottom of joist for flush ceiling with LVL
        if filler_row and filler_thickness > 0:
            filler = make_filler_strip(f"{assembly_name}_Filler_{i+1}", x_center)
            if filler:
                created.append(filler)

        # Hangers at front and back LVL rims using new explicit placement function
        # Front hanger: joist meets front LVL rim at Y = rim_thick (south face of rim)
        # Joist is SOUTH of rim face, hanger opens NORTH toward rim
        hanger_grp.addObject(
            make_hanger_for_joist(
                doc,
                f"{assembly_name}_Hanger_Front_{i+1}",
                joist_x_in=x_center,
                joist_y_in=rim_thick,  # Y where joist starts (south face of front rim)
                joist_z_in=joist_z_offset,  # Joist bottom Z
                joist_thick_in=joist_thick,
                joist_depth_in=joist_depth,
                rim_face_position_in=rim_thick,  # South face of front LVL rim
                rim_axis="X",  # Front LVL rim runs E-W
                rim_side="south",  # Joist is south of rim face
                hanger_thickness_in=hanger_thickness,
                hanger_height_in=hanger_height,
                hanger_seat_depth_in=hanger_seat_depth,
                hanger_label=hanger_label,
            )
        )

        # Back hanger: joist meets back LVL rim at Y = total_y_in - rim_thick (north face of rim)
        # Joist is NORTH of rim face, hanger opens SOUTH toward rim
        hanger_grp.addObject(
            make_hanger_for_joist(
                doc,
                f"{assembly_name}_Hanger_Back_{i+1}",
                joist_x_in=x_center,
                joist_y_in=total_y_in - rim_thick,  # Y where joist ends (north face of back rim)
                joist_z_in=joist_z_offset,  # Joist bottom Z
                joist_thick_in=joist_thick,
                joist_depth_in=joist_depth,
                rim_face_position_in=total_y_in - rim_thick,  # North face of back LVL rim
                rim_axis="X",  # Back LVL rim runs E-W
                rim_side="north",  # Joist is north of rim face
                hanger_thickness_in=hanger_thickness,
                hanger_height_in=hanger_height,
                hanger_seat_depth_in=hanger_seat_depth,
                hanger_label=hanger_label,
            )
        )

    # NOTE: Sheathing is added separately after all joist modules are placed

    # Create assembly
    assembly = create_assembly(doc, assembly_name)
    for obj in created:
        if hasattr(obj, "Shape"):
            assembly.addObject(obj)
    assembly.addObject(hanger_grp)

    # Add LCS markers for snapping
    # Origin at (0, 0, 0) - bottom-left-front corner
    lcs_origin = doc.addObject("PartDesign::CoordinateSystem", f"{assembly_name}_LCS_Origin")
    lcs_origin.Placement.Base = App.Vector(0, 0, 0)
    assembly.addObject(lcs_origin)

    # BottomRight at (total_x_in, 0, 0)
    lcs_br = doc.addObject("PartDesign::CoordinateSystem", f"{assembly_name}_LCS_BottomRight")
    lcs_br.Placement.Base = App.Vector(inch(total_x_in), 0, 0)
    assembly.addObject(lcs_br)

    # TopLeft at (0, total_y_in, 0)
    lcs_tl = doc.addObject("PartDesign::CoordinateSystem", f"{assembly_name}_LCS_TopLeft")
    lcs_tl.Placement.Base = App.Vector(0, inch(total_y_in), 0)
    assembly.addObject(lcs_tl)

    # TopRight at (total_x_in, total_y_in, 0)
    lcs_tr = doc.addObject("PartDesign::CoordinateSystem", f"{assembly_name}_LCS_TopRight")
    lcs_tr.Placement.Base = App.Vector(inch(total_x_in), inch(total_y_in), 0)
    assembly.addObject(lcs_tr)

    doc.recompute()

    bbox = get_assembly_bbox(assembly)
    App.Console.PrintMessage(
        f"[parts] ✓ Second floor module '{assembly_name}' complete: "
        f'{bbox.XLength / 25.4:.2f}" x {bbox.YLength / 25.4:.2f}" x {bbox.ZLength / 25.4:.2f}"\n'
    )

    return assembly


def create_sheathing_panel(
    doc,
    catalog_rows,
    name,
    x_in,
    y_in,
    z_in,
    x_size_in=None,
    y_size_in=None,
    panel_label="panel_advantech_4x8",
):
    """
    Create a single sheathing panel (4x8 Advantech, 3/4" thick).

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data
        name: Object name
        x_in: X position (inches)
        y_in: Y position (inches)
        z_in: Z position (inches, top of joists)
        x_size_in: Panel X dimension (inches, default from catalog)
        y_size_in: Panel Y dimension (inches, default from catalog)
        panel_label: Catalog label (default: panel_advantech_4x8)

    Returns:
        Part::Feature panel object
    """
    panel_row = find_stock(catalog_rows, panel_label)
    thick_in = float(panel_row["actual_thickness_in"])
    width_in = float(panel_row["actual_width_in"])  # 48"
    length_in = float(panel_row["length_in"])  # 96"

    # Use provided size or catalog defaults
    x_size = x_size_in if x_size_in is not None else width_in
    y_size = y_size_in if y_size_in is not None else length_in

    # Create panel box
    box = Part.makeBox(inch(x_size), inch(y_size), inch(thick_in))
    panel = doc.addObject("Part::Feature", name)
    panel.Shape = box
    panel.Placement.Base = App.Vector(inch(x_in), inch(y_in), inch(z_in))

    # Attach metadata
    attach_metadata(panel, panel_row, panel_label, supplier="lowes")

    return panel


def create_sheathing_for_floor(
    doc,
    catalog_rows,
    floor_bbox,
    z_offset_in,
    group_name="Floor_Sheathing",
    panel_label="panel_advantech_4x8",
    exclude_left_ft=0.0,
    exclude_right_ft=0.0,
):
    """
    Create sheathing panels to cover a floor assembly.

    Design:
        - 4x8 Advantech panels (3/4" thick)
        - Staggered seams (alternating columns offset by 4')
        - Panels trimmed to fit exact floor dimensions
        - Optional exclusion zones on left/right edges (for deck areas)

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data
        floor_bbox: Bounding box of floor joist assembly (from Part.getShape().BoundBox)
        z_offset_in: Z offset above floor joists (typically joist depth, e.g., 11.25")
        group_name: Name for sheathing group
        panel_label: Catalog label (default: panel_advantech_4x8)
        exclude_left_ft: Exclude sheathing from leftmost N feet (default 0.0)
        exclude_right_ft: Exclude sheathing from rightmost N feet (default 0.0)

    Returns:
        App::Part assembly containing all sheathing panels
    """
    import math

    panel_row = find_stock(catalog_rows, panel_label)
    panel_width_in = float(panel_row["actual_width_in"])  # 48" (X direction)
    panel_length_in = float(panel_row["length_in"])  # 96" (Y direction)

    # Floor dimensions (mm to inches)
    floor_x_min_in = floor_bbox.XMin / 25.4
    floor_y_min_in = floor_bbox.YMin / 25.4
    floor_x_span_in = floor_bbox.XLength / 25.4
    floor_y_span_in = floor_bbox.YLength / 25.4
    floor_z_top_in = (floor_bbox.ZMax / 25.4) + z_offset_in

    # Apply exclusion zones (convert feet to inches)
    exclude_left_in = exclude_left_ft * 12.0
    exclude_right_in = exclude_right_ft * 12.0

    # Adjust effective sheathing area
    sheathing_x_min_in = floor_x_min_in + exclude_left_in
    sheathing_x_span_in = floor_x_span_in - exclude_left_in - exclude_right_in

    App.Console.PrintMessage(
        f"[create_sheathing] Floor bbox (mm): X={floor_bbox.XMin:.1f} to {floor_bbox.XMax:.1f} ({floor_bbox.XLength:.1f}), "
        f"Y={floor_bbox.YMin:.1f} to {floor_bbox.YMax:.1f} ({floor_bbox.YLength:.1f})\n"
    )
    App.Console.PrintMessage(
        f'[create_sheathing] Floor dimensions: {floor_x_span_in:.2f}" x {floor_y_span_in:.2f}" '
        f'at Z={floor_z_top_in:.2f}"\n'
    )
    if exclude_left_in > 0 or exclude_right_in > 0:
        App.Console.PrintMessage(
            f'[create_sheathing] Exclusion zones: left {exclude_left_in:.2f}", right {exclude_right_in:.2f}"\n'
        )
        App.Console.PrintMessage(
            f'[create_sheathing] Sheathing area: {sheathing_x_span_in:.2f}" (from X={sheathing_x_min_in:.2f}")\n'
        )
    App.Console.PrintMessage(
        f'[create_sheathing] Panel size: {panel_width_in:.2f}" x {panel_length_in:.2f}"\n'
    )

    created = []

    # Calculate number of columns (panels across X direction) using sheathing area (not full floor)
    cols = int(math.ceil(sheathing_x_span_in / panel_width_in))
    App.Console.PrintMessage(
        f'[create_sheathing] Calculated {cols} columns ({sheathing_x_span_in:.2f}" / {panel_width_in:.2f}")\n'
    )

    for col in range(cols):
        x0_in = sheathing_x_min_in + (col * panel_width_in)

        # Trim last column if needed
        remaining_x_in = (sheathing_x_min_in + sheathing_x_span_in) - x0_in
        x_size_in = min(panel_width_in, remaining_x_in)

        # Stagger seams: odd columns start with 4' piece
        stagger = col % 2 == 1

        if stagger:
            # Starter 4' piece (48" length)
            created.append(
                create_sheathing_panel(
                    doc,
                    catalog_rows,
                    f"Panel_{col}_0",
                    x0_in,
                    floor_y_min_in,
                    floor_z_top_in,
                    x_size_in=x_size_in,
                    y_size_in=48.0,
                    panel_label=panel_label,
                )
            )
            y_in = floor_y_min_in + 48.0
        else:
            y_in = floor_y_min_in

        # Fill rest of column with 8' panels
        panel_count = 0
        max_panels_per_column = 50  # Safety limit to prevent infinite loops
        while y_in < (floor_y_min_in + floor_y_span_in) and panel_count < max_panels_per_column:
            remaining_y_in = (floor_y_min_in + floor_y_span_in) - y_in
            y_size_in = min(panel_length_in, remaining_y_in)

            # Safety check: if panel would be too small (< 0.1"), skip it
            if y_size_in < 0.1:
                break

            created.append(
                create_sheathing_panel(
                    doc,
                    catalog_rows,
                    f"Panel_{col}_{int(y_in - floor_y_min_in)}",
                    x0_in,
                    y_in,
                    floor_z_top_in,
                    x_size_in=x_size_in,
                    y_size_in=y_size_in,
                    panel_label=panel_label,
                )
            )
            y_in += panel_length_in
            panel_count += 1

        if panel_count >= max_panels_per_column:
            App.Console.PrintWarning(
                f"[create_sheathing] Column {col} hit max panel limit ({max_panels_per_column})\n"
            )

    # Create assembly (App::Part, not DocumentObjectGroup)
    # Clear existing assembly if rerunning
    existing = doc.getObject(group_name)
    if existing:
        doc.removeObject(existing.Name)
        App.Console.PrintMessage(f"[create_sheathing] Removed existing assembly: {group_name}\n")

    # Create assembly container (App::Part has spatial properties)
    assembly = doc.addObject("App::Part", group_name)
    assembly.Label = group_name

    # Add all panels to assembly
    for panel in created:
        assembly.addObject(panel)

    # Recompute to update bounding box
    doc.recompute()

    bbox = get_assembly_bbox(assembly)
    App.Console.PrintMessage(
        f"[create_sheathing] ✓ Created {len(created)} sheathing panels ({group_name}): "
        f'{bbox.XLength / 25.4:.2f}" x {bbox.YLength / 25.4:.2f}" x {bbox.ZLength / 25.4:.2f}"\n'
    )

    return assembly
