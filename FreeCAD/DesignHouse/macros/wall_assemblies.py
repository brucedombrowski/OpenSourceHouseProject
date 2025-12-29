#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wall_assemblies.py - Wall assembly creation functions for standard wall modules.

Provides reusable functions for creating wall assemblies as App::Part objects
(instead of DocumentObjectGroup) to enable bounding box queries and spatial operations.

Assembly types:
  1. Window_Wall_Double_3x5 - 8' wide wall with double 3x5 windows
  2. Sliding_Door_72x80 - 8' wide wall with 72" x 80" sliding door opening

All assemblies follow the standard pattern:
  - Create App::Part assembly container
  - Create all parts (plates, studs, headers, etc.)
  - Add parts to assembly via addObject()
  - Recompute document
  - Return assembly

For Luke Dombrowski. Stay Alive.
"""

import os
import sys

import Part

import FreeCAD as App

# Add lumber directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import lumber_common as lc  # noqa: E402


def create_window_wall_double_3x5(
    doc,
    catalog_rows,
    assembly_name="Window_Wall_Double_3x5",
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    make_pressure_treated=False,
    use_debug_colors=False,
):
    """
    Create an 8' wide wall with double 3x5 windows as an App::Part assembly.

    Design (from Window_Wall_Double_3x5.FCMacro):
        - 8' wide (96") wall with 2x4 framing
        - Bottom and top plates (2x4x96)
        - End king studs (2x4x104.625)
        - Jack studs (80") supporting header
        - Built-up header (2x12 + 0.5" ply + 2x12 = 3.5" total)
        - Cap plate atop header
        - Header blocks (7 @ 16" OC) from cap plate to top plate
        - Bottom short studs (15.5") with double cap (2x4x90)
        - Six 60" studs forming two 36" window openings
        - Top cap over 60" studs

    Orientation: X = wall thickness (1.5"), Y = wall length (96"), Z = vertical

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data (from lumber_common.load_catalog)
        assembly_name: Name for the assembly (default "Window_Wall_Double_3x5")
        x_base: X position offset (inches)
        y_base: Y position offset (inches)
        z_base: Z position offset (inches)
        make_pressure_treated: If True, use PT lumber (default False)
        use_debug_colors: If True, apply fixed debug colors (default False)

    Returns:
        App::Part assembly containing all wall parts
    """
    # Parameters (inches)
    wall_length = 96.0
    plate_label = "2x4x96"
    king_label = "2x4x104.625"
    jack_label = "2x4x96"  # cut to height
    jack_height = 80.0
    header_label = "2x12x96"  # cut to header_length
    header_length = 93.0  # 7'9" leaving 1.5" at each end inside kings
    header_height = 11.25
    ply_thickness = 0.5  # ripped sheet between header plies
    ply_label = "plywood_0.5x4x8"

    # Lookup catalog entries
    def catalog_row(label):
        key = label + "_PT" if make_pressure_treated else label
        row = lc.find_stock(catalog_rows, key)
        if not row:
            raise ValueError(f"Label '{key}' not found in catalog")
        return row, key

    plate_row, plate_key = catalog_row(plate_label)
    king_row, king_key = catalog_row(king_label)
    jack_row, jack_key = catalog_row(jack_label)
    header_row, header_key = catalog_row(header_label)
    ply_row, ply_key = catalog_row(ply_label)

    plate_thick = float(plate_row["actual_thickness_in"])  # 1.5
    stud_thick = float(king_row["actual_thickness_in"])  # 1.5
    stud_width = float(king_row["actual_width_in"])  # 3.5
    stud_length = float(king_row["length_in"])  # 104.625
    header_thick = float(header_row["actual_thickness_in"])  # 1.5

    # Colors (optional debug colors)
    COLOR_PLATE = (1.0, 0.0, 0.0)  # red
    COLOR_KING = (1.0, 1.0, 0.0)  # yellow
    COLOR_JACK = (0.0, 1.0, 0.0)  # green
    COLOR_HEADER = (1.0, 0.5, 0.0)  # orange
    COLOR_PLY = (0.0, 0.6, 1.0)  # blue
    COLOR_BLOCK = (0.0, 0.8, 0.8)  # teal
    COLOR_BOTTOM_SHORT = (0.7, 0.2, 0.7)  # violet

    def apply_debug_color(obj, color):
        if not use_debug_colors or color is None:
            return
        try:
            obj.ViewObject.ShapeColor = color
        except Exception:
            pass

    def inch(x):
        return x * 25.4

    # Create assembly (App::Part, not DocumentObjectGroup)
    existing = doc.getObject(assembly_name)
    if existing:
        doc.removeObject(existing.Name)
        App.Console.PrintMessage(f"[wall_assemblies] Removed existing assembly: {assembly_name}\n")

    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    App.Console.PrintMessage(
        f"[wall_assemblies] Created assembly: {assembly.Name} (type: {assembly.TypeId})\n"
    )

    created = []

    # Plates (bottom and top)
    def make_plate(name, z_offset):
        # Flat plate: X=3.5, Y=length, Z=1.5
        box = Part.makeBox(inch(stud_width), inch(wall_length), inch(plate_thick))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(inch(x_base), inch(y_base), inch(z_base + z_offset))
        lc.attach_metadata(obj, plate_row, plate_key, supplier="lowes")
        apply_debug_color(obj, COLOR_PLATE)
        return obj

    created.append(make_plate("Plate_Bottom", 0.0))
    created.append(make_plate("Plate_Top", plate_thick + stud_length))

    # End kings (rotated 90°: X=3.5, Y=1.5, Z=height)
    def make_king(name, y_offset):
        box = Part.makeBox(inch(stud_width), inch(stud_thick), inch(stud_length))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            inch(x_base), inch(y_base + y_offset), inch(z_base + plate_thick)
        )
        lc.attach_metadata(obj, king_row, king_key, supplier="lowes")
        apply_debug_color(obj, COLOR_KING)
        return obj

    created.append(make_king("King_Left", 0.0))
    created.append(make_king("King_Right", wall_length - stud_thick))

    # Jacks (80") inside kings
    def make_jack(name, y_offset):
        box = Part.makeBox(inch(stud_width), inch(stud_thick), inch(jack_height))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            inch(x_base), inch(y_base + y_offset), inch(z_base + plate_thick)
        )
        lc.attach_metadata(obj, jack_row, jack_key, supplier="lowes")
        try:
            obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = f"{jack_height}"
        except Exception:
            pass
        apply_debug_color(obj, COLOR_JACK)
        return obj

    created.append(make_jack("Jack_Left", stud_thick))
    created.append(make_jack("Jack_Right", wall_length - (2 * stud_thick)))

    # Built-up header: 2x12 + 0.5" ply + 2x12 (total 3.5"), sitting on jacks
    header_start_y = stud_thick  # 1.5" in from left
    header_z_base = plate_thick + jack_height
    cap_plate_z = header_z_base + header_height

    def make_header(name, y_offset, thickness, color, x_offset=0.0):
        box = Part.makeBox(inch(thickness), inch(header_length), inch(header_height))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            inch(x_base + x_offset), inch(y_base + y_offset), inch(z_base + header_z_base)
        )
        lc.attach_metadata(obj, header_row, header_key, supplier="lowes")
        try:
            obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
                f"{header_length}"
            )
        except Exception:
            pass
        apply_debug_color(obj, color)
        return obj

    created.append(
        make_header("Header_2x12_A", header_start_y, header_thick, COLOR_HEADER, x_offset=0.0)
    )

    # 1/2" rip layer
    ply = Part.makeBox(inch(ply_thickness), inch(header_length), inch(header_height))
    ply_obj = doc.addObject("Part::Feature", "Header_Ply_0p5")
    ply_obj.Shape = ply
    ply_obj.Placement.Base = App.Vector(
        inch(x_base + header_thick), inch(y_base + header_start_y), inch(z_base + header_z_base)
    )
    lc.attach_metadata(ply_obj, ply_row, ply_key, supplier="lowes")
    try:
        ply_obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
            f"{header_length}"
        )
    except Exception:
        pass
    apply_debug_color(ply_obj, COLOR_PLY)
    created.append(ply_obj)

    created.append(
        make_header(
            "Header_2x12_B",
            header_start_y,
            header_thick,
            COLOR_HEADER,
            x_offset=header_thick + ply_thickness,
        )
    )

    # Cap plate atop header (2x4x93)
    cap_plate = Part.makeBox(inch(stud_width), inch(header_length), inch(plate_thick))
    cap_plate_obj = doc.addObject("Part::Feature", "Header_Cap_Plate")
    cap_plate_obj.Shape = cap_plate
    cap_plate_obj.Placement.Base = App.Vector(
        inch(x_base), inch(y_base + header_start_y), inch(z_base + cap_plate_z)
    )
    lc.attach_metadata(cap_plate_obj, plate_row, plate_key, supplier="lowes")
    try:
        cap_plate_obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
            f"{header_length}"
        )
    except Exception:
        pass
    apply_debug_color(cap_plate_obj, COLOR_PLATE)
    created.append(cap_plate_obj)

    # Short blocks (11-7/8") on 16" OC atop header
    block_height = 11.875

    def make_block(name, y_offset):
        box = Part.makeBox(inch(stud_width), inch(stud_thick), inch(block_height))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            inch(x_base),
            inch(y_base + y_offset),
            inch(z_base + header_z_base + header_height + plate_thick),
        )
        lc.attach_metadata(obj, plate_row, plate_key, supplier="lowes")
        try:
            obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
                f"{block_height}"
            )
        except Exception:
            pass
        apply_debug_color(obj, COLOR_BLOCK)
        return obj

    blocks_added = 0
    center = header_start_y + stud_thick / 2.0
    while blocks_added < 7 and center <= header_start_y + header_length - (stud_thick / 2.0) + 1e-6:
        y_pos = center - (stud_thick / 2.0)
        created.append(make_block(f"Header_Block_{blocks_added+1}", y_pos))
        blocks_added += 1
        center += 16.0

    # Short studs (15.5") on bottom plate, 16" OC, spanning between jack faces
    short_height = 15.5

    def make_short(name, y_offset):
        box = Part.makeBox(inch(stud_width), inch(stud_thick), inch(short_height))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            inch(x_base), inch(y_base + y_offset), inch(z_base + plate_thick)
        )
        lc.attach_metadata(obj, plate_row, plate_key, supplier="lowes")
        try:
            obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
                f"{short_height}"
            )
        except Exception:
            pass
        apply_debug_color(obj, COLOR_BOTTOM_SHORT)
        return obj

    short_added = 0
    short_base = stud_thick  # start flush to left jack face
    while short_added < 7:
        y_pos = short_base
        if short_added == 0:  # shift first stud +1.5" in Y
            y_pos += 1.5
        if short_added == 6:  # shift the 7th stud -6" in Y
            y_pos -= 6.0
        created.append(make_short(f"Short_Bottom_{short_added+1}", y_pos))
        short_added += 1
        short_base += 16.0

    # 90" 2x4 atop the short studs (cap for lower opening)
    cap_bottom_length = 90.0
    cap_bottom_start_y = header_start_y + (header_length - cap_bottom_length) / 2.0
    cap_bottom = Part.makeBox(inch(stud_width), inch(cap_bottom_length), inch(plate_thick))
    cap_bottom_obj = doc.addObject("Part::Feature", "Bottom_Cap_90")
    cap_bottom_obj.Shape = cap_bottom
    cap_bottom_obj.Placement.Base = App.Vector(
        inch(x_base), inch(y_base + cap_bottom_start_y), inch(z_base + plate_thick + short_height)
    )
    lc.attach_metadata(cap_bottom_obj, plate_row, plate_key, supplier="lowes")
    try:
        cap_bottom_obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
            f"{cap_bottom_length}"
        )
    except Exception:
        pass
    apply_debug_color(cap_bottom_obj, COLOR_PLATE)
    created.append(cap_bottom_obj)

    # Second 2x4x90 cap atop the first cap
    cap_second_z = plate_thick + short_height + plate_thick
    cap_second = Part.makeBox(inch(stud_width), inch(cap_bottom_length), inch(plate_thick))
    cap_second_obj = doc.addObject("Part::Feature", "Bottom_Cap_90_2")
    cap_second_obj.Shape = cap_second
    cap_second_obj.Placement.Base = App.Vector(
        inch(x_base), inch(y_base + cap_bottom_start_y), inch(z_base + cap_second_z)
    )
    lc.attach_metadata(cap_second_obj, plate_row, plate_key, supplier="lowes")
    try:
        cap_second_obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
            f"{cap_bottom_length}"
        )
    except Exception:
        pass
    apply_debug_color(cap_second_obj, COLOR_PLATE)
    created.append(cap_second_obj)

    # Six 60" studs on top of second cap to form two 36" openings
    stud60_height = 60.0
    stud60_z_base = cap_second_z + plate_thick

    stud60_positions = []
    y1 = cap_bottom_start_y
    stud60_positions.append(y1)
    y2 = y1 + 36.0
    stud60_positions.append(y2)
    y3 = y2 + stud_thick
    stud60_positions.append(y3)
    y4 = y3 + 15.0
    stud60_positions.append(y4)
    y5 = y4 + stud_thick
    stud60_positions.append(y5)
    y6 = y5 + 36.0 - 1.5
    stud60_positions.append(y6)

    def make_stud60(name, y_offset):
        box = Part.makeBox(inch(stud_width), inch(stud_thick), inch(stud60_height))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            inch(x_base), inch(y_base + y_offset), inch(z_base + stud60_z_base)
        )
        lc.attach_metadata(obj, plate_row, plate_key, supplier="lowes")
        try:
            obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
                f"{stud60_height}"
            )
        except Exception:
            pass
        apply_debug_color(obj, COLOR_KING)
        return obj

    for idx, y_pos in enumerate(stud60_positions, start=1):
        created.append(make_stud60(f"Stud60_{idx}", y_pos))

    # Top 2x4x90 cap over 60" studs
    cap_top_z = stud60_z_base + stud60_height
    cap_top = Part.makeBox(inch(stud_width), inch(cap_bottom_length), inch(plate_thick))
    cap_top_obj = doc.addObject("Part::Feature", "Bottom_Cap_90_3")
    cap_top_obj.Shape = cap_top
    cap_top_obj.Placement.Base = App.Vector(
        inch(x_base), inch(y_base + cap_bottom_start_y), inch(z_base + cap_top_z)
    )
    lc.attach_metadata(cap_top_obj, plate_row, plate_key, supplier="lowes")
    try:
        cap_top_obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
            f"{cap_bottom_length}"
        )
    except Exception:
        pass
    apply_debug_color(cap_top_obj, COLOR_PLATE)
    created.append(cap_top_obj)

    # Add all parts to assembly
    App.Console.PrintMessage(f"[wall_assemblies] Adding {len(created)} parts to assembly...\n")
    for obj in created:
        assembly.addObject(obj)

    App.Console.PrintMessage(
        f"[wall_assemblies] ✓ Assembly complete: {assembly_name} ({len(created)} parts)\n"
    )

    return assembly


def create_sliding_door_72x80(
    doc,
    catalog_rows,
    assembly_name="Sliding_Door_72x80",
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    make_pressure_treated=False,
    use_debug_colors=False,
):
    """
    Create an 8' wide wall with 72" x 80" sliding door opening as an App::Part assembly.

    Design (from Sliding_Door_72x80.FCMacro):
        - 8' wide (96") wall with 2x4 framing
        - Bottom and top plates (2x4x96)
        - End king studs (2x4x104.625)
        - Jack studs (80") supporting header
        - Built-up header (2x12 + 0.5" ply + 2x12 = 3.5" total)
        - Cap plate atop header
        - Header blocks from cap plate to top plate (16" OC)
        - Six 80" studs framing the 72" clear opening

    Orientation: X = wall thickness (1.5"), Y = wall length (96"), Z = vertical

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data (from lumber_common.load_catalog)
        assembly_name: Name for the assembly (default "Sliding_Door_72x80")
        x_base: X position offset (inches)
        y_base: Y position offset (inches)
        z_base: Z position offset (inches)
        make_pressure_treated: If True, use PT lumber (default False)
        use_debug_colors: If True, apply fixed debug colors (default False)

    Returns:
        App::Part assembly containing all wall parts
    """
    # Parameters
    wall_length = 96.0
    opening_height = 80.0
    plate_label = "2x4x96"
    king_label = "2x4x104.625"
    jack_label = "2x4x96"  # cut to height
    jack_height = opening_height
    header_label = "2x12x96"  # cut to length
    header_height = 11.25
    ply_thickness = 0.5  # rip between header plies
    ply_label = "plywood_0.5x4x8"

    # Lookup catalog entries
    def catalog_row(label):
        key = label + "_PT" if make_pressure_treated else label
        row = lc.find_stock(catalog_rows, key)
        if not row:
            raise ValueError(f"Label '{key}' not found in catalog")
        return row, key

    plate_row, plate_key = catalog_row(plate_label)
    king_row, king_key = catalog_row(king_label)
    jack_row, jack_key = catalog_row(jack_label)
    header_row, header_key = catalog_row(header_label)
    ply_row, ply_key = catalog_row(ply_label)

    plate_thick = float(plate_row["actual_thickness_in"])
    stud_thick = float(king_row["actual_thickness_in"])
    stud_width = float(king_row["actual_width_in"])
    stud_length = float(king_row["length_in"])
    header_thick = float(header_row["actual_thickness_in"])

    # Derived dimensions
    header_length = 93.0  # match window macro
    header_start_y = (wall_length - header_length) / 2.0  # centers the opening
    header_z_base = plate_thick + jack_height
    cap_plate_z = header_z_base + header_height

    COLOR_PLATE = (1.0, 0.0, 0.0)
    COLOR_KING = (1.0, 1.0, 0.0)
    COLOR_JACK = (0.0, 1.0, 0.0)
    COLOR_HEADER = (1.0, 0.5, 0.0)
    COLOR_PLY = (0.0, 0.6, 1.0)
    COLOR_BLOCK = (0.0, 0.8, 0.8)

    def apply_debug_color(obj, color):
        if not use_debug_colors or color is None:
            return
        try:
            obj.ViewObject.ShapeColor = color
        except Exception:
            pass

    def inch(x):
        return x * 25.4

    # Create assembly (App::Part, not DocumentObjectGroup)
    existing = doc.getObject(assembly_name)
    if existing:
        doc.removeObject(existing.Name)
        App.Console.PrintMessage(f"[wall_assemblies] Removed existing assembly: {assembly_name}\n")

    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    App.Console.PrintMessage(
        f"[wall_assemblies] Created assembly: {assembly.Name} (type: {assembly.TypeId})\n"
    )

    created = []

    # Plates (bottom and top)
    def make_plate(name, z_offset):
        box = Part.makeBox(inch(stud_width), inch(wall_length), inch(plate_thick))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(inch(x_base), inch(y_base), inch(z_base + z_offset))
        lc.attach_metadata(obj, plate_row, plate_key, supplier="lowes")
        apply_debug_color(obj, COLOR_PLATE)
        return obj

    created.append(make_plate("Plate_Bottom", 0.0))
    created.append(make_plate("Plate_Top", plate_thick + stud_length))

    # End kings
    def make_king(name, y_offset):
        box = Part.makeBox(inch(stud_width), inch(stud_thick), inch(stud_length))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            inch(x_base), inch(y_base + y_offset), inch(z_base + plate_thick)
        )
        lc.attach_metadata(obj, king_row, king_key, supplier="lowes")
        apply_debug_color(obj, COLOR_KING)
        return obj

    created.append(make_king("King_Left", 0.0))
    created.append(make_king("King_Right", wall_length - stud_thick))

    # Jacks (centered 72" opening)
    def make_jack(name, y_offset):
        box = Part.makeBox(inch(stud_width), inch(stud_thick), inch(jack_height))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            inch(x_base), inch(y_base + y_offset), inch(z_base + plate_thick)
        )
        lc.attach_metadata(obj, jack_row, jack_key, supplier="lowes")
        try:
            obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = f"{jack_height}"
        except Exception:
            pass
        apply_debug_color(obj, COLOR_JACK)
        return obj

    created.append(make_jack("Jack_Left", header_start_y))
    created.append(make_jack("Jack_Right", header_start_y + header_length - stud_thick))

    # Additional 80" studs (qty 6) to mirror window module layout
    stud80_positions = [
        header_start_y,  # aligns with left jack
        header_start_y + 7.5,
        header_start_y + 7.5 + stud_thick,
        header_start_y + 7.5 + stud_thick + 73.5,  # leaves 72" clear opening
        header_start_y + 7.5 + (2 * stud_thick) + 73.5,
        header_start_y + header_length - stud_thick,  # aligns with right jack
    ]

    def make_stud80(name, y_offset):
        box = Part.makeBox(inch(stud_width), inch(stud_thick), inch(jack_height))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            inch(x_base), inch(y_base + y_offset), inch(z_base + plate_thick)
        )
        lc.attach_metadata(obj, jack_row, jack_key, supplier="lowes")
        try:
            obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = f"{jack_height}"
        except Exception:
            pass
        apply_debug_color(obj, COLOR_JACK)
        return obj

    for idx, y_pos in enumerate(stud80_positions, start=1):
        created.append(make_stud80(f"Stud80_{idx}", y_pos))

    # Built-up header
    def make_header(name, y_offset, thickness, color, x_offset=0.0):
        box = Part.makeBox(inch(thickness), inch(header_length), inch(header_height))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            inch(x_base + x_offset), inch(y_base + y_offset), inch(z_base + header_z_base)
        )
        lc.attach_metadata(obj, header_row, header_key, supplier="lowes")
        try:
            obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
                f"{header_length}"
            )
        except Exception:
            pass
        apply_debug_color(obj, color)
        return obj

    created.append(
        make_header("Header_2x12_A", header_start_y, header_thick, COLOR_HEADER, x_offset=0.0)
    )

    ply = Part.makeBox(inch(ply_thickness), inch(header_length), inch(header_height))
    ply_obj = doc.addObject("Part::Feature", "Header_Ply_0p5")
    ply_obj.Shape = ply
    ply_obj.Placement.Base = App.Vector(
        inch(x_base + header_thick), inch(y_base + header_start_y), inch(z_base + header_z_base)
    )
    lc.attach_metadata(ply_obj, ply_row, ply_key, supplier="lowes")
    try:
        ply_obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
            f"{header_length}"
        )
    except Exception:
        pass
    apply_debug_color(ply_obj, COLOR_PLY)
    created.append(ply_obj)

    created.append(
        make_header(
            "Header_2x12_B",
            header_start_y,
            header_thick,
            COLOR_HEADER,
            x_offset=header_thick + ply_thickness,
        )
    )

    # Cap plate atop header
    cap_plate = Part.makeBox(inch(stud_width), inch(header_length), inch(plate_thick))
    cap_plate_obj = doc.addObject("Part::Feature", "Header_Cap_Plate")
    cap_plate_obj.Shape = cap_plate
    cap_plate_obj.Placement.Base = App.Vector(
        inch(x_base), inch(y_base + header_start_y), inch(z_base + cap_plate_z)
    )
    lc.attach_metadata(cap_plate_obj, plate_row, plate_key, supplier="lowes")
    try:
        cap_plate_obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
            f"{header_length}"
        )
    except Exception:
        pass
    apply_debug_color(cap_plate_obj, COLOR_PLATE)
    created.append(cap_plate_obj)

    # Short blocks from header cap to top plate (16" OC)
    block_height = 11.875

    def make_block(name, y_offset):
        box = Part.makeBox(inch(stud_width), inch(stud_thick), inch(block_height))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            inch(x_base),
            inch(y_base + y_offset),
            inch(z_base + header_z_base + header_height + plate_thick),
        )
        lc.attach_metadata(obj, plate_row, plate_key, supplier="lowes")
        try:
            obj.addProperty("App::PropertyString", "cut_length_in").cut_length_in = (
                f"{block_height}"
            )
        except Exception:
            pass
        apply_debug_color(obj, COLOR_BLOCK)
        return obj

    center = header_start_y + stud_thick / 2.0
    while center <= header_start_y + header_length - (stud_thick / 2.0) + 1e-6:
        y_pos = center - (stud_thick / 2.0)
        idx = len([o for o in created if o.Name.startswith("Header_Block_")]) + 1
        created.append(make_block(f"Header_Block_{idx}", y_pos))
        center += 16.0

    # Add all parts to assembly
    App.Console.PrintMessage(f"[wall_assemblies] Adding {len(created)} parts to assembly...\n")
    for obj in created:
        assembly.addObject(obj)

    App.Console.PrintMessage(
        f"[wall_assemblies] ✓ Assembly complete: {assembly_name} ({len(created)} parts)\n"
    )

    return assembly


def create_solid_stud_wall(
    doc,
    catalog_rows,
    wall_length_in=192.0,
    assembly_name="Solid_Stud_Wall",
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    make_pressure_treated=False,
    use_debug_colors=False,
):
    """
    Create a solid stud wall (no windows/doors) as an App::Part assembly.

    Design:
        - Custom length wall with 2x4 framing
        - Bottom and top plates (2x4, field-cut to length)
        - Studs at 16" OC (2x4x104.625)
        - End studs at each corner

    Orientation: X = wall thickness (3.5"), Y = wall length, Z = vertical

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data (from lumber_common.load_catalog)
        wall_length_in: Wall length in inches (default 192" = 16')
        assembly_name: Name for the assembly (default "Solid_Stud_Wall")
        x_base: X position offset (inches)
        y_base: Y position offset (inches)
        z_base: Z position offset (inches)
        make_pressure_treated: If True, use PT lumber (default False)
        use_debug_colors: If True, apply fixed debug colors (default False)

    Returns:
        App::Part assembly containing all wall parts
    """
    # Parameters (inches)
    wall_length = wall_length_in
    # Select plate stock based on wall length (use smallest stock that covers)
    if wall_length <= 96:
        plate_label = "2x4x96"
    elif wall_length <= 120:
        plate_label = "2x4x120"
    elif wall_length <= 144:
        plate_label = "2x4x144"
    else:
        plate_label = "2x4x192"  # Max standard length
    stud_label = "2x4x104.625"
    stud_spacing_oc = 16.0

    # Lookup catalog entries
    def catalog_row(label):
        key = label + "_PT" if make_pressure_treated else label
        row = lc.find_stock(catalog_rows, key)
        if not row:
            raise ValueError(f"Label '{key}' not found in catalog")
        return row, key

    plate_row, plate_key = catalog_row(plate_label)
    stud_row, stud_key = catalog_row(stud_label)

    plate_thick = float(plate_row["actual_thickness_in"])  # 1.5"
    stud_thick = float(stud_row["actual_thickness_in"])  # 1.5"
    stud_width = float(stud_row["actual_width_in"])  # 3.5"
    stud_length = float(stud_row["length_in"])  # 104.625"

    # Debug colors
    COLOR_PLATE = (1.0, 0.0, 0.0)
    COLOR_STUD = (0.0, 1.0, 0.0)

    def apply_debug_color(obj, color):
        if not use_debug_colors or color is None:
            return
        try:
            obj.ViewObject.ShapeColor = color
        except Exception:
            pass

    def inch(x):
        return x * 25.4

    # Create assembly (App::Part)
    existing = doc.getObject(assembly_name)
    if existing:
        doc.removeObject(existing.Name)
        App.Console.PrintMessage(f"[wall_assemblies] Removed existing assembly: {assembly_name}\n")

    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    App.Console.PrintMessage(
        f"[wall_assemblies] Created assembly: {assembly.Name} (type: {assembly.TypeId})\n"
    )

    created = []

    # Bottom plate
    bottom_plate = Part.makeBox(inch(stud_width), inch(wall_length), inch(plate_thick))
    bottom_plate_obj = doc.addObject("Part::Feature", f"{assembly_name}_Plate_Bottom")
    bottom_plate_obj.Shape = bottom_plate
    bottom_plate_obj.Placement.Base = App.Vector(inch(x_base), inch(y_base), inch(z_base))
    lc.attach_metadata(bottom_plate_obj, plate_row, plate_key, supplier="lowes")
    apply_debug_color(bottom_plate_obj, COLOR_PLATE)
    created.append(bottom_plate_obj)

    # Top plate
    top_plate_z = z_base + plate_thick + stud_length
    top_plate = Part.makeBox(inch(stud_width), inch(wall_length), inch(plate_thick))
    top_plate_obj = doc.addObject("Part::Feature", f"{assembly_name}_Plate_Top")
    top_plate_obj.Shape = top_plate
    top_plate_obj.Placement.Base = App.Vector(inch(x_base), inch(y_base), inch(top_plate_z))
    lc.attach_metadata(top_plate_obj, plate_row, plate_key, supplier="lowes")
    apply_debug_color(top_plate_obj, COLOR_PLATE)
    created.append(top_plate_obj)

    # Studs at 16" OC
    # First stud at Y=0, then every 16", plus end stud
    stud_positions = []
    y_pos = 0.0
    while y_pos <= wall_length - stud_thick:
        stud_positions.append(y_pos)
        y_pos += stud_spacing_oc

    # Add end stud if not already at the end
    if stud_positions[-1] < wall_length - stud_thick - 0.1:
        stud_positions.append(wall_length - stud_thick)

    for idx, y_pos in enumerate(stud_positions, start=1):
        stud = Part.makeBox(inch(stud_width), inch(stud_thick), inch(stud_length))
        stud_obj = doc.addObject("Part::Feature", f"{assembly_name}_Stud_{idx}")
        stud_obj.Shape = stud
        stud_obj.Placement.Base = App.Vector(
            inch(x_base), inch(y_base + y_pos), inch(z_base + plate_thick)
        )
        lc.attach_metadata(stud_obj, stud_row, stud_key, supplier="lowes")
        apply_debug_color(stud_obj, COLOR_STUD)
        created.append(stud_obj)

    # Add all parts to assembly
    App.Console.PrintMessage(f"[wall_assemblies] Adding {len(created)} parts to assembly...\n")
    for obj in created:
        assembly.addObject(obj)

    App.Console.PrintMessage(
        f"[wall_assemblies] ✓ Assembly complete: {assembly_name} ({len(created)} parts)\n"
    )

    return assembly


def create_solid_stud_wall_16ft(
    doc,
    catalog_rows,
    assembly_name="Solid_Stud_Wall_16ft",
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    make_pressure_treated=False,
    use_debug_colors=False,
):
    """
    Create a 16' (192") solid stud wall. Convenience wrapper for create_solid_stud_wall.
    """
    return create_solid_stud_wall(
        doc,
        catalog_rows,
        wall_length_in=192.0,
        assembly_name=assembly_name,
        x_base=x_base,
        y_base=y_base,
        z_base=z_base,
        make_pressure_treated=make_pressure_treated,
        use_debug_colors=use_debug_colors,
    )


if __name__ == "__main__":
    print("[wall_assemblies] This module provides wall assembly creation helpers.")
    print("[wall_assemblies] Import into your macro: import wall_assemblies as wa")
