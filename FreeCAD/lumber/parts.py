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
)
from lumber_common import (
    make_hanger as make_hanger_helper,
)

import FreeCAD as App


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
