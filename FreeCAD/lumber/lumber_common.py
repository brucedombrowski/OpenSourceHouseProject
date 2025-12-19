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
        tx = inch(x_pos + (bt if direction > 0 else -bt))  # shift along world X
        ty = inch(y_center - (thick / 2.0))  # center on joist thickness
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
