# Shared helpers for FreeCAD lumber macros

import csv
import os
import sys

import Part

import FreeCAD as App

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
    with open(path, newline="") as f:
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
    debug_components=False,
    color=None,
):
    """
    Build a simple U-shape hanger (back plate + seat + two side flanges + front lip).

    x_pos is the face of the rim the hanger mounts to.
    direction=+1: hanger extends into +X (left rim interior).
    direction=-1: hanger extends into -X (right rim interior).

    When debug_components is True, return a colored group of sub-parts instead of a fused solid.
    """
    bh = hanger_height
    bd = hanger_seat_depth
    bt = hanger_thickness
    z0 = -bt  # drop seat below joist bottom
    direction = 1 if direction >= 0 else -1

    # Position solids so they always extend into the module interior.
    if direction > 0:
        back_base_x = x_pos - bt  # back plate sits on rim face
        seat_base_x = back_base_x + bt  # seat starts just inside the back
        front_base_x = back_base_x  # lip sits in same X plane as back
    else:
        back_base_x = x_pos  # back plate sits on rim face
        seat_base_x = back_base_x - bd  # seat extends toward negative X
        front_base_x = back_base_x - bt  # lip sits in same X plane as back

    # Back plate (treat as left flange in debug): same size as front lip; align its right edge to the green flange (-Y face)
    back = Part.makeBox(inch(bt), inch(thick), inch(bh))
    back.Placement.Base = App.Vector(
        inch(back_base_x), inch(y_center - thick / 2.0 - thick), inch(z0)
    )

    # Seat (spans joist width only)
    seat = Part.makeBox(inch(bd), inch(thick), inch(bt))
    seat.Placement.Base = App.Vector(inch(seat_base_x), inch(y_center - thick / 2.0), inch(z0))

    # Side flanges (tall plates)
    sideL = Part.makeBox(inch(bd), inch(bt), inch(bh))
    sideL.Placement.Base = App.Vector(
        inch(seat_base_x), inch(y_center - thick / 2.0 - bt), inch(z0)
    )

    sideR = Part.makeBox(inch(bd), inch(bt), inch(bh))
    sideR.Placement.Base = App.Vector(inch(seat_base_x), inch(y_center + thick / 2.0), inch(z0))

    # Front lip (treat as right flange in debug): same size as back, at +Y side
    front = Part.makeBox(inch(bt), inch(thick), inch(bh))
    front.Placement.Base = App.Vector(inch(front_base_x), inch(y_center + thick / 2.0), inch(z0))

    if debug_components:
        # Build individual colored parts and group them for visual debugging.
        colors = {
            "back": (0.8, 0.2, 0.2),
            "seat": (0.2, 0.6, 0.9),
            "sideL": (0.2, 0.8, 0.4),
            "sideR": (0.9, 0.7, 0.2),
            "front": (0.6, 0.4, 0.9),
        }
        if color:
            for k in colors:
                colors[k] = color
        pieces = [
            ("back", back),
            ("seat", seat),
            ("sideL", sideL),
            ("sideR", sideR),
            ("front", front),
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
        u_shape = back.fuse([seat, sideL, sideR, front])
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = u_shape
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
