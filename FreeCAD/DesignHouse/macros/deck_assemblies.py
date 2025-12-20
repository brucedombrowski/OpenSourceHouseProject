"""
Deck assembly creation functions for FreeCAD.
Returns App::Part assemblies that can be positioned in larger builds.

Construction sequence:
1. create_deck_joists_16x8() - Joists, rims, hangers (installed before sheathing)
2. create_deck_surface_16x8() - Deck boards, posts (installed after walls)
"""

import os

import Part

import FreeCAD as App

try:
    import lumber_common as lc
except ImportError:
    import sys

    _here = os.path.dirname(__file__)
    if _here not in sys.path:
        sys.path.append(_here)
    import lumber_common as lc


def create_deck_joists_16x8(
    doc,
    catalog_rows,
    assembly_name="Deck_Joists_16x8",
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    supplier="lowes",
):
    """
    Create a 16' x 8' deck joist framing assembly (joists, rims, hangers only).
    This is installed BEFORE sheathing so workers can walk on it.

    Design:
        - 16' x 8' footprint (X=16', Y=8')
        - House side rim at Y=0, joists project +Y (8')
        - 2x12 joists @ 16" OC with rim/end boards
        - Joist hangers on house rim and outboard rim

    Args:
        doc: FreeCAD document
        catalog_rows: Catalog data (list of dicts)
        assembly_name: Name for the assembly
        x_base, y_base, z_base: Position offsets (inches)
        supplier: Supplier preference ("lowes" or "hd")

    Returns:
        App::Part assembly containing joists, rims, and hangers
    """
    # Parameters
    length_x_in = 192.0  # 16'
    proj_y_in = 96.0  # 8'
    joist_spacing_oc_in = 16.0
    rim_label = "2x12x192"
    joist_label = "2x12x96"
    hanger_label = "hanger_LU210"
    hanger_thickness = 0.06
    hanger_height = 7.8125
    hanger_seat_depth = 2.0

    # Find stock
    rim_row = lc.find_stock(catalog_rows, rim_label)
    joist_row = lc.find_stock(catalog_rows, joist_label)

    if not rim_row or not joist_row:
        raise ValueError("Required rim/joist stock not found in catalog.")

    # Dimensions
    rim_thick = float(rim_row["actual_thickness_in"])
    rim_depth = float(rim_row["actual_width_in"])
    rim_len = float(rim_row["length_in"])
    joist_thick = float(joist_row["actual_thickness_in"])
    joist_depth = float(joist_row["actual_width_in"])
    joist_len = float(joist_row["length_in"])

    created = []

    def make_rim(name, y_local):
        box = Part.makeBox(lc.inch(rim_len), lc.inch(rim_thick), lc.inch(rim_depth))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(0, lc.inch(y_local), 0)
        lc.attach_metadata(obj, rim_row, rim_label, supplier=supplier)
        return obj

    def make_joist(name, x_local):
        box = Part.makeBox(lc.inch(joist_thick), lc.inch(proj_y_in), lc.inch(joist_depth))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(lc.inch(x_local), 0, 0)
        lc.attach_metadata(obj, joist_row, joist_label, supplier=supplier)
        return obj

    # Rims
    rim_offset = joist_thick
    created.append(make_rim("Rim_House", -rim_offset))
    created.append(make_rim("Rim_Outboard", proj_y_in))

    # Joists @ 16" OC along X
    centers = []
    first_center = joist_thick / 2.0
    last_center = length_x_in - (joist_thick / 2.0)
    c = first_center
    while c < last_center - 1e-6:
        centers.append(c)
        c += joist_spacing_oc_in
    if not centers or centers[-1] < last_center - 1e-6:
        centers.append(last_center)

    for idx, cx in enumerate(centers, start=1):
        x_pos = cx - (joist_thick / 2.0)
        created.append(make_joist(f"Joist_{idx}", x_pos))

    # Hangers on house rim for each joist (skip first/last)
    hangs = []
    house_face_y = 0.0
    outboard_face_y = proj_y_in

    for idx, cx in enumerate(centers, start=1):
        if idx == 1 or idx == len(centers):
            continue  # skip end joists
        try:
            # House rim hanger: extends into +Y
            hangs.append(
                lc.make_hanger(
                    doc,
                    f"Hanger_House_{idx}",
                    house_face_y,
                    cx,
                    joist_thick,
                    hanger_thickness,
                    hanger_height,
                    hanger_seat_depth,
                    hanger_label,
                    direction=1,
                    axis="Y",
                    debug_components=False,
                    color=(0.6, 0.6, 0.7),
                )
            )
            # Outboard rim hanger: extends into -Y
            hangs.append(
                lc.make_hanger(
                    doc,
                    f"Hanger_Outboard_{idx}",
                    outboard_face_y,
                    cx + joist_thick,
                    joist_thick,
                    hanger_thickness,
                    hanger_height,
                    hanger_seat_depth,
                    hanger_label,
                    direction=-1,
                    axis="Y",
                    debug_components=False,
                    color=(0.6, 0.6, 0.7),
                )
            )
        except Exception as e:
            App.Console.PrintError(f"[deck_assemblies] Hanger build failed for joist {idx}: {e}\n")

    created.extend(hangs)

    # Create assembly (App::Part)
    App.Console.PrintMessage(
        f"[deck_assemblies] Created assembly: {assembly_name} (type: App::Part)\n"
    )
    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    # Add all parts to assembly
    App.Console.PrintMessage(f"[deck_assemblies] Adding {len(created)} parts to assembly...\n")
    for obj in created:
        assembly.addObject(obj)

    # Apply global position offset
    assembly.Placement.Base = App.Vector(lc.inch(x_base), lc.inch(y_base), lc.inch(z_base))

    doc.recompute()

    App.Console.PrintMessage(
        f"[deck_assemblies] ✓ Assembly complete: {assembly_name} "
        f"({len(centers)} joists, 2 rims, {len(hangs)} hangers)\n"
    )

    return assembly


def create_deck_joists_8x8(
    doc,
    catalog_rows,
    assembly_name="Deck_Joists_8x8",
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    supplier="lowes",
):
    """
    Create an 8' x 8' deck joist framing assembly (joists, rims, hangers only).
    This is installed BEFORE sheathing so workers can walk on it.

    Design:
        - 8' x 8' footprint (X=8', Y=8')
        - House side rim at Y=0, joists project +Y (8')
        - 2x12 joists @ 16" OC with rim/end boards
        - Joist hangers on house rim and outboard rim

    Args:
        doc: FreeCAD document
        catalog_rows: Catalog data (list of dicts)
        assembly_name: Name for the assembly
        x_base, y_base, z_base: Position offsets (inches)
        supplier: Supplier preference ("lowes" or "hd")

    Returns:
        App::Part assembly containing joists, rims, and hangers
    """
    # Parameters
    length_x_in = 96.0  # 8' (not 16')
    proj_y_in = 96.0  # 8'
    joist_spacing_oc_in = 16.0
    rim_label = "2x12x96"  # 8' rim (not 16')
    joist_label = "2x12x96"
    hanger_label = "hanger_LU210"
    hanger_thickness = 0.06
    hanger_height = 7.8125
    hanger_seat_depth = 2.0

    # Find stock
    rim_row = lc.find_stock(catalog_rows, rim_label)
    joist_row = lc.find_stock(catalog_rows, joist_label)

    if not rim_row or not joist_row:
        raise ValueError("Required rim/joist stock not found in catalog.")

    # Dimensions
    rim_thick = float(rim_row["actual_thickness_in"])
    rim_depth = float(rim_row["actual_width_in"])
    rim_len = float(rim_row["length_in"])
    joist_thick = float(joist_row["actual_thickness_in"])
    joist_depth = float(joist_row["actual_width_in"])
    joist_len = float(joist_row["length_in"])

    created = []

    def make_rim(name, y_local):
        box = Part.makeBox(lc.inch(rim_len), lc.inch(rim_thick), lc.inch(rim_depth))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(0, lc.inch(y_local), 0)
        lc.attach_metadata(obj, rim_row, rim_label, supplier=supplier)
        return obj

    def make_joist(name, x_local):
        box = Part.makeBox(lc.inch(joist_thick), lc.inch(proj_y_in), lc.inch(joist_depth))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(lc.inch(x_local), 0, 0)
        lc.attach_metadata(obj, joist_row, joist_label, supplier=supplier)
        return obj

    # Rims
    rim_offset = joist_thick
    created.append(make_rim("Rim_House", -rim_offset))
    created.append(make_rim("Rim_Outboard", proj_y_in))


def create_deck_joists_8ft9in_x_8ft(
    doc,
    catalog_rows,
    assembly_name="Deck_Joists_8ft9in_x_8ft",
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    supplier="lowes",
):
    """
    Create an 8'9" x 8' deck joist framing assembly (joists, rims, hangers only).
    This is installed BEFORE sheathing so workers can walk on it.

    Design:
        - 8'9" wide (X=105") x 8' deep (Y=96")
        - House side rim (Rim_House) and outboard rim (Rim_Outboard) are 105" long (cut from 10' boards)
        - End joists (Rim_Left/Rim_Right) are 96" long (8' joists running in Y direction)
        - 2x12 joists @ 16" OC with rim/end boards
        - Joist hangers on house rim and outboard rim

    Args:
        doc: FreeCAD document
        catalog_rows: Catalog data (list of dicts)
        assembly_name: Name for the assembly
        x_base, y_base, z_base: Position offsets (inches)
        supplier: Supplier preference ("lowes" or "hd")

    Returns:
        App::Part assembly containing joists, rims, and hangers
    """
    # Parameters
    length_x_in = 105.0  # 8'9" wide
    proj_y_in = 96.0  # 8' deep
    joist_spacing_oc_in = 16.0
    rim_house_outboard_label = "2x12x120"  # 10' boards for house/outboard rims (cut to 105")
    joist_label = "2x12x96"  # 8' joists
    hanger_label = "hanger_LU210"
    hanger_thickness = 0.06
    hanger_height = 7.8125
    hanger_seat_depth = 2.0

    # Find stock
    rim_row = lc.find_stock(catalog_rows, rim_house_outboard_label)
    joist_row = lc.find_stock(catalog_rows, joist_label)

    if not rim_row or not joist_row:
        raise ValueError("Required rim/joist stock not found in catalog.")

    # Dimensions
    rim_thick = float(rim_row["actual_thickness_in"])
    rim_depth = float(rim_row["actual_width_in"])
    joist_thick = float(joist_row["actual_thickness_in"])
    joist_depth = float(joist_row["actual_width_in"])
    joist_len = float(joist_row["length_in"])

    created = []

    def make_rim_house_outboard(name, y_local):
        """Make Rim_House or Rim_Outboard (105\" long, cut from 10' boards)"""
        box = Part.makeBox(lc.inch(length_x_in), lc.inch(rim_thick), lc.inch(rim_depth))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(0, lc.inch(y_local), 0)
        lc.attach_metadata(obj, rim_row, rim_house_outboard_label, supplier=supplier)
        try:
            if "cut_length_in" not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", "cut_length_in")
            obj.cut_length_in = f"{length_x_in}"
        except Exception:
            pass
        return obj

    def make_joist(name, x_local):
        """Make a joist (96\" long, running in Y direction)"""
        box = Part.makeBox(lc.inch(joist_thick), lc.inch(proj_y_in), lc.inch(joist_depth))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(lc.inch(x_local), 0, 0)
        lc.attach_metadata(obj, joist_row, joist_label, supplier=supplier)
        return obj

    # Rims: House and Outboard are 105" long
    rim_offset = joist_thick
    created.append(make_rim_house_outboard("Rim_House", -rim_offset))
    created.append(make_rim_house_outboard("Rim_Outboard", proj_y_in))

    # Joists @ 16" OC along X
    centers = []
    first_center = joist_thick / 2.0
    last_center = length_x_in - (joist_thick / 2.0)
    c = first_center
    while c < last_center - 1e-6:
        centers.append(c)
        c += joist_spacing_oc_in
    if not centers or centers[-1] < last_center - 1e-6:
        centers.append(last_center)

    for idx, cx in enumerate(centers, start=1):
        x_pos = cx - (joist_thick / 2.0)
        created.append(make_joist(f"Joist_{idx}", x_pos))

    # Hangers on house rim for each joist (skip first/last)
    hangs = []
    house_face_y = 0.0
    outboard_face_y = proj_y_in

    for idx, cx in enumerate(centers, start=1):
        if idx == 1 or idx == len(centers):
            continue  # skip end joists
        try:
            # House rim hanger: extends into +Y
            hangs.append(
                lc.make_hanger(
                    doc,
                    f"Hanger_House_{idx}",
                    house_face_y,
                    cx,
                    joist_thick,
                    hanger_thickness,
                    hanger_height,
                    hanger_seat_depth,
                    hanger_label,
                    direction=1,
                    axis="Y",
                    debug_components=False,
                    color=(0.6, 0.6, 0.7),
                )
            )
            # Outboard rim hanger: extends into -Y
            hangs.append(
                lc.make_hanger(
                    doc,
                    f"Hanger_Outboard_{idx}",
                    outboard_face_y,
                    cx + joist_thick,
                    joist_thick,
                    hanger_thickness,
                    hanger_height,
                    hanger_seat_depth,
                    hanger_label,
                    direction=-1,
                    axis="Y",
                    debug_components=False,
                    color=(0.6, 0.6, 0.7),
                )
            )
        except Exception as e:
            App.Console.PrintError(f"[deck_assemblies] Hanger build failed for joist {idx}: {e}\n")

    created.extend(hangs)

    # Create assembly (App::Part)
    App.Console.PrintMessage(
        f"[deck_assemblies] Created assembly: {assembly_name} (type: App::Part)\n"
    )
    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    # Add all parts to assembly
    App.Console.PrintMessage(f"[deck_assemblies] Adding {len(created)} parts to assembly...\n")
    for obj in created:
        assembly.addObject(obj)

    # Apply global position offset
    assembly.Placement.Base = App.Vector(lc.inch(x_base), lc.inch(y_base), lc.inch(z_base))

    doc.recompute()

    App.Console.PrintMessage(
        f"[deck_assemblies] ✓ Assembly complete: {assembly_name} "
        f"({len(centers)} joists, 2 rims, {len(hangs)} hangers)\n"
    )

    return assembly


def create_deck_surface_16x8(
    doc,
    catalog_rows,
    assembly_name="Deck_Surface_16x8",
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    supplier="lowes",
    include_left_edge=True,
    include_right_edge=True,
):
    """
    Create a 16' x 8' deck surface assembly (boards and posts only).
    This is installed AFTER walls are up.

    Design:
        - 16' x 8' footprint (X=16', Y=8')
        - 5/4x6x16' pressure-treated deck boards (1/8" gaps)
        - Six 6x6 posts (4 corners + 2 intermediate along outboard edge)
        - Posts are cut to height and boards are notched for post penetrations

    Args:
        doc: FreeCAD document
        catalog_rows: Catalog data (list of dicts)
        assembly_name: Name for the assembly
        x_base, y_base, z_base: Position offsets (inches)
        supplier: Supplier preference ("lowes" or "hd")

    Returns:
        App::Part assembly containing deck boards and posts
    """
    # Parameters
    length_x_in = 192.0  # 16'
    proj_y_in = 96.0  # 8'
    deck_label = "deckboard_5_4x6x192_PT"
    post_label = "post_6x6x144_PT"
    joist_depth = 11.25  # 2x12 depth (for post height calculation)

    # Find stock
    deck_row = lc.find_stock(catalog_rows, deck_label)
    post_row = lc.find_stock(catalog_rows, post_label)

    if not deck_row:
        raise ValueError(f"Deck board label '{deck_label}' not found in catalog.")
    if not post_row:
        raise ValueError(f"Post label '{post_label}' not found in catalog.")

    # Dimensions
    deck_thick = float(deck_row["actual_thickness_in"])
    deck_width = float(deck_row["actual_width_in"])
    deck_len = float(deck_row["length_in"])
    deck_gap = 0.125  # 1/8" gap
    post_thick = float(post_row["actual_thickness_in"])
    post_width = float(post_row["actual_width_in"])
    post_height_in = joist_depth  # flush to deck board underside

    created = []

    # Calculate board length and X offset based on edge boards
    board_x_start = deck_width if include_left_edge else 0.0
    board_length = length_x_in
    if include_left_edge:
        board_length -= deck_width
    if include_right_edge:
        board_length -= deck_width

    def make_deck_board(name, y_local):
        box = Part.makeBox(lc.inch(board_length), lc.inch(deck_width), lc.inch(deck_thick))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            lc.inch(board_x_start), lc.inch(y_local), lc.inch(joist_depth)
        )
        lc.attach_metadata(obj, deck_row, deck_label, supplier=supplier)
        return obj

    def make_post(name, x_local, y_local, z_local):
        box = Part.makeBox(lc.inch(post_width), lc.inch(post_thick), lc.inch(post_height_in))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(lc.inch(x_local), lc.inch(y_local), lc.inch(z_local))
        lc.attach_metadata(obj, post_row, post_label, supplier=supplier)
        try:
            if "cut_length_in" not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", "cut_length_in")
            obj.cut_length_in = f"{post_height_in}"
        except Exception:
            pass
        return obj

    # Deck boards running along X, 1/8" gaps
    boards = []
    board_count = 0
    step = deck_width + deck_gap
    y_pos = -1.5  # shift first board toward house by 1.5"
    last_full_end = None

    while True:
        next_y = y_pos + deck_width
        if next_y > proj_y_in:
            # Rip last board to remaining space
            rip_start = (last_full_end if last_full_end is not None else y_pos) + deck_gap
            remaining = proj_y_in - rip_start + 1.5  # widen rip by 1.5"
            if remaining > 0.25:
                board_count += 1
                rip = make_deck_board(f"Deck_{board_count}_RIP", rip_start)
                rip.Shape = Part.makeBox(
                    lc.inch(board_length), lc.inch(remaining), lc.inch(deck_thick)
                )
                rip.Placement.Base.x = lc.inch(board_x_start)
                rip.Placement.Base.y = lc.inch(rip_start)
                rip.Placement.Base.z = lc.inch(joist_depth)
                boards.append(rip)
            break
        board_count += 1
        boards.append(make_deck_board(f"Deck_{board_count}", y_pos))
        last_full_end = next_y
        y_pos += step

    created.extend(boards)

    # Edge boards (picture frame): perpendicular boards at left and right edges
    # These run along Y direction to square out the deck
    # Only include edge boards on the outermost edges of the full deck assembly
    edge_boards = []

    if include_left_edge:
        # Left edge board (at X=0, runs from Y=-1.5 to Y=proj_y_in+1.5)
        left_edge = doc.addObject("Part::Feature", "Edge_Left")
        left_edge.Shape = Part.makeBox(
            lc.inch(deck_width),  # 5.5" wide
            lc.inch(proj_y_in + 3.0),  # Extends from -1.5 to +97.5 (9.5' total)
            lc.inch(deck_thick),
        )
        left_edge.Placement.Base = App.Vector(0, lc.inch(-1.5), lc.inch(joist_depth))
        lc.attach_metadata(left_edge, deck_row, deck_label, supplier=supplier)
        edge_boards.append(left_edge)

    if include_right_edge:
        # Right edge board (at X=length_x_in - deck_width, runs from Y=-1.5 to Y=proj_y_in+1.5)
        right_edge = doc.addObject("Part::Feature", "Edge_Right")
        right_edge.Shape = Part.makeBox(
            lc.inch(deck_width),  # 5.5" wide
            lc.inch(proj_y_in + 3.0),  # Extends from -1.5 to +97.5 (9.5' total)
            lc.inch(deck_thick),
        )
        right_edge.Placement.Base = App.Vector(
            lc.inch(length_x_in - deck_width), lc.inch(-1.5), lc.inch(joist_depth)
        )
        lc.attach_metadata(right_edge, deck_row, deck_label, supplier=supplier)
        edge_boards.append(right_edge)

    created.extend(edge_boards)

    # Posts removed - will be added later as a separate assembly

    # Create assembly (App::Part)
    App.Console.PrintMessage(
        f"[deck_assemblies] Created assembly: {assembly_name} (type: App::Part)\n"
    )
    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    # Add all parts to assembly
    App.Console.PrintMessage(f"[deck_assemblies] Adding {len(created)} parts to assembly...\n")
    for obj in created:
        assembly.addObject(obj)

    # Apply global position offset
    assembly.Placement.Base = App.Vector(lc.inch(x_base), lc.inch(y_base), lc.inch(z_base))

    doc.recompute()

    App.Console.PrintMessage(
        f"[deck_assemblies] ✓ Assembly complete: {assembly_name} "
        f"({len(boards)} deck boards, {len(edge_boards)} edge boards)\n"
    )

    return assembly


def create_deck_surface_8ft9in_x_8ft(
    doc,
    catalog_rows,
    assembly_name="Deck_Surface_8ft9in_x_8ft",
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    supplier="lowes",
    include_left_edge=False,
    include_right_edge=False,
):
    """
    Create an 8'9" x 8' deck surface assembly (boards only, no posts).
    This is installed AFTER walls are up.

    Design:
        - 8'9" wide (X=105") x 8' deep (Y=96")
        - 5/4x6x16' pressure-treated deck boards running X direction (cut to 105")
        - 5/4x6x16' edge boards running Y direction for picture frame (cut to fit)
        - Posts removed (will be added separately later)

    Args:
        doc: FreeCAD document
        catalog_rows: Catalog data (list of dicts)
        assembly_name: Name for the assembly
        x_base, y_base, z_base: Position offsets (inches)
        supplier: Supplier preference ("lowes" or "hd")

    Returns:
        App::Part assembly containing deck boards and posts
    """
    # Parameters
    length_x_in = 105.0  # 8'9" wide
    proj_y_in = 96.0  # 8' deep
    deck_label_main = "deckboard_5_4x6x192_PT"  # 16' boards for main deck boards (cut to 105")
    deck_label_edge = "deckboard_5_4x6x192_PT"  # 16' boards for edge boards (cut to fit)
    post_label = "post_6x6x144_PT"
    joist_depth = 11.25  # 2x12 depth (for post height calculation)

    # Find stock
    deck_row_main = lc.find_stock(catalog_rows, deck_label_main)
    deck_row_edge = lc.find_stock(catalog_rows, deck_label_edge)
    post_row = lc.find_stock(catalog_rows, post_label)

    if not deck_row_main:
        raise ValueError(f"Deck board label '{deck_label_main}' not found in catalog.")
    if not deck_row_edge:
        raise ValueError(f"Edge deck board label '{deck_label_edge}' not found in catalog.")
    if not post_row:
        raise ValueError(f"Post label '{post_label}' not found in catalog.")

    # Dimensions
    deck_thick = float(deck_row_main["actual_thickness_in"])
    deck_width = float(deck_row_main["actual_width_in"])
    deck_gap = 0.125  # 1/8" gap
    post_thick = float(post_row["actual_thickness_in"])
    post_width = float(post_row["actual_width_in"])
    post_height_in = joist_depth  # flush to deck board underside

    created = []

    # Calculate board length and X offset based on edge boards
    board_x_start = deck_width if include_left_edge else 0.0
    board_length = length_x_in
    if include_left_edge:
        board_length -= deck_width
    if include_right_edge:
        board_length -= deck_width

    def make_deck_board_main(name, y_local):
        """Main deck boards running along X (trimmed to fit between edge boards)"""
        box = Part.makeBox(lc.inch(board_length), lc.inch(deck_width), lc.inch(deck_thick))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(
            lc.inch(board_x_start), lc.inch(y_local), lc.inch(joist_depth)
        )
        lc.attach_metadata(obj, deck_row_main, deck_label_main, supplier=supplier)
        try:
            if "cut_length_in" not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", "cut_length_in")
            obj.cut_length_in = f"{board_length}"
        except Exception:
            pass
        return obj

    def make_post(name, x_local, y_local, z_local):
        box = Part.makeBox(lc.inch(post_width), lc.inch(post_thick), lc.inch(post_height_in))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(lc.inch(x_local), lc.inch(y_local), lc.inch(z_local))
        lc.attach_metadata(obj, post_row, post_label, supplier=supplier)
        try:
            if "cut_length_in" not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", "cut_length_in")
            obj.cut_length_in = f"{post_height_in}"
        except Exception:
            pass
        return obj

    # Deck boards running along X, 1/8" gaps
    boards = []
    board_count = 0
    step = deck_width + deck_gap
    y_pos = -1.5  # shift first board toward house by 1.5"
    last_full_end = None

    while True:
        next_y = y_pos + deck_width
        if next_y > proj_y_in:
            # Rip last board to remaining space
            rip_start = (last_full_end if last_full_end is not None else y_pos) + deck_gap
            remaining = proj_y_in - rip_start + 1.5  # widen rip by 1.5"
            if remaining > 0.25:
                board_count += 1
                rip = make_deck_board_main(f"Deck_{board_count}_RIP", rip_start)
                rip.Shape = Part.makeBox(
                    lc.inch(board_length), lc.inch(remaining), lc.inch(deck_thick)
                )
                rip.Placement.Base.x = lc.inch(board_x_start)
                rip.Placement.Base.y = lc.inch(rip_start)
                rip.Placement.Base.z = lc.inch(joist_depth)
                boards.append(rip)
            break
        board_count += 1
        boards.append(make_deck_board_main(f"Deck_{board_count}", y_pos))
        last_full_end = next_y
        y_pos += step

    created.extend(boards)

    # Edge boards (picture frame): perpendicular boards at left and right edges
    # These run along Y direction to square out the deck
    # Only include edge boards on the outermost edges of the full deck assembly
    edge_boards = []

    if include_left_edge:
        # Left edge board (at X=0, runs from Y=-1.5 to Y=proj_y_in+1.5)
        left_edge = doc.addObject("Part::Feature", "Edge_Left")
        left_edge.Shape = Part.makeBox(
            lc.inch(deck_width),  # 5.5" wide
            lc.inch(proj_y_in + 3.0),  # Extends from -1.5 to +97.5 (9.5' total, cut from 16')
            lc.inch(deck_thick),
        )
        left_edge.Placement.Base = App.Vector(0, lc.inch(-1.5), lc.inch(joist_depth))
        lc.attach_metadata(left_edge, deck_row_edge, deck_label_edge, supplier=supplier)
        try:
            if "cut_length_in" not in left_edge.PropertiesList:
                left_edge.addProperty("App::PropertyString", "cut_length_in")
            left_edge.cut_length_in = f"{proj_y_in + 3.0}"
        except Exception:
            pass
        edge_boards.append(left_edge)

    if include_right_edge:
        # Right edge board (at X=length_x_in - deck_width, runs from Y=-1.5 to Y=proj_y_in+1.5)
        right_edge = doc.addObject("Part::Feature", "Edge_Right")
        right_edge.Shape = Part.makeBox(
            lc.inch(deck_width),  # 5.5" wide
            lc.inch(proj_y_in + 3.0),  # Extends from -1.5 to +97.5 (9.5' total, cut from 16')
            lc.inch(deck_thick),
        )
        right_edge.Placement.Base = App.Vector(
            lc.inch(length_x_in - deck_width), lc.inch(-1.5), lc.inch(joist_depth)
        )
        lc.attach_metadata(right_edge, deck_row_edge, deck_label_edge, supplier=supplier)
        try:
            if "cut_length_in" not in right_edge.PropertiesList:
                right_edge.addProperty("App::PropertyString", "cut_length_in")
            right_edge.cut_length_in = f"{proj_y_in + 3.0}"
        except Exception:
            pass
        edge_boards.append(right_edge)

    created.extend(edge_boards)

    # Posts removed - will be added later as a separate assembly

    # Create assembly (App::Part)
    App.Console.PrintMessage(
        f"[deck_assemblies] Created assembly: {assembly_name} (type: App::Part)\n"
    )
    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    # Add all parts to assembly
    App.Console.PrintMessage(f"[deck_assemblies] Adding {len(created)} parts to assembly...\n")
    for obj in created:
        assembly.addObject(obj)

    # Apply global position offset
    assembly.Placement.Base = App.Vector(lc.inch(x_base), lc.inch(y_base), lc.inch(z_base))

    doc.recompute()

    App.Console.PrintMessage(
        f"[deck_assemblies] ✓ Assembly complete: {assembly_name} "
        f"({len(boards)} deck boards, {len(edge_boards)} edge boards)\n"
    )

    return assembly


def create_deck_16x8(
    doc,
    catalog_rows,
    assembly_name="Deck_16x8",
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    supplier="lowes",
):
    """
    Create a 16' x 8' deck module as an App::Part assembly.

    Design:
        - 16' x 8' footprint (X=16', Y=8')
        - House side rim at Y=0, joists project +Y (8')
        - 2x12 joists @ 16" OC with rim/end boards
        - 5/4x6x16' pressure-treated deck boards (1/8" gaps)
        - Six 6x6 posts (4 corners + 2 intermediate along outboard rim)
        - Joist hangers on house rim and outboard rim

    Args:
        doc: FreeCAD document
        catalog_rows: Catalog data (list of dicts)
        assembly_name: Name for the assembly
        x_base, y_base, z_base: Position offsets (inches)
        supplier: Supplier preference ("lowes" or "hd")

    Returns:
        App::Part assembly containing all deck components
    """
    # Parameters
    length_x_in = 192.0  # 16'
    proj_y_in = 96.0  # 8'
    joist_spacing_oc_in = 16.0
    rim_label = "2x12x192"
    joist_label = "2x12x96"
    deck_label = "deckboard_5_4x6x192_PT"
    post_label = "post_6x6x144_PT"
    hanger_label = "hanger_LU210"
    hanger_thickness = 0.06  # approx 16ga
    hanger_height = 7.8125  # ~7-13/16" overall height
    hanger_seat_depth = 2.0  # back plate depth

    # Find stock
    rim_row = lc.find_stock(catalog_rows, rim_label)
    joist_row = lc.find_stock(catalog_rows, joist_label)
    deck_row = lc.find_stock(catalog_rows, deck_label)
    post_row = lc.find_stock(catalog_rows, post_label)

    if not rim_row or not joist_row:
        raise ValueError("Required rim/joist stock not found in catalog.")
    if not deck_row:
        raise ValueError(f"Deck board label '{deck_label}' not found in catalog.")
    if not post_row:
        raise ValueError(f"Post label '{post_label}' not found in catalog.")

    # Dimensions
    rim_thick = float(rim_row["actual_thickness_in"])  # 1.5"
    rim_depth = float(rim_row["actual_width_in"])  # 11.25"
    rim_len = float(rim_row["length_in"])  # 192"
    joist_thick = float(joist_row["actual_thickness_in"])
    joist_depth = float(joist_row["actual_width_in"])
    joist_len = float(joist_row["length_in"])  # 96"
    deck_thick = float(deck_row["actual_thickness_in"])  # 1.0"
    deck_width = float(deck_row["actual_width_in"])  # 5.5"
    deck_len = float(deck_row["length_in"])  # 192"
    deck_gap = 0.125  # 1/8" gap
    post_thick = float(post_row["actual_thickness_in"])  # 5.5"
    post_width = float(post_row["actual_width_in"])  # 5.5"
    post_len = float(post_row["length_in"])  # 144" stock
    post_height_in = joist_depth  # flush to deck board underside

    created = []

    def make_rim(name, y_local):
        box = Part.makeBox(lc.inch(rim_len), lc.inch(rim_thick), lc.inch(rim_depth))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(0, lc.inch(y_local), 0)
        lc.attach_metadata(obj, rim_row, rim_label, supplier=supplier)
        return obj

    def make_joist(name, x_local):
        box = Part.makeBox(lc.inch(joist_thick), lc.inch(proj_y_in), lc.inch(joist_depth))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(lc.inch(x_local), 0, 0)
        lc.attach_metadata(obj, joist_row, joist_label, supplier=supplier)
        return obj

    def make_deck_board(name, y_local):
        box = Part.makeBox(lc.inch(deck_len), lc.inch(deck_width), lc.inch(deck_thick))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(0, lc.inch(y_local), lc.inch(joist_depth))
        lc.attach_metadata(obj, deck_row, deck_label, supplier=supplier)
        return obj

    def make_post(name, x_local, y_local, z_local):
        box = Part.makeBox(lc.inch(post_width), lc.inch(post_thick), lc.inch(post_height_in))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = box
        obj.Placement.Base = App.Vector(lc.inch(x_local), lc.inch(y_local), lc.inch(z_local))
        lc.attach_metadata(obj, post_row, post_label, supplier=supplier)
        try:
            if "cut_length_in" not in obj.PropertiesList:
                obj.addProperty("App::PropertyString", "cut_length_in")
            obj.cut_length_in = f"{post_height_in}"
        except Exception:
            pass
        return obj

    # Rims
    rim_offset = joist_thick
    created.append(make_rim("Rim_House", -rim_offset))
    created.append(make_rim("Rim_Outboard", proj_y_in))

    # Joists @ 16" OC along X
    centers = []
    first_center = joist_thick / 2.0
    last_center = length_x_in - (joist_thick / 2.0)
    c = first_center
    while c < last_center - 1e-6:
        centers.append(c)
        c += joist_spacing_oc_in
    if not centers or centers[-1] < last_center - 1e-6:
        centers.append(last_center)

    for idx, cx in enumerate(centers, start=1):
        x_pos = cx - (joist_thick / 2.0)
        created.append(make_joist(f"Joist_{idx}", x_pos))

    # Deck boards running along X, 1/8" gaps
    boards = []
    board_count = 0
    step = deck_width + deck_gap
    y_pos = -1.5  # shift first board toward house by 1.5"
    last_full_end = None

    while True:
        next_y = y_pos + deck_width
        if next_y > proj_y_in:
            # Rip last board to remaining space
            rip_start = (last_full_end if last_full_end is not None else y_pos) + deck_gap
            remaining = proj_y_in - rip_start + 1.5  # widen rip by 1.5"
            if remaining > 0.25:
                board_count += 1
                rip = make_deck_board(f"Deck_{board_count}_RIP", rip_start)
                rip.Shape = Part.makeBox(lc.inch(deck_len), lc.inch(remaining), lc.inch(deck_thick))
                rip.Placement.Base.y = lc.inch(rip_start)
                rip.Placement.Base.z = lc.inch(joist_depth)
                boards.append(rip)
            break
        board_count += 1
        boards.append(make_deck_board(f"Deck_{board_count}", y_pos))
        last_full_end = next_y
        y_pos += step

    created.extend(boards)

    # Posts: four corners + two intermediate along outboard rim
    posts = []
    z_post_base = 0.0
    posts.append(make_post("Post_Front_Left", 1.5, -1.5, z_post_base))
    posts.append(make_post("Post_Front_Right", length_x_in - post_width - 1.5, -1.5, z_post_base))
    posts.append(make_post("Post_Outboard_Left", 1.5, proj_y_in - post_thick, z_post_base))
    posts.append(
        make_post(
            "Post_Outboard_Right",
            length_x_in - post_width - 1.5,
            proj_y_in - post_thick,
            z_post_base,
        )
    )

    # Two intermediate posts along outboard rim
    mid_positions = [72.75, 120.75]
    for i, x_mid in enumerate(mid_positions, start=1):
        posts.append(
            make_post(f"Post_Outboard_Mid_{i}", x_mid, proj_y_in - post_thick, z_post_base)
        )

    created.extend(posts)

    # Cut deck boards for post penetrations
    def cut_board_for_posts(board, posts):
        try:
            b = board.Shape
        except Exception:
            return board
        by = board.Placement.Base.y / lc.inch(1)
        bw = b.BoundBox.YLength / lc.inch(1)
        bz = board.Placement.Base.z / lc.inch(1)
        cuts = []
        for p in posts:
            px = p.Placement.Base.x / lc.inch(1)
            py = p.Placement.Base.y / lc.inch(1)
            pz = p.Placement.Base.z / lc.inch(1)
            if py > by + bw or (py + post_thick) < by:
                continue
            hole = Part.makeBox(lc.inch(post_width), lc.inch(post_thick), lc.inch(deck_thick * 2.0))
            hole.Placement.Base = App.Vector(
                lc.inch(px), lc.inch(py), lc.inch(bz - deck_thick * 0.5)
            )
            cuts.append(hole)
        if not cuts:
            return board
        try:
            new_shape = board.Shape
            for h in cuts:
                new_shape = new_shape.cut(h)
            board.Shape = new_shape
        except Exception:
            pass
        return board

    for b in boards:
        cut_board_for_posts(b, posts)

    # Hangers on house rim for each joist (skip first/last)
    hangs = []
    house_face_y = 0.0
    outboard_face_y = proj_y_in

    for idx, cx in enumerate(centers, start=1):
        if idx == 1 or idx == len(centers):
            continue  # skip end joists
        try:
            # House rim hanger: extends into +Y
            hangs.append(
                lc.make_hanger(
                    doc,
                    f"Hanger_House_{idx}",
                    house_face_y,
                    cx,
                    joist_thick,
                    hanger_thickness,
                    hanger_height,
                    hanger_seat_depth,
                    hanger_label,
                    direction=1,
                    axis="Y",
                    debug_components=False,
                    color=(0.6, 0.6, 0.7),
                )
            )
            # Outboard rim hanger: extends into -Y
            hangs.append(
                lc.make_hanger(
                    doc,
                    f"Hanger_Outboard_{idx}",
                    outboard_face_y,
                    cx + joist_thick,
                    joist_thick,
                    hanger_thickness,
                    hanger_height,
                    hanger_seat_depth,
                    hanger_label,
                    direction=-1,
                    axis="Y",
                    debug_components=False,
                    color=(0.6, 0.6, 0.7),
                )
            )
        except Exception as e:
            App.Console.PrintError(f"[deck_assemblies] Hanger build failed for joist {idx}: {e}\n")

    created.extend(hangs)

    # Create assembly (App::Part)
    App.Console.PrintMessage(
        f"[deck_assemblies] Created assembly: {assembly_name} (type: App::Part)\n"
    )
    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    # Add all parts to assembly
    App.Console.PrintMessage(f"[deck_assemblies] Adding {len(created)} parts to assembly...\n")
    for obj in created:
        assembly.addObject(obj)

    # Apply global position offset
    assembly.Placement.Base = App.Vector(lc.inch(x_base), lc.inch(y_base), lc.inch(z_base))

    doc.recompute()

    App.Console.PrintMessage(
        f"[deck_assemblies] ✓ Assembly complete: {assembly_name} "
        f"({len(centers)} joists, {len(boards)} deck boards, {len(posts)} posts, {len(hangs)} hangers)\n"
    )

    return assembly
