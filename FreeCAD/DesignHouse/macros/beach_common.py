"""BeachHouse common helpers for FreeCAD macros.

This module provides catalog integration and geometry helpers specific to the
BeachHouse project while leveraging shared lumber_common utilities where possible.

Catalog Integration:
    BeachHouse uses a simplified catalog format (sku, url, price_each_usd) while
    the main lumber catalog uses dual-supplier format (sku_lowes, sku_hd, etc.).
    This module normalizes both formats for attach_metadata() compatibility.

Usage:
    from beach_common import load_beach_catalog, find_stock, attach_beach_metadata

    catalog = load_beach_catalog()
    row = find_stock(catalog, "beam_2x12x192_PT")
    attach_beach_metadata(obj, row, "beam_2x12x192_PT")
"""

import csv
import os
import sys

import Part

import FreeCAD as App

# Import shared lumber helpers (lives at DesignHouse/macros)
_macro_dir = os.path.dirname(__file__)
_design_house_dir = os.path.dirname(_macro_dir)
_lumber_dir = os.path.join(_design_house_dir, "lumber")
if _macro_dir not in sys.path:
    sys.path.append(_macro_dir)

try:
    import lumber_common as lc

    LUMBER_COMMON_AVAILABLE = True
except ImportError:
    lc = None
    LUMBER_COMMON_AVAILABLE = False
    App.Console.PrintWarning("[beach_common] lumber_common not available; using fallback helpers\n")


# ============================================================
# Unit Conversion
# ============================================================


def inch(x):
    """Convert inches to millimeters (FreeCAD's native unit)."""
    return x * 25.4


def ft(x):
    """Convert feet to millimeters."""
    return inch(x * 12.0)


# ============================================================
# Catalog Loading (Multi-Source with Override)
# ============================================================


def load_beach_catalog():
    """Load BeachHouse catalog with fallback to shared lumber catalog.

    Strategy:
        1. Load shared lumber catalog (FreeCAD/lumber/lumber_catalog.csv) as base
        2. Load BeachHouse catalog (macros/catalog.csv) and override base entries
        3. Normalize field names for compatibility with lumber_common

    Returns:
        list: Catalog rows as dicts with normalized field names

    Notes:
        BeachHouse catalog uses: sku, url, price_each_usd
        Lumber catalog uses: sku_lowes, url_lowes, sku_hd, url_hd
        This function normalizes both to lumber_common format.
    """
    catalog_paths = [
        # Base: shared lumber catalog (comprehensive, dual-supplier)
        os.path.join(_lumber_dir, "lumber_catalog.csv"),
        # Override: BeachHouse-specific parts (pilings, special items)
        os.path.join(_macro_dir, "catalog.csv"),
    ]

    merged = {}
    for path in catalog_paths:
        if not os.path.isfile(path):
            App.Console.PrintWarning(f"[beach_common] Catalog not found: {path}\n")
            continue

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                label = row.get("label", "").strip()
                if not label:
                    continue

                # Normalize BeachHouse format → lumber_common format
                if "sku" in row and "sku_lowes" not in row:
                    # BeachHouse catalog: map generic fields to lowes fields
                    row["sku_lowes"] = row.get("sku", "")
                    row["url_lowes"] = row.get("url", "")
                    row["sku_hd"] = ""
                    row["url_hd"] = ""

                # Ensure all required fields exist (for lumber_common compatibility)
                for field in ("actual_thickness_in", "actual_width_in", "length_in", "nominal"):
                    if field not in row:
                        row[field] = ""

                # Store normalized row (later entries override earlier)
                merged[label] = row

    # Convert dict back to list for find_stock() compatibility
    return list(merged.values())


# ============================================================
# Catalog Lookup
# ============================================================


def find_stock(catalog_rows, label):
    """Find catalog entry by label.

    Args:
        catalog_rows (list): Catalog rows from load_beach_catalog()
        label (str): Part label (e.g., "beam_2x12x192_PT")

    Returns:
        dict: Catalog row or None if not found

    Raises:
        ValueError: If label not found (fail-fast for missing parts)
    """
    if LUMBER_COMMON_AVAILABLE:
        return lc.find_stock(catalog_rows, label)

    # Fallback implementation
    for row in catalog_rows:
        if row.get("label") == label:
            return row

    raise ValueError(
        f"Part '{label}' not found in BeachHouse catalog.\n"
        f"Check FreeCAD/BeachHouse/macros/catalog.csv or "
        f"FreeCAD/lumber/lumber_catalog.csv.\n"
        f"Available labels: {[r['label'] for r in catalog_rows[:10]]}..."
    )


# ============================================================
# Metadata Attachment (with BeachHouse extensions)
# ============================================================


def attach_beach_metadata(obj, row, label, supplier="lowes", apply_color=True):
    """Attach catalog metadata to FreeCAD object (BeachHouse version).

    Attaches:
        - Supplier info (sku_lowes, url_lowes, sku_hd, url_hd)
        - Part label and supplier
        - Color palette (if apply_color=True)
        - BeachHouse-specific: price_each_usd, price_per_ft_usd (if present)

    Args:
        obj: FreeCAD Part::Feature object
        row (dict): Catalog row from load_beach_catalog()
        label (str): Part label (e.g., "beam_2x12x192_PT")
        supplier (str): Default supplier ("lowes" or "hd")
        apply_color (bool): Apply color palette (default True)

    Notes:
        Uses lumber_common.attach_metadata() if available, otherwise falls back
        to manual property attachment.
    """
    if not row:
        App.Console.PrintWarning(
            f"[beach_common] No catalog row for label '{label}'; skipping metadata\n"
        )
        return

    # Use lumber_common if available (handles color palette, all standard fields)
    if LUMBER_COMMON_AVAILABLE:
        lc.attach_metadata(obj, row, label, supplier=supplier)
    else:
        # Fallback: manual property attachment
        for prop in ("sku_lowes", "url_lowes", "sku_hd", "url_hd", "supplier", "label"):
            if prop not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", prop)
            val = row.get(prop, "")
            if val:
                setattr(obj, prop, val)

        # Apply generic color if lumber_common unavailable
        if apply_color and hasattr(obj, "ViewObject"):
            obj.ViewObject.ShapeColor = (0.8, 0.8, 0.8)  # Default gray

    # Attach BeachHouse-specific pricing (if present in catalog)
    for prop in ("price_each_usd", "price_per_ft_usd"):
        val = row.get(prop, "")
        if val:
            if prop not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", prop)
            setattr(obj, prop, val)


# ============================================================
# Grouping Helpers (Standardized FreeCAD API)
# ============================================================


def create_group(doc, name, label=None):
    """Create FreeCAD DocumentObjectGroup with optional custom label.

    Args:
        doc: FreeCAD document
        name (str): Internal object name (must be unique in document)
        label (str): Display label (defaults to name if not provided)

    Returns:
        DocumentObjectGroup: New group object

    Usage:
        foundation_grp = create_group(doc, "Foundation")
        piles_grp = create_group(doc, "Piles_Subgroup", label="Piles")
    """
    grp = doc.addObject("App::DocumentObjectGroup", name)
    grp.Label = label if label else name
    return grp


def add_to_group(grp, objects):
    """Add objects to FreeCAD group (handles both single object and list).

    Standard pattern:
        1. Call addObject() for each item (FreeCAD tree update)
        2. Set Group property explicitly (compatibility across FreeCAD versions)

    Args:
        grp: DocumentObjectGroup
        objects: Single object or list of objects to add

    Usage:
        add_to_group(foundation_grp, pile_obj)
        add_to_group(foundation_grp, [pile1, pile2, pile3])
    """
    if not isinstance(objects, (list, tuple)):
        objects = [objects]

    for obj in objects:
        grp.addObject(obj)

    # Explicit Group assignment (some FreeCAD builds need this)
    grp.Group = list(grp.Group)  # Convert to list + reassign for compatibility


# ============================================================
# Geometry Helpers (Foundation-Specific)
# ============================================================


def make_pile(doc, catalog, label, name, x_ft, y_ft, base_z_in, height_in):
    """Create pile foundation member with catalog metadata.

    Args:
        doc: FreeCAD document
        catalog (list): Catalog rows
        label (str): Catalog label (e.g., "12x12x40_piling_PT")
        name (str): Object name (e.g., "Pile_25_20")
        x_ft (float): X position in feet (lot coordinates)
        y_ft (float): Y position in feet (lot coordinates)
        base_z_in (float): Z base in inches (negative for embedded)
        height_in (float): Total height in inches (embed + above-grade)

    Returns:
        Part::Feature: Pile object with metadata attached

    Construction Notes:
        - Pile positioned by center (subtract half width from placement)
        - Base at base_z_in (typically negative for embedment)
        - Height extends from base to top (total = embed + above-grade)
    """
    row = find_stock(catalog, label)
    thick_in = float(row["actual_thickness_in"])
    width_in = float(row["actual_width_in"])

    # Create geometry (Z up, pile extends upward from base)
    box = Part.makeBox(inch(width_in), inch(thick_in), inch(height_in))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = box

    # Position: center pile on (x_ft, y_ft), base at base_z_in
    obj.Placement.Base = App.Vector(
        ft(x_ft) - inch(width_in / 2.0), ft(y_ft) - inch(thick_in / 2.0), inch(base_z_in)
    )

    # Attach catalog metadata (includes SKU, URL, color)
    attach_beach_metadata(obj, row, label)

    return obj


def make_beam(doc, catalog, label, name, x_ft, y_start_ft, z_base_in, length_in, orientation="Y"):
    """Create beam with catalog metadata.

    Args:
        doc: FreeCAD document
        catalog (list): Catalog rows
        label (str): Catalog label (e.g., "beam_2x12x192_PT")
        name (str): Object name (e.g., "Beam_East_Row3_L")
        x_ft (float): X position in feet
        y_start_ft (float): Y start position in feet
        z_base_in (float): Z base in inches
        length_in (float): Beam length in inches
        orientation (str): "Y" (runs along Y) or "X" (runs along X)

    Returns:
        Part::Feature: Beam object with metadata

    Construction Notes:
        - Beams typically run perpendicular to joists
        - Placed with bottom at z_base_in, extends along orientation axis
        - For double beams, call twice with x_ft offset ±0.75"
    """
    row = find_stock(catalog, label)
    thick_in = float(row["actual_thickness_in"])
    depth_in = float(row["actual_width_in"])

    if orientation.upper() == "Y":
        # Beam runs along Y: thickness in X, length in Y, depth in Z
        box = Part.makeBox(inch(thick_in), inch(length_in), inch(depth_in))
        placement = App.Vector(ft(x_ft) - inch(thick_in / 2.0), ft(y_start_ft), inch(z_base_in))
    else:
        # Beam runs along X: length in X, thickness in Y, depth in Z
        box = Part.makeBox(inch(length_in), inch(thick_in), inch(depth_in))
        placement = App.Vector(ft(x_ft), ft(y_start_ft) - inch(thick_in / 2.0), inch(z_base_in))

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = box
    obj.Placement.Base = placement

    attach_beach_metadata(obj, row, label)

    return obj


# ============================================================
# Utility Functions
# ============================================================


def clear_existing_groups(doc, group_names):
    """Remove existing groups (for re-running macros cleanly).

    Args:
        doc: FreeCAD document
        group_names (list): List of group names to remove

    Notes:
        Removes groups and all their children. Use carefully!
    """
    for name in group_names:
        obj = doc.getObject(name)
        if obj:
            # Remove all children first
            if hasattr(obj, "Group"):
                for child in list(obj.Group):
                    doc.removeObject(child.Name)
            # Remove group itself
            doc.removeObject(obj.Name)


def recompute_once(doc):
    """Single recompute at end of macro (performance optimization).

    Args:
        doc: FreeCAD document

    Notes:
        Calling doc.recompute() after every object creation is slow.
        Create all geometry, then recompute once at end.
    """
    doc.recompute()


# ============================================================
# Diagnostic Helpers
# ============================================================


def print_catalog_summary(catalog):
    """Print catalog summary to FreeCAD console (debugging aid).

    Args:
        catalog (list): Catalog rows

    Output:
        Prints label, nominal, length_in for first 10 entries
    """
    App.Console.PrintMessage(f"[beach_common] Loaded {len(catalog)} catalog entries:\n")
    for row in catalog[:10]:
        label = row.get("label", "?")
        nominal = row.get("nominal", "?")
        length_in = row.get("length_in", "?")
        App.Console.PrintMessage(f"  - {label:30s} {nominal:15s} {length_in} in\n")
    if len(catalog) > 10:
        App.Console.PrintMessage(f"  ... and {len(catalog) - 10} more entries\n")


# ============================================================
# Module Test (run as standalone for verification)
# ============================================================

if __name__ == "__main__":
    print("Testing beach_common module...")

    # Test catalog loading
    catalog = load_beach_catalog()
    print(f"Loaded {len(catalog)} catalog entries")

    # Test stock lookup
    try:
        row = find_stock(catalog, "beam_2x12x192_PT")
        print(f"Found beam: {row['nominal']} @ {row['length_in']} inches")
    except ValueError as e:
        print(f"Lookup failed: {e}")

    # Test unit conversion
    assert abs(inch(12.0) - 304.8) < 0.1, "inch() conversion failed"
    assert abs(ft(1.0) - 304.8) < 0.1, "ft() conversion failed"

    print("beach_common module tests passed!")
