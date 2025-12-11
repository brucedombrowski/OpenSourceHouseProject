# Shared helpers for FreeCAD lumber macros

import csv
import os
import sys

import Part

import FreeCAD as App


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
    for key in ("sku_lowes", "url_lowes", "sku_hd", "url_hd"):
        if key not in obj.PropertiesList:
            obj.addProperty("App::PropertyString", key)
        obj.__setattr__(key, row.get(key, ""))
    obj.addProperty("App::PropertyString", "supplier").supplier = supplier
    obj.addProperty("App::PropertyString", "label").label = label


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
):
    # Build a simple U with seat + side flanges + back plate.
    bw = thick + 2 * hanger_thickness  # overall width across joist + flanges
    bh = hanger_height
    bd = hanger_seat_depth
    bt = hanger_thickness
    z0 = -bt  # drop seat below joist bottom

    # Back plate (thin)
    back = Part.makeBox(inch(bt), inch(bw), inch(bh))
    back.Placement.Base = App.Vector(inch(x_pos - bt), inch(y_center - bw / 2.0), inch(z0))

    # Seat (spans joist width only)
    seat = Part.makeBox(inch(bd), inch(thick), inch(bt))
    seat.Placement.Base = App.Vector(inch(x_pos - bd), inch(y_center - thick / 2.0), inch(z0))

    # Side flanges
    sideL = Part.makeBox(inch(bd), inch(bt), inch(bh))
    sideL.Placement.Base = App.Vector(inch(x_pos - bd), inch(y_center - thick / 2.0 - bt), inch(z0))

    sideR = Part.makeBox(inch(bd), inch(bt), inch(bh))
    sideR.Placement.Base = App.Vector(inch(x_pos - bd), inch(y_center + thick / 2.0), inch(z0))

    u_shape = back.fuse([seat, sideL, sideR])
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = u_shape
    obj.addProperty("App::PropertyString", "supplier").supplier = "lowes"
    obj.addProperty("App::PropertyString", "label").label = hanger_label
    return obj
