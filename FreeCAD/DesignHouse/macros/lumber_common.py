# -*- coding: utf-8 -*-
# Shared helpers for FreeCAD lumber macros

import csv
import os
import sys

import Part

import FreeCAD as App

# Debug/verbosity switches (can be overridden with env vars)
COLOR_DEBUG = os.environ.get("LUMBER_COLOR_DEBUG", "").lower() in ("1", "true", "yes")

# -----------------------
# Color palette helpers
# -----------------------
NOMINAL_COLORS = {
    "2x4": (0.9, 0.35, 0.35),
    "2x6": (0.95, 0.55, 0.25),
    "2x8": (0.95, 0.75, 0.2),
    "2x10": (0.4, 0.7, 0.35),
    "2x12": (0.3, 0.5, 0.85),
    "4x8_panel": (0.25, 0.8, 0.9),
    "hardware": (0.7, 0.7, 0.7),
}

LENGTH_MIN_IN = 96.0  # 8'
LENGTH_MAX_IN = 192.0  # 16'


def clamp(val, lo=0.0, hi=1.0):
    return max(lo, min(hi, val))


def shade_color(base, length_in):
    """Discrete shade bands so 8', 12', 14', 16' are clearly distinct."""
    if not length_in:
        return base
    if length_in <= 100:  # ~8'
        factor = 1.20
    elif length_in <= 130:  # ~10'
        factor = 1.00
    elif length_in <= 170:  # ~14'
        factor = 0.80
    else:  # 16'+
        factor = 0.60
    return tuple(clamp(c * factor, 0.0, 1.0) for c in base)


def color_for_row(row):
    """Pick a color based on nominal and shade by length."""
    if not row:
        return None
    nominal = row.get("nominal", "").lower()
    try:
        length_in = float(row.get("length_in", 0) or 0)
    except Exception:
        length_in = None

    base = None
    for key, val in NOMINAL_COLORS.items():
        if nominal.startswith(key):
            base = val
            break
    if base is None:
        base = (0.8, 0.8, 0.8)
    return shade_color(base, length_in)


def ensure_macro_path():
    """Make sure this macro directory is on sys.path (for nested imports)."""
    here = os.path.dirname(__file__)
    if here not in sys.path:
        sys.path.append(here)


def inch(x):
    return x * 25.4


def resolve_catalog(candidates):
    for p in candidates:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(f"Could not find lumber_catalog.csv. Checked: {candidates}")


def load_catalog(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find_stock(rows, label):
    for r in rows:
        if r.get("label") == label:
            return r
    return None


def attach_metadata(obj, row, label, supplier="lowes"):
    if not row:
        return
    for key in ("sku_lowes", "url_lowes", "sku_hd", "url_hd"):
        if key not in obj.PropertiesList:
            obj.addProperty("App::PropertyString", key)
        obj.__setattr__(key, row.get(key, ""))
    obj.addProperty("App::PropertyString", "supplier").supplier = supplier
    obj.addProperty("App::PropertyString", "label").label = label
    try:
        col = color_for_row(row)
        if col and hasattr(obj, "ViewObject"):
            obj.ViewObject.ShapeColor = col
        if COLOR_DEBUG:
            try:
                length_in = row.get("length_in", "?")
                App.Console.PrintMessage(
                    f"[color-debug] label={label} nominal={row.get('nominal','?')} length_in={length_in} color={col}\n"
                )
            except Exception:
                pass
    except Exception:
        pass


def clear_group(doc, name):
    # Remove any object whose Name or Label matches the desired group name
    targets = []
    for obj in doc.Objects:
        if obj.Name == name or obj.Label == name:
            targets.append(obj)
    for old in targets:
        if hasattr(old, "Group"):
            for c in list(old.Group):
                doc.removeObject(c.Name)
        doc.removeObject(old.Name)


def make_hanger(
    doc,
    name,
    x_pos,
    y_center,
    thick,
    hanger_thickness,
    hanger_height,
    hanger_seat_depth,
    hanger_label="hanger",
    direction=1,
    axis="X",
    debug_components=False,
    color=None,
):
    """
    Build a simple U-shape hanger (rim flange + seat + two side flanges + far flange).
    Built at origin in local coordinates, then translated to the requested rim face.

    axis="X": rim face at x_pos, hanger extends along ±X.
    axis="Y": rim face at y_pos (x_pos arg), hanger extends along ±Y.
    direction=+1 extends into +axis; direction=-1 extends into -axis.

    When debug_components is True, return a colored group of sub-parts instead of a fused solid (used by test macro).
    """
    bh = hanger_height
    bd = hanger_seat_depth
    bt = hanger_thickness
    z0 = -bt  # drop seat below joist bottom
    direction = 1 if direction >= 0 else -1
    axis = (axis or "X").upper()

    # Build at origin in local coordinates: A-axis = seat length, B-axis = joist thickness, Z up
    if axis == "Y":
        # Local A (seat length) -> world Y, Local B (joist thickness) -> world X
        seat = Part.makeBox(inch(thick), inch(bd), inch(bt))  # X=thickness, Y=length
        seat.Placement.Base = App.Vector(0, 0, inch(z0))
        sideL = Part.makeBox(inch(thick), inch(bt), inch(bh))
        sideL.Placement.Base = App.Vector(0, 0, inch(z0))  # shift back -bt in X
        sideL.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), 90)
        sideR = Part.makeBox(inch(thick), inch(bt), inch(bh))
        sideR.Placement.Base = App.Vector(
            inch(thick + bt), 0, inch(z0)
        )  # far side shift +X by hanger thickness
        sideR.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), 90)
        flangeL = Part.makeBox(inch(thick), inch(bt), inch(bh))
        flangeL.Placement.Base = App.Vector(
            -inch(bt + thick), 0, inch(z0)
        )  # rim flange at X=-bt-thick
        flangeR = Part.makeBox(inch(thick), inch(bt), inch(bh))
        flangeR.Placement.Base = App.Vector(
            inch(thick + bt), 0, inch(z0)
        )  # far flange at X=thick+bt

        assembled = seat.fuse([sideL, sideR, flangeL, flangeR])
        # Rotate to flip rim/far orientation when extending toward -Y
        rot_z = 0 if direction > 0 else 180
        assembled.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), rot_z)
        # Translate: center on joist thickness (world X = y_center), rim face to world Y = x_pos
        tx = inch(y_center - (thick / 2.0))  # center on joist thickness (no extra offset)
        ty = inch(x_pos)
        assembled.Placement.Base = App.Vector(tx, ty, 0)
    else:
        # axis == "X": local A -> world X, local B -> world Y
        seat = Part.makeBox(inch(bd), inch(thick), inch(bt))
        seat.Placement.Base = App.Vector(0, 0, inch(z0))
        sideL = Part.makeBox(inch(bd), inch(bt), inch(bh))
        sideL.Placement.Base = App.Vector(0, -inch(bt), inch(z0))
        sideR = Part.makeBox(inch(bd), inch(bt), inch(bh))
        sideR.Placement.Base = App.Vector(0, inch(thick), inch(z0))
        flangeL = Part.makeBox(inch(bt), inch(thick), inch(bh))
        flangeL.Placement.Base = App.Vector(
            0, -inch(bt + thick), inch(z0)
        )  # rim side at x=0, y=-bt-thick
        flangeR = Part.makeBox(inch(bt), inch(thick), inch(bh))
        flangeR.Placement.Base = App.Vector(0, inch(thick + bt), inch(z0))  # far side at Y=thick+bt

        assembled = seat.fuse([sideL, sideR, flangeL, flangeR])
        tx = inch(x_pos)  # rim flange at x_pos
        # Y offset: direction=-1 needs to shift +Y by (bt + thick) to align properly
        y_offset = (bt + thick) if direction < 0 else 0
        ty = inch(y_center - (thick / 2.0) + y_offset)  # center on joist thickness
        assembled.Placement.Base = App.Vector(tx, ty, 0)

    if debug_components:
        # Build individual colored parts and group them for visual debugging.
        colors = {
            "flangeL": (0.8, 0.2, 0.2),  # rim edge
            "seat": (0.2, 0.6, 0.9),
            "sideL": (0.2, 0.8, 0.4),
            "sideR": (0.9, 0.7, 0.2),
            "flangeR": (0.6, 0.4, 0.9),  # far edge
        }
        if color:
            for k in colors:
                colors[k] = color
        pieces = [
            ("flangeL", flangeL),
            ("seat", seat),
            ("sideL", sideL),
            ("sideR", sideR),
            ("flangeR", flangeR),
        ]

        grp = doc.addObject("App::DocumentObjectGroup", name)
        grp.Label = name
        try:
            grp.addProperty("App::PropertyString", "supplier").supplier = "lowes"
            grp.addProperty("App::PropertyString", "label").label = hanger_label
        except Exception:
            pass

        objs = []
        for suffix, solid in pieces:
            part_obj = doc.addObject("Part::Feature", f"{name}_{suffix}")
            part_obj.Shape = solid
            try:
                part_obj.ViewObject.ShapeColor = colors.get(suffix, (0.8, 0.8, 0.8))
            except Exception:
                pass
            objs.append(part_obj)
            grp.addObject(part_obj)
        grp.Group = objs
        return grp
    else:
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = assembled
        obj.addProperty("App::PropertyString", "supplier").supplier = "lowes"
        obj.addProperty("App::PropertyString", "label").label = hanger_label
        # Default to hardware palette if no color provided
        final_color = (
            color if color is not None else NOMINAL_COLORS.get("hardware", (0.7, 0.7, 0.7))
        )
        if final_color:
            try:
                obj.ViewObject.ShapeColor = final_color
            except Exception:
                pass
        return obj


def make_hanger_for_joist(
    doc,
    name,
    joist_x_in,
    joist_y_in,
    joist_z_in,
    joist_thick_in,
    joist_depth_in,
    rim_face_position_in,
    rim_axis="Y",
    rim_side="south",
    hanger_thickness_in=0.06,
    hanger_height_in=7.8125,
    hanger_seat_depth_in=2.0,
    hanger_label="hanger_LU210",
    color=None,
):
    """
    Create a joist hanger positioned correctly relative to a joist and rim.

    The hanger is placed so that:
    - Seat top is at joist bottom (Z = joist_z_in)
    - Rim flange is against the rim face
    - Side flanges wrap around joist sides

    Hanger anatomy (looking down, joist running N-S):
        Rim (LVL)
        =========
        |flange|  <- rim flange (nailed to rim)
        +-----+
        |     |   <- seat (joist bottom rests here)
        +-----+
        || | ||   <- side flanges (wrap joist sides)

    Args:
        doc: FreeCAD document
        name: Object name
        joist_x_in: X position of joist center (inches)
        joist_y_in: Y position where joist meets rim (inches)
        joist_z_in: Z position of joist bottom (inches)
        joist_thick_in: Joist thickness (1.5" for 2x lumber)
        joist_depth_in: Joist depth (11.25" for 2x12)
        rim_face_position_in: Position of rim face along rim_axis (inches)
        rim_axis: "X" if rim runs E-W, "Y" if rim runs N-S
        rim_side: Which side of rim the joist is on:
                  "south"/"north" for X-running rim
                  "west"/"east" for Y-running rim
        hanger_thickness_in: Metal thickness (default 0.06")
        hanger_height_in: Height of side flanges (default 7.8125")
        hanger_seat_depth_in: Depth of seat (default 2.0")
        hanger_label: Catalog label for BOM
        color: Optional color tuple

    Returns:
        Part::Feature object

    Example (joist running N-S, meeting E-W LVL rim at south end):
        make_hanger_for_joist(
            doc, "Hanger_1",
            joist_x_in=16.0,        # Joist center X
            joist_y_in=1.75,        # Y where joist meets rim (rim_thick)
            joist_z_in=0.625,       # Joist bottom Z (raised for top alignment)
            joist_thick_in=1.5,
            joist_depth_in=11.25,
            rim_face_position_in=1.75,  # South face of front LVL rim
            rim_axis="X",           # LVL rim runs E-W
            rim_side="south",       # Joist is south of rim face
        )
    """
    bt = hanger_thickness_in
    bh = hanger_height_in
    bd = hanger_seat_depth_in
    jt = joist_thick_in

    # Seat top is at joist bottom Z
    seat_top_z = joist_z_in
    seat_bottom_z = seat_top_z - bt

    # Build hanger components
    # Seat: under joist, extends toward rim
    # Side flanges: on either side of joist
    # Rim flange: against rim face

    if rim_axis.upper() == "X":
        # Rim runs E-W (X direction), joist runs N-S (Y direction)
        # Hanger seat extends in Y direction toward rim

        if rim_side.lower() in ("south", "front"):
            # Joist is SOUTH of rim, hanger opens to NORTH (toward rim)
            # Seat extends from joist end toward rim (in +Y direction)
            seat_y_start = joist_y_in
            seat_y_end = joist_y_in + bd

            # Rim flange is at rim face (north side of rim)
            flange_y = rim_face_position_in
        else:
            # Joist is NORTH of rim, hanger opens to SOUTH (toward rim)
            seat_y_start = joist_y_in - bd
            seat_y_end = joist_y_in

            # Rim flange is at rim face (south side of rim)
            flange_y = rim_face_position_in

        # Seat box (under joist)
        seat = Part.makeBox(
            inch(jt),  # X = joist thickness
            inch(bd),  # Y = seat depth
            inch(bt),  # Z = hanger thickness
        )
        seat.Placement.Base = App.Vector(
            inch(joist_x_in - jt / 2.0),
            inch(min(seat_y_start, seat_y_end)),
            inch(seat_bottom_z),
        )

        # Side flanges (on east and west sides of joist)
        side_west = Part.makeBox(inch(bt), inch(bd), inch(bh))
        side_west.Placement.Base = App.Vector(
            inch(joist_x_in - jt / 2.0 - bt),
            inch(min(seat_y_start, seat_y_end)),
            inch(seat_bottom_z),
        )

        side_east = Part.makeBox(inch(bt), inch(bd), inch(bh))
        side_east.Placement.Base = App.Vector(
            inch(joist_x_in + jt / 2.0),
            inch(min(seat_y_start, seat_y_end)),
            inch(seat_bottom_z),
        )

        # Rim flange (against rim, spans joist width + side flanges)
        flange_width = jt + 2 * bt  # Joist width + both side flanges
        rim_flange = Part.makeBox(inch(flange_width), inch(bt), inch(bh))
        rim_flange.Placement.Base = App.Vector(
            inch(joist_x_in - jt / 2.0 - bt),
            inch(flange_y - bt) if rim_side.lower() in ("south", "front") else inch(flange_y),
            inch(seat_bottom_z),
        )

    else:
        # Rim runs N-S (Y direction), joist runs E-W (X direction)
        # Hanger seat extends in X direction toward rim

        if rim_side.lower() in ("west", "left"):
            # Joist is WEST of rim, hanger opens to EAST (toward rim)
            seat_x_start = joist_x_in
            seat_x_end = joist_x_in + bd
            flange_x = rim_face_position_in
        else:
            # Joist is EAST of rim, hanger opens to WEST (toward rim)
            seat_x_start = joist_x_in - bd
            seat_x_end = joist_x_in
            flange_x = rim_face_position_in

        # Seat box
        seat = Part.makeBox(inch(bd), inch(jt), inch(bt))
        seat.Placement.Base = App.Vector(
            inch(min(seat_x_start, seat_x_end)),
            inch(joist_y_in - jt / 2.0),
            inch(seat_bottom_z),
        )

        # Side flanges (on north and south sides of joist)
        side_south = Part.makeBox(inch(bd), inch(bt), inch(bh))
        side_south.Placement.Base = App.Vector(
            inch(min(seat_x_start, seat_x_end)),
            inch(joist_y_in - jt / 2.0 - bt),
            inch(seat_bottom_z),
        )

        side_north = Part.makeBox(inch(bd), inch(bt), inch(bh))
        side_north.Placement.Base = App.Vector(
            inch(min(seat_x_start, seat_x_end)),
            inch(joist_y_in + jt / 2.0),
            inch(seat_bottom_z),
        )

        # Rim flange
        flange_height_span = jt + 2 * bt
        rim_flange = Part.makeBox(inch(bt), inch(flange_height_span), inch(bh))
        rim_flange.Placement.Base = App.Vector(
            inch(flange_x - bt) if rim_side.lower() in ("west", "left") else inch(flange_x),
            inch(joist_y_in - jt / 2.0 - bt),
            inch(seat_bottom_z),
        )

    # Fuse all parts
    if rim_axis.upper() == "X":
        assembled = seat.fuse([side_west, side_east, rim_flange])
    else:
        assembled = seat.fuse([side_south, side_north, rim_flange])

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = assembled
    obj.addProperty("App::PropertyString", "supplier").supplier = "lowes"
    obj.addProperty("App::PropertyString", "label").label = hanger_label

    final_color = color if color is not None else NOMINAL_COLORS.get("hardware", (0.7, 0.7, 0.7))
    if final_color:
        try:
            obj.ViewObject.ShapeColor = final_color
        except Exception:
            pass

    return obj


# ============================================================
# ASSEMBLY HELPERS (App::Part with Bounding Box Support)
# ============================================================


def create_assembly(doc, name, label=None):
    """Create App::Part assembly container (NOT DocumentObjectGroup).

    App::Part provides spatial properties (bounding box) unlike DocumentObjectGroup.

    Args:
        doc: FreeCAD document
        name (str): Internal object name (must be unique)
        label (str): Display label (defaults to name if not provided)

    Returns:
        App::Part object that can hold parts and expose bounding box

    Example:
        assembly = create_assembly(doc, "Joist_Module_16x16")
        assembly.addObject(joist1)
        assembly.addObject(joist2)
        bbox = get_assembly_bbox(assembly)
    """
    assembly = doc.addObject("App::Part", name)
    assembly.Label = label if label else name
    return assembly


def get_assembly_bbox(assembly):
    """Get bounding box of an App::Part assembly.

    Only includes Part::Feature objects (excludes LCS, DocumentObjectGroup, etc.)
    to avoid infinite bounding boxes from coordinate system markers.

    Args:
        assembly: App::Part object

    Returns:
        App.BoundBox with XMin, XMax, YMin, YMax, ZMin, ZMax, XLength, YLength, ZLength

    Example:
        bbox = get_assembly_bbox(assembly)
        width_in = bbox.XLength / 25.4  # Convert mm to inches
        print(f"Assembly: {bbox.XLength} x {bbox.YLength} x {bbox.ZLength} mm")
    """
    bbox = App.BoundBox()

    def add_shapes_recursive(obj):
        """Recursively add shapes from Part::Feature objects only."""
        if hasattr(obj, "Shape") and obj.TypeId == "Part::Feature":
            bbox.add(obj.Shape.BoundBox)
        if hasattr(obj, "Group"):
            for child in obj.Group:
                add_shapes_recursive(child)

    add_shapes_recursive(assembly)
    return bbox


def add_lcs_markers(assembly, corners=None):
    """Add Local Coordinate System markers to assembly corners.

    LCS markers are visual aids for placement but excluded from bounding box.

    Args:
        assembly: App::Part object
        corners (list): Corner names to add markers for
                       Default: ["origin", "bottom_right", "top_left", "top_right"]

    Returns:
        dict: Mapping of corner name to LCS object

    Example:
        lcs_markers = add_lcs_markers(assembly)
        # Now assembly has visible corner markers in FreeCAD tree
    """
    if corners is None:
        corners = ["origin", "bottom_right", "top_left", "top_right"]

    # Get assembly bounding box to place markers
    bbox = get_assembly_bbox(assembly)

    corner_positions = {
        "origin": App.Vector(bbox.XMin, bbox.YMin, bbox.ZMin),
        "bottom_left": App.Vector(bbox.XMin, bbox.YMin, bbox.ZMin),
        "bottom_right": App.Vector(bbox.XMax, bbox.YMin, bbox.ZMin),
        "top_left": App.Vector(bbox.XMin, bbox.YMax, bbox.ZMin),
        "top_right": App.Vector(bbox.XMax, bbox.YMax, bbox.ZMin),
    }

    lcs_objects = {}
    for corner in corners:
        if corner in corner_positions:
            lcs = assembly.newObject("PartDesign::CoordinateSystem", f"LCS_{corner}")
            lcs.Label = f"LCS_{corner}"
            lcs.Placement = App.Placement(corner_positions[corner], App.Rotation())
            lcs_objects[corner] = lcs

    return lcs_objects


def snap_assembly_corner_to_corner(
    assembly,
    target_assembly,
    target_corner="bottom_right",
    assembly_corner="bottom_left",
):
    """Snap assembly's corner to target assembly's corner.

    Human-readable placement logic. NO hard-coded offsets.

    Args:
        assembly: App::Part to be moved
        target_assembly: App::Part to snap to
        target_corner: Which corner of target to snap to
                      ("bottom_left", "bottom_right", "top_left", "top_right")
        assembly_corner: Which corner of assembly to align
                        ("bottom_left", "bottom_right", "top_left", "top_right")

    Example:
        # Place module2's bottom-left corner at module1's bottom-right corner
        snap_assembly_corner_to_corner(module2, module1, "bottom_right", "bottom_left")

        # Result: 0.0000mm gap (perfect alignment)
    """
    # Get bounding boxes
    target_bbox = get_assembly_bbox(target_assembly)
    assembly_bbox_local = get_assembly_bbox(assembly)

    # Apply target assembly's placement to get global coordinates
    target_placement = target_assembly.Placement.Base

    # Get target corner coordinates (in global space)
    corner_map_target = {
        "bottom_left": (
            target_bbox.XMin + target_placement.x,
            target_bbox.YMin + target_placement.y,
            target_bbox.ZMin + target_placement.z,
        ),
        "bottom_right": (
            target_bbox.XMax + target_placement.x,
            target_bbox.YMin + target_placement.y,
            target_bbox.ZMin + target_placement.z,
        ),
        "top_left": (
            target_bbox.XMin + target_placement.x,
            target_bbox.YMax + target_placement.y,
            target_bbox.ZMin + target_placement.z,
        ),
        "top_right": (
            target_bbox.XMax + target_placement.x,
            target_bbox.YMax + target_placement.y,
            target_bbox.ZMin + target_placement.z,
        ),
    }

    target_x, target_y, target_z = corner_map_target[target_corner]

    # Calculate offset from assembly's origin to its corner (in local space)
    corner_offset_map = {
        "bottom_left": (
            assembly_bbox_local.XMin,
            assembly_bbox_local.YMin,
            assembly_bbox_local.ZMin,
        ),
        "bottom_right": (
            assembly_bbox_local.XMax,
            assembly_bbox_local.YMin,
            assembly_bbox_local.ZMin,
        ),
        "top_left": (
            assembly_bbox_local.XMin,
            assembly_bbox_local.YMax,
            assembly_bbox_local.ZMin,
        ),
        "top_right": (
            assembly_bbox_local.XMax,
            assembly_bbox_local.YMax,
            assembly_bbox_local.ZMin,
        ),
    }

    offset_x, offset_y, offset_z = corner_offset_map[assembly_corner]

    # Position assembly so its corner aligns with target corner
    assembly.Placement.Base = App.Vector(
        target_x - offset_x, target_y - offset_y, target_z - offset_z
    )


def place_assembly_at(assembly, x_ft=0, y_ft=0, z_ft=0):
    """Place assembly at absolute position (feet).

    Args:
        assembly: App::Part object
        x_ft, y_ft, z_ft: Position in feet

    Example:
        place_assembly_at(module, x_ft=25.0, y_ft=20.0, z_ft=20.0)
    """
    assembly.Placement.Base = App.Vector(x_ft * 304.8, y_ft * 304.8, z_ft * 304.8)  # feet to mm
