# -*- coding: utf-8 -*-
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


# ============================================================
# CONSTANTS - Hardware dimensions for Simpson Strong-Tie LU210
# ============================================================
# LU210 is used for 2x10 through 2x12 joists
# Ref: https://www.strongtie.com/hangersandanchors_woodconstruction/lu_hanger/p/lu
HANGER_THICKNESS_IN = 0.06  # ~16 gauge steel
HANGER_HEIGHT_IN = 7.8125  # 7-13/16" overall height
HANGER_SEAT_DEPTH_IN = 2.0  # Seat depth (back plate)
HANGER_LABEL = "hanger_LU210"
HANGER_COLOR = (0.6, 0.6, 0.7)

# Framing spacing (IRC R502.3)
JOIST_SPACING_OC_IN = 16.0  # 16" on-center

# Deck board gaps (per manufacturer recommendations)
DECK_BOARD_GAP_IN = 0.125  # 1/8" gap between boards

# Deck board overhang beyond framing (per local preference)
DECK_OVERHANG_IN = 1.0  # 1" overhang on outer edges

# Maximum deck board length (16' stock for even distribution)
MAX_DECK_BOARD_LENGTH_IN = 192.0  # 16' = 192"

# Minimum acceptable end segment length (avoid short stub boards)
MIN_END_SEGMENT_IN = 24.0  # 2' minimum - shorter segments look bad and waste material

# Floating point tolerance for length comparisons (inches)
LENGTH_TOLERANCE_IN = 0.1  # 1/10" tolerance for comparing board lengths

# Deck board catalog label (matches lumber_catalog.csv)
DECK_BOARD_LABEL = "deckboard_5_4x6x192_PT"  # 5/4x6x16' PT deck boards

# Seam board configuration
# Seam boards span between two joists (double-joist at each seam)
SEAM_BOARD_WIDTH_IN = 5.5  # Same as deck board width
DOUBLE_JOIST_SPACING_IN = 5.5  # Distance between double-joist pair (seam board width)


def _calculate_seam_zones(
    total_length,
    max_board_length,
    joist_spacing,
    joist_thick=1.5,
    seam_board_width=5.5,
    first_joist_offset=None,
):
    """
    Calculate seam zones for deck board layout with perpendicular seam boards.

    Real-world construction workflow:
    1. Lay 16' field boards from picture frame edge
    2. Trim them over a joist (chalk line), removing minimum to align on joist
    3. Place perpendicular seam board starting at the trim line
    4. Add second joist to support the far edge of seam board
    5. Continue with next set of field boards from the second joist

    IMPORTANT: Field boards are 16' (192") STOCK that get TRIMMED to fit.
    - First board: starts at 0, trimmed to end on nearest joist within 192"
    - Subsequent boards: start after seam, trimmed to end on next joist within 192"
    - All board ends land on joist centers (with >= half joist face covered)

    This creates a "double joist" situation at each seam:
    - First joist supports the trimmed ends of first set of field boards
    - Seam board spans from first joist to second joist (perpendicular)
    - Second joist supports the start of next set of field boards

    Args:
        total_length: Total length to cover (inches)
        max_board_length: Maximum board length (inches), e.g., 192" for 16'
        joist_spacing: Regular joist spacing on-center (inches), e.g., 16"
        joist_thick: Joist thickness (1.5" for 2x lumber)
        seam_board_width: Width of seam board (5.5" for 5/4x6)
        first_joist_offset: Distance from zone start (position 0) to first joist center.
                           If None, defaults to joist_thick/2 (0.75" for 2x lumber).
                           For field boards starting after picture frame, this should be
                           calculated as the distance from field start to the first joist.

    Returns:
        List of dicts describing field and seam segments:
        [
            {"type": "field", "start": 0.0, "end": 184.125, "stock_length": 192.0},
            {"type": "seam", "start": 184.25, "end": 189.875, ...},
            {"type": "field", "start": 190.0, "end": 374.125, "stock_length": 192.0},
            ...
        ]
        Where field segments show cut length (end - start) from stock_length boards.
    """
    if total_length <= max_board_length:
        # Single run of field boards covers entire length - no seams needed
        return [
            {"type": "field", "start": 0.0, "end": total_length, "stock_length": max_board_length}
        ]

    segments = []
    current_pos = 0.0
    gap = DECK_BOARD_GAP_IN

    # Calculate how much space a seam zone takes up
    # Seam board width = 5.5", plus gaps on each side
    seam_zone_width = seam_board_width + 2 * gap  # Total including gaps

    # Calculate all joist positions within the zone
    # Default: first joist at joist_thick/2 from zone start, then every joist_spacing
    if first_joist_offset is None:
        first_joist_offset = joist_thick / 2.0

    joist_positions = []
    pos = first_joist_offset
    while pos < total_length:
        joist_positions.append(pos)
        pos += joist_spacing

    while current_pos < total_length - LENGTH_TOLERANCE_IN:
        # Maximum field board run before needing a seam
        max_run = max_board_length

        # Check if we can reach the end without a seam
        remaining = total_length - current_pos
        if remaining <= max_run:
            # Final field segment to the end
            segments.append(
                {
                    "type": "field",
                    "start": current_pos,
                    "end": total_length,
                    "stock_length": max_board_length,
                }
            )
            break

        # Need a seam - find the farthest joist we can reach within max_run
        # Field boards should end with at least half the joist face covered (0.75")
        # Field board ends at joist_center + joist_thick/4 (covers >= half joist)

        # Find the FARTHEST joist within max_run from current_pos
        # (we want to use as much of the 16' board as possible)
        best_joist_idx = None

        for idx, joist_pos in enumerate(joist_positions):
            # Field board end position - board covers at least half the joist
            field_end = joist_pos + joist_thick / 4.0

            # Must be after current position
            if field_end <= current_pos + gap:
                continue

            # Must not exceed max board length from current position
            board_length = field_end - current_pos
            if board_length > max_run:
                break  # Past this joist, all others are too far

            # Check if there's room for seam zone + meaningful field boards after
            space_after_seam = total_length - (field_end + seam_zone_width)
            if space_after_seam < MIN_END_SEGMENT_IN and space_after_seam > 0:
                # Would create short stub after seam - skip this position
                continue

            # This joist is valid - keep it (we want the farthest one)
            best_joist_idx = idx

        if best_joist_idx is None:
            # No valid joist found - just extend to end
            segments.append(
                {
                    "type": "field",
                    "start": current_pos,
                    "end": total_length,
                    "stock_length": max_board_length,
                }
            )
            break

        # Create field segment (trimmed from 16' stock)
        joist1_center = joist_positions[best_joist_idx]
        field_end = joist1_center + joist_thick / 4.0
        segments.append(
            {
                "type": "field",
                "start": current_pos,
                "end": field_end,
                "stock_length": max_board_length,
            }
        )

        # Create seam zone
        # Seam board starts at field_end + gap
        seam_start = field_end + gap
        # Second joist center is seam_board_width from first joist center
        joist2_center = joist1_center + seam_board_width
        # Seam board ends at joist2 center + joist_thick/4 (covering half of joist2)
        seam_end = joist2_center + joist_thick / 4.0

        segments.append(
            {
                "type": "seam",
                "start": seam_start,
                "end": seam_end,
                "joist1_center": joist1_center,
                "joist2_center": joist2_center,
            }
        )

        # Next field segment starts after seam + gap
        current_pos = seam_end + gap

    return segments


def _calculate_splice_positions(total_length, max_board_length, joist_spacing, start_offset=0.0):
    """
    Calculate board splice positions that align with joist centers.

    DEPRECATED: Use _calculate_seam_zones() for new code.
    This function is kept for backward compatibility.

    All board ends MUST be supported - no floating ends allowed.
    Splices are placed at joist center positions within max_board_length constraints.

    Args:
        total_length: Total length to cover (inches)
        max_board_length: Maximum board length (inches), e.g., 192" for 16'
        joist_spacing: Joist spacing on-center (inches), e.g., 16"
        start_offset: Offset from zone start to first joist center (inches)

    Returns:
        List of splice positions (X or Y coordinates where boards end/start)
        First position is 0.0 (start), last is total_length (end)
    """

    if total_length <= max_board_length:
        # Single board covers entire length - no splices needed
        return [0.0, total_length]

    # Calculate joist positions within the zone
    joist_positions = []
    pos = start_offset
    while pos < total_length:
        if pos > 0:  # Don't include starting edge as a joist position
            joist_positions.append(pos)
        pos += joist_spacing

    if not joist_positions:
        # No interior joists - single board (shouldn't happen for long spans)
        return [0.0, total_length]

    # Calculate ideal number of boards and target length
    num_boards = max(
        1, int(total_length / max_board_length) + (1 if total_length % max_board_length > 0 else 0)
    )

    # Check if greedy approach would create short end segment
    # If so, try redistributing to avoid it
    ideal_board_length = total_length / num_boards

    # Find splice positions using ideal spacing, snapped to nearest joist
    splices = [0.0]

    for i in range(1, num_boards):
        target_pos = ideal_board_length * i
        # Find nearest joist to target position
        best_joist = None
        best_distance = float("inf")
        for joist_pos in joist_positions:
            # Must be after previous splice
            if joist_pos <= splices[-1]:
                continue
            # Must not exceed max_board_length from previous splice
            if joist_pos - splices[-1] > max_board_length:
                break
            # Find closest to target
            distance = abs(joist_pos - target_pos)
            if distance < best_distance:
                best_distance = distance
                best_joist = joist_pos

        if best_joist is not None:
            splices.append(best_joist)

    # Add end position
    splices.append(total_length)

    # Validate: check if any segment exceeds max_board_length
    # If so, fall back to greedy algorithm
    needs_greedy = False
    for i in range(len(splices) - 1):
        if splices[i + 1] - splices[i] > max_board_length + LENGTH_TOLERANCE_IN:
            needs_greedy = True
            break

    if needs_greedy:
        # Fall back to greedy approach
        splices = [0.0]
        current_pos = 0.0

        while current_pos < total_length - LENGTH_TOLERANCE_IN:
            best_joist = None
            for joist_pos in joist_positions:
                if joist_pos <= current_pos:
                    continue
                board_length = joist_pos - current_pos
                if board_length <= max_board_length:
                    best_joist = joist_pos
                else:
                    break

            if best_joist is None:
                splices.append(total_length)
                break
            else:
                splices.append(best_joist)
                current_pos = best_joist

            if current_pos >= total_length - joist_spacing:
                splices.append(total_length)
                break

        splices = sorted(set(splices))
        if splices[-1] < total_length - LENGTH_TOLERANCE_IN:
            splices.append(total_length)

    return splices


def _create_deck_hangers(
    doc,
    joist_centers,
    joist_thick,
    joist_depth,
    proj_y_in,
    hanger_thickness,
    hanger_height,
    hanger_seat_depth,
    hanger_label,
    name_prefix="",
):
    """
    Create hangers for deck joists at house rim and outboard rim.

    Deck geometry:
        - Joists run N-S (Y direction) from house rim (Y=0) to outboard rim (Y=proj_y_in)
        - Rims run E-W (X direction)
        - House rim: south face at Y=0
        - Outboard rim: north face at Y=proj_y_in

    Args:
        doc: FreeCAD document
        joist_centers: List of joist center X positions (skip first/last for hangers)
        joist_thick: Joist thickness (1.5" for 2x)
        joist_depth: Joist depth (11.25" for 2x12)
        proj_y_in: Deck projection depth in Y (96" typical)
        hanger_thickness: Hanger metal thickness
        hanger_height: Hanger flange height
        hanger_seat_depth: Hanger seat depth
        hanger_label: Catalog label for BOM
        name_prefix: Optional prefix for hanger names

    Returns:
        List of hanger objects
    """
    hangs = []

    for idx, cx in enumerate(joist_centers, start=1):
        if idx == 1 or idx == len(joist_centers):
            continue  # skip end joists (they're rim joists)
        try:
            prefix = f"{name_prefix}_" if name_prefix else ""

            # House rim hanger: joist meets south face of house rim at Y=0
            # Joist is SOUTH of rim face, hanger opens NORTH toward rim
            hangs.append(
                lc.make_hanger_for_joist(
                    doc,
                    f"{prefix}Hanger_House_{idx}",
                    joist_x_in=cx,  # Joist center X
                    joist_y_in=0.0,  # Y where joist meets rim (south face of house rim)
                    joist_z_in=0.0,  # Joist bottom Z (deck joists sit at Z=0)
                    joist_thick_in=joist_thick,
                    joist_depth_in=joist_depth,
                    rim_face_position_in=0.0,  # South face of house rim at Y=0
                    rim_axis="X",  # Rim runs E-W
                    rim_side="south",  # Joist is south of rim face
                    hanger_thickness_in=hanger_thickness,
                    hanger_height_in=hanger_height,
                    hanger_seat_depth_in=hanger_seat_depth,
                    hanger_label=hanger_label,
                    color=(0.6, 0.6, 0.7),
                )
            )
            # Outboard rim hanger: joist meets north face of outboard rim at Y=proj_y_in
            # Joist is NORTH of rim face, hanger opens SOUTH toward rim
            hangs.append(
                lc.make_hanger_for_joist(
                    doc,
                    f"{prefix}Hanger_Outboard_{idx}",
                    joist_x_in=cx,  # Joist center X
                    joist_y_in=proj_y_in,  # Y where joist meets rim (north face of outboard rim)
                    joist_z_in=0.0,  # Joist bottom Z
                    joist_thick_in=joist_thick,
                    joist_depth_in=joist_depth,
                    rim_face_position_in=proj_y_in,  # North face of outboard rim at Y=proj_y_in
                    rim_axis="X",  # Rim runs E-W
                    rim_side="north",  # Joist is north of rim face
                    hanger_thickness_in=hanger_thickness,
                    hanger_height_in=hanger_height,
                    hanger_seat_depth_in=hanger_seat_depth,
                    hanger_label=hanger_label,
                    color=(0.6, 0.6, 0.7),
                )
            )
        except Exception as e:
            App.Console.PrintError(f"[deck_assemblies] Hanger build failed for joist {idx}: {e}\n")

    return hangs


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
    rim_label = "2x12x192"
    joist_label = "2x12x96"

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
    _joist_len = float(joist_row["length_in"])  # noqa: F841 - kept for reference

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
        c += JOIST_SPACING_OC_IN
    if not centers or centers[-1] < last_center - 1e-6:
        centers.append(last_center)

    for idx, cx in enumerate(centers, start=1):
        x_pos = cx - (joist_thick / 2.0)
        created.append(make_joist(f"Joist_{idx}", x_pos))

    # Hangers on house rim and outboard rim for each interior joist
    hangs = _create_deck_hangers(
        doc,
        centers,
        joist_thick,
        joist_depth,
        proj_y_in,
        HANGER_THICKNESS_IN,
        HANGER_HEIGHT_IN,
        HANGER_SEAT_DEPTH_IN,
        HANGER_LABEL,
    )
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
    _length_x_in = 96.0  # 8' (not 16') - noqa: F841 - kept for reference
    proj_y_in = 96.0  # 8'
    _joist_spacing_oc_in = 16.0  # noqa: F841 - kept for reference
    rim_label = "2x12x96"  # 8' rim (not 16')
    joist_label = "2x12x96"
    _hanger_label = "hanger_LU210"  # noqa: F841 - kept for reference
    _hanger_thickness = 0.06  # noqa: F841 - kept for reference
    _hanger_height = 7.8125  # noqa: F841 - kept for reference
    _hanger_seat_depth = 2.0  # noqa: F841 - kept for reference

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
    _joist_len = float(joist_row["length_in"])  # noqa: F841 - kept for reference

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
    rim_house_outboard_label = "2x12x120"  # 10' boards for house/outboard rims (cut to 105")
    joist_label = "2x12x96"  # 8' joists

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
    _joist_len = float(joist_row["length_in"])  # noqa: F841 - kept for reference

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
        c += JOIST_SPACING_OC_IN
    if not centers or centers[-1] < last_center - 1e-6:
        centers.append(last_center)

    for idx, cx in enumerate(centers, start=1):
        x_pos = cx - (joist_thick / 2.0)
        created.append(make_joist(f"Joist_{idx}", x_pos))

    # Hangers on house rim and outboard rim for each interior joist
    hangs = _create_deck_hangers(
        doc,
        centers,
        joist_thick,
        joist_depth,
        proj_y_in,
        HANGER_THICKNESS_IN,
        HANGER_HEIGHT_IN,
        HANGER_SEAT_DEPTH_IN,
        HANGER_LABEL,
    )
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


# ============================================================
# MITERED EDGE BOARD HELPERS
# ============================================================


def _make_mitered_edge_board(
    doc,
    deck_row,
    deck_label,
    edge_length_in,
    deck_width,
    deck_thick,
    board_z,
    x_pos,
    y_pos,
    name,
    supplier,
    miter_start=None,
    miter_end=None,
    edge_axis="Y",
    edge_position="left",
):
    """
    Create an edge board with optional 45-degree mitered corners.

    Miters are cut at 45 degrees so that two perpendicular edge boards meet cleanly.
    The miter cuts remove a triangular section from the end of the board.

    Args:
        doc: FreeCAD document
        deck_row: Catalog row for deck boards
        deck_label: Catalog label for BOM
        edge_length_in: Full length of edge board before miters (inches)
        deck_width: Width of deck board (5.5" for 5/4x6)
        deck_thick: Thickness of deck board
        board_z: Z position (top of joists)
        x_pos: X position of board's left edge
        y_pos: Y position of board's front (south) edge
        name: Part name
        supplier: Supplier for BOM
        miter_start: "left", "right", "front", "back" - which corner to miter at start
        miter_end: "left", "right", "front", "back" - which corner to miter at end
        edge_axis: "X" (board runs E-W) or "Y" (board runs N-S)
        edge_position: For NS boards: "left" (inner edge at X=deck_width) or "right" (inner edge at X=0)
                      For EW boards: "front" (inner edge at Y=deck_width) or "back" (inner edge at Y=0)

    Returns:
        Part::Feature object with mitered shape
    """
    import Part

    # Create base board shape
    if edge_axis == "Y":
        # Board runs N-S (along Y axis)
        base_box = Part.makeBox(lc.inch(deck_width), lc.inch(edge_length_in), lc.inch(deck_thick))
    else:
        # Board runs E-W (along X axis)
        base_box = Part.makeBox(lc.inch(edge_length_in), lc.inch(deck_width), lc.inch(deck_thick))

    shape = base_box

    # Apply 45-degree miter cuts for picture frame corners
    #
    # Picture frame layout (top-down view, north up):
    #
    #     NW corner              NE corner
    #        +--------------------+
    #        |\     Back (EW)    /|
    #        | \               / |
    #   Left |  +-------------+  | Right
    #   (NS) |  |             |  | (NS)
    #        |  |   Field     |  |
    #        |  |             |  |
    #        |  +-------------+  |
    #        | /               \ |
    #        |/    Front (EW)   \|
    #        +--------------------+
    #     SW corner              SE corner
    #
    # For EW boards (front/back):
    #   - "left" miter: 45° cut at west end, diagonal from (0,0) to (deck_width, deck_width)
    #   - "right" miter: 45° cut at east end, diagonal from (length,deck_width) to (length-deck_width,0)
    #
    # For NS boards (left/right):
    #   - "front"/"south" miter: 45° cut at south end
    #   - "back"/"north" miter: 45° cut at north end

    if edge_axis == "Y":
        # Board runs N-S (Y direction)
        # Board dimensions: X = deck_width, Y = edge_length_in
        #
        # For left edge board (edge_position="left", at west side of deck):
        #   - West face (X=0) is outer edge
        #   - East face (X=deck_width) is inner edge (meets field boards)
        #   - Miter at south end should cut the SE inner corner
        #   - Miter at north end should cut the NE inner corner
        #
        # For right edge board (edge_position="right", at east side of deck):
        #   - East face (X=deck_width) is outer edge
        #   - West face (X=0) is inner edge (meets field boards)
        #   - Miter at south end should cut the SW inner corner
        #   - Miter at north end should cut the NW inner corner
        #
        if miter_start in ("front", "south"):
            if edge_position == "left":
                # Left edge board: cut removes SE inner corner (at X=deck_width, Y=0)
                # Triangle: (deck_width, 0) - (deck_width, deck_width) - (0, 0)
                cut_points = [
                    App.Vector(lc.inch(deck_width), 0, -lc.inch(deck_thick)),
                    App.Vector(lc.inch(deck_width), lc.inch(deck_width), -lc.inch(deck_thick)),
                    App.Vector(0, 0, -lc.inch(deck_thick)),
                    App.Vector(lc.inch(deck_width), 0, -lc.inch(deck_thick)),
                ]
            else:
                # Right edge board: cut removes SW inner corner (at X=0, Y=0)
                # Triangle: (0, 0) - (deck_width, 0) - (0, deck_width)
                cut_points = [
                    App.Vector(0, 0, -lc.inch(deck_thick)),
                    App.Vector(lc.inch(deck_width), 0, -lc.inch(deck_thick)),
                    App.Vector(0, lc.inch(deck_width), -lc.inch(deck_thick)),
                    App.Vector(0, 0, -lc.inch(deck_thick)),
                ]
            cut_wire = Part.makePolygon(cut_points)
            cut_face = Part.Face(cut_wire)
            cut_shape = cut_face.extrude(App.Vector(0, 0, lc.inch(deck_thick * 3)))
            shape = shape.cut(cut_shape)

        if miter_end in ("back", "north"):
            if edge_position == "left":
                # Left edge board: cut removes NE inner corner (at X=deck_width, Y=length)
                # Triangle: (deck_width, length) - (0, length) - (deck_width, length-deck_width)
                cut_points = [
                    App.Vector(lc.inch(deck_width), lc.inch(edge_length_in), -lc.inch(deck_thick)),
                    App.Vector(0, lc.inch(edge_length_in), -lc.inch(deck_thick)),
                    App.Vector(
                        lc.inch(deck_width),
                        lc.inch(edge_length_in - deck_width),
                        -lc.inch(deck_thick),
                    ),
                    App.Vector(lc.inch(deck_width), lc.inch(edge_length_in), -lc.inch(deck_thick)),
                ]
            else:
                # Right edge board: cut removes NW inner corner (at X=0, Y=length)
                # Triangle: (0, length) - (0, length-deck_width) - (deck_width, length)
                cut_points = [
                    App.Vector(0, lc.inch(edge_length_in), -lc.inch(deck_thick)),
                    App.Vector(0, lc.inch(edge_length_in - deck_width), -lc.inch(deck_thick)),
                    App.Vector(lc.inch(deck_width), lc.inch(edge_length_in), -lc.inch(deck_thick)),
                    App.Vector(0, lc.inch(edge_length_in), -lc.inch(deck_thick)),
                ]
            cut_wire = Part.makePolygon(cut_points)
            cut_face = Part.Face(cut_wire)
            cut_shape = cut_face.extrude(App.Vector(0, 0, lc.inch(deck_thick * 3)))
            shape = shape.cut(cut_shape)

    else:
        # Board runs E-W (X direction)
        # Board dimensions: X = edge_length_in, Y = deck_width
        #
        # For front edge board (edge_position="front", at south side of deck):
        #   - South face (Y=0) is outer edge
        #   - North face (Y=deck_width) is inner edge (meets field boards)
        #   - Miter at west end should cut the NW inner corner
        #   - Miter at east end should cut the NE inner corner
        #
        # For back edge board (edge_position="back", at north side of deck):
        #   - North face (Y=deck_width) is outer edge
        #   - South face (Y=0) is inner edge (meets field boards)
        #   - Miter at west end should cut the SW inner corner
        #   - Miter at east end should cut the SE inner corner
        #
        if miter_start in ("left", "west"):
            if edge_position == "front":
                # Front edge board: cut removes NW inner corner (at X=0, Y=deck_width)
                # Triangle: (0, deck_width) - (deck_width, deck_width) - (0, 0)
                cut_points = [
                    App.Vector(0, lc.inch(deck_width), -lc.inch(deck_thick)),
                    App.Vector(lc.inch(deck_width), lc.inch(deck_width), -lc.inch(deck_thick)),
                    App.Vector(0, 0, -lc.inch(deck_thick)),
                    App.Vector(0, lc.inch(deck_width), -lc.inch(deck_thick)),
                ]
            else:
                # Back edge board: cut removes SW inner corner (at X=0, Y=0)
                # Triangle: (0, 0) - (0, deck_width) - (deck_width, 0)
                cut_points = [
                    App.Vector(0, 0, -lc.inch(deck_thick)),
                    App.Vector(0, lc.inch(deck_width), -lc.inch(deck_thick)),
                    App.Vector(lc.inch(deck_width), 0, -lc.inch(deck_thick)),
                    App.Vector(0, 0, -lc.inch(deck_thick)),
                ]
            cut_wire = Part.makePolygon(cut_points)
            cut_face = Part.Face(cut_wire)
            cut_shape = cut_face.extrude(App.Vector(0, 0, lc.inch(deck_thick * 3)))
            shape = shape.cut(cut_shape)

        if miter_end in ("right", "east"):
            if edge_position == "front":
                # Front edge board: cut removes NE inner corner (at X=length, Y=deck_width)
                # Triangle: (length, deck_width) - (length-deck_width, deck_width) - (length, 0)
                cut_points = [
                    App.Vector(lc.inch(edge_length_in), lc.inch(deck_width), -lc.inch(deck_thick)),
                    App.Vector(
                        lc.inch(edge_length_in - deck_width),
                        lc.inch(deck_width),
                        -lc.inch(deck_thick),
                    ),
                    App.Vector(lc.inch(edge_length_in), 0, -lc.inch(deck_thick)),
                    App.Vector(lc.inch(edge_length_in), lc.inch(deck_width), -lc.inch(deck_thick)),
                ]
            else:
                # Back edge board: cut removes SE inner corner (at X=length, Y=0)
                # Triangle: (length, 0) - (length, deck_width) - (length-deck_width, 0)
                cut_points = [
                    App.Vector(lc.inch(edge_length_in), 0, -lc.inch(deck_thick)),
                    App.Vector(lc.inch(edge_length_in), lc.inch(deck_width), -lc.inch(deck_thick)),
                    App.Vector(lc.inch(edge_length_in - deck_width), 0, -lc.inch(deck_thick)),
                    App.Vector(lc.inch(edge_length_in), 0, -lc.inch(deck_thick)),
                ]
            cut_wire = Part.makePolygon(cut_points)
            cut_face = Part.Face(cut_wire)
            cut_shape = cut_face.extrude(App.Vector(0, 0, lc.inch(deck_thick * 3)))
            shape = shape.cut(cut_shape)

    # Create FreeCAD object
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    obj.Placement.Base = App.Vector(lc.inch(x_pos), lc.inch(y_pos), lc.inch(board_z))
    lc.attach_metadata(obj, deck_row, deck_label, supplier=supplier)

    return obj


# ============================================================
# SCARF JOINT (ANGLED SPLICE) HELPER
# ============================================================


def _make_scarf_cut(
    shape, cut_position, board_width, board_thick, cut_angle_deg=22.5, cut_side="right", axis="X"
):
    """
    Apply a scarf (angled splice) cut to a board shape.

    A scarf joint is an angled cut used to splice boards end-to-end.
    More professional than a square butt joint - sheds water better
    and provides more surface area for fastening.

    Args:
        shape: FreeCAD shape to cut
        cut_position: Position along the board where cut occurs (inches)
        board_width: Board width perpendicular to cut (inches)
        board_thick: Board thickness (inches)
        cut_angle_deg: Cut angle in degrees (22.5 typical)
        cut_side: "right" or "left" - which side of the cut to keep
        axis: "X" or "Y" - which axis the board runs along

    Returns:
        Modified FreeCAD shape with scarf cut applied
    """
    import math

    # Calculate the horizontal run of the angled cut
    # For a 22.5° angle, run = board_width * tan(22.5°) ≈ 0.414 * board_width
    angle_rad = math.radians(cut_angle_deg)
    cut_run = board_width * math.tan(angle_rad)

    # Create cutting wedge
    if axis == "X":
        # Board runs along X axis, cut perpendicular creates Y-Z face
        if cut_side == "right":
            # Keep right side: cut removes left portion at cut_position
            # Wedge: (cut_position - cut_run, 0) to (cut_position, board_width) to (cut_position - cut_run, board_width)
            cut_points = [
                App.Vector(lc.inch(cut_position - cut_run), 0, -lc.inch(board_thick)),
                App.Vector(lc.inch(cut_position), 0, -lc.inch(board_thick)),
                App.Vector(lc.inch(cut_position), lc.inch(board_width), -lc.inch(board_thick)),
                App.Vector(
                    lc.inch(cut_position - cut_run), lc.inch(board_width), -lc.inch(board_thick)
                ),
                App.Vector(lc.inch(cut_position - cut_run), 0, -lc.inch(board_thick)),
            ]
        else:
            # Keep left side: cut removes right portion at cut_position
            cut_points = [
                App.Vector(lc.inch(cut_position), 0, -lc.inch(board_thick)),
                App.Vector(lc.inch(cut_position + cut_run), 0, -lc.inch(board_thick)),
                App.Vector(
                    lc.inch(cut_position + cut_run), lc.inch(board_width), -lc.inch(board_thick)
                ),
                App.Vector(lc.inch(cut_position), lc.inch(board_width), -lc.inch(board_thick)),
                App.Vector(lc.inch(cut_position), 0, -lc.inch(board_thick)),
            ]
    else:
        # Board runs along Y axis, cut perpendicular creates X-Z face
        if cut_side == "right":
            cut_points = [
                App.Vector(0, lc.inch(cut_position - cut_run), -lc.inch(board_thick)),
                App.Vector(0, lc.inch(cut_position), -lc.inch(board_thick)),
                App.Vector(lc.inch(board_width), lc.inch(cut_position), -lc.inch(board_thick)),
                App.Vector(
                    lc.inch(board_width), lc.inch(cut_position - cut_run), -lc.inch(board_thick)
                ),
                App.Vector(0, lc.inch(cut_position - cut_run), -lc.inch(board_thick)),
            ]
        else:
            cut_points = [
                App.Vector(0, lc.inch(cut_position), -lc.inch(board_thick)),
                App.Vector(0, lc.inch(cut_position + cut_run), -lc.inch(board_thick)),
                App.Vector(
                    lc.inch(board_width), lc.inch(cut_position + cut_run), -lc.inch(board_thick)
                ),
                App.Vector(lc.inch(board_width), lc.inch(cut_position), -lc.inch(board_thick)),
                App.Vector(0, lc.inch(cut_position), -lc.inch(board_thick)),
            ]

    try:
        cut_wire = Part.makePolygon(cut_points)
        cut_face = Part.Face(cut_wire)
        cut_shape = cut_face.extrude(App.Vector(0, 0, lc.inch(board_thick * 3)))
        return shape.cut(cut_shape)
    except Exception:
        # If cut fails, return original shape
        return shape


# ============================================================
# BOARD SEGMENT CALCULATION (for realistic board lengths)
# ============================================================


def _calculate_board_segments(
    total_length,
    max_length,
    board_width,
    joist_spacing=16.0,
    first_joist_offset=None,
    joist_thick=1.5,
):
    """
    Calculate board segment positions for a long edge that needs multiple boards.

    When a board length exceeds max_length, split into multiple segments.
    If joist alignment is provided (first_joist_offset not None), splices land on joists.
    Otherwise, short board (remainder) is placed in the MIDDLE per user requirement.

    Args:
        total_length: Total length to cover (inches)
        max_length: Maximum board length (inches), e.g., 192" for 16'
        board_width: Board width (for miter calculations)
        joist_spacing: Joist spacing on-center (inches), default 16"
        first_joist_offset: Distance from board start (position 0) to first joist center.
                           If None, uses legacy center-split algorithm.
        joist_thick: Joist thickness for splice calculations (default 1.5" for 2x)

    Returns:
        List of (start_pos, length, has_miter_start, has_miter_end) tuples
        where positions are relative to the edge (0 = start of edge)
    """
    if total_length <= max_length:
        # Single board covers entire length
        return [(0.0, total_length, True, True)]

    # ========================================
    # JOIST-ALIGNED SEGMENTATION
    # ========================================
    if first_joist_offset is not None:
        # Calculate joist positions
        joist_positions = []
        pos = first_joist_offset
        while pos < total_length:
            joist_positions.append(pos)
            pos += joist_spacing

        # Find splice points - the farthest joist within max_length from current position
        segments = []
        current_pos = 0.0

        while current_pos < total_length - LENGTH_TOLERANCE_IN:
            is_first = current_pos < 0.1
            remaining = total_length - current_pos

            if remaining <= max_length:
                # Final segment to the end
                is_last = True
                segments.append((current_pos, remaining, is_first, is_last))
                break

            # Find farthest joist within max_length from current_pos
            # Board ends at joist_center + joist_thick/4 (covering >= half joist)
            best_splice_pos = None
            for joist_pos in joist_positions:
                splice_pos = joist_pos + joist_thick / 4.0  # Board end covers half joist
                if splice_pos <= current_pos + 0.1:
                    continue  # Must be after current position
                board_length = splice_pos - current_pos
                if board_length > max_length:
                    break  # Past max length
                # Check we're not creating a tiny end piece
                remaining_after = total_length - splice_pos
                if remaining_after > 0 and remaining_after < board_width * 2:
                    continue  # Would leave tiny stub
                best_splice_pos = splice_pos

            if best_splice_pos is None:
                # No valid joist found - just go to end
                is_last = True
                segments.append((current_pos, remaining, is_first, is_last))
                break

            # Create segment ending at best splice position
            seg_length = best_splice_pos - current_pos
            is_last = False
            segments.append((current_pos, seg_length, is_first, is_last))
            current_pos = best_splice_pos

        return segments

    # ========================================
    # LEGACY CENTER-SPLIT ALGORITHM
    # ========================================
    # Calculate number of boards needed
    # Reserve board_width at each end for miter cuts
    inner_length = total_length - (2 * board_width)
    num_full_boards = int(inner_length // max_length) + 1  # Minimum boards needed

    # Calculate segment lengths
    if num_full_boards <= 1:
        # Just one board with miters
        return [(0.0, total_length, True, True)]

    # Distribute length across boards
    # Two end boards get miters, middle boards are straight cut
    segments = []

    # Strategy: equal-length end boards, remainder in middle
    # For 3+ boards: [end_board] [middle_boards...] [end_board]
    # End boards include miter area

    if num_full_boards == 2:
        # Two boards: split evenly
        half_length = total_length / 2.0
        segments.append((0.0, half_length, True, False))
        segments.append((half_length, half_length, False, True))
    else:
        # 3+ boards: maximize end boards, short board in middle
        # End boards: as long as possible (up to max_length)
        # Remaining length divided among middle boards

        remaining = total_length
        num_middle = num_full_boards - 2

        # Each end board can be at most max_length
        # Try to make ends equal and as long as possible
        end_length = min(max_length, (total_length - num_middle) / 2.0)

        # If ends would leave too much for middle, recalculate
        middle_total = total_length - (2 * end_length)
        if num_middle > 0 and middle_total / num_middle > max_length:
            # Need more middle boards
            num_middle = int(middle_total // max_length) + 1
            end_length = (total_length - (num_middle * max_length)) / 2.0
            if end_length < board_width * 2:
                # Ends too short, redistribute
                end_length = max_length
                middle_total = total_length - (2 * end_length)
                num_middle = max(1, int(middle_total // max_length) + 1)

        # First end board (with start miter)
        segments.append((0.0, end_length, True, False))

        # Middle boards (no miters, short one in the middle)
        if num_middle > 0:
            middle_total = total_length - (2 * end_length)
            base_middle_length = middle_total / num_middle
            current_pos = end_length

            for i in range(num_middle):
                seg_length = base_middle_length
                segments.append((current_pos, seg_length, False, False))
                current_pos += seg_length

        # Last end board (with end miter)
        last_start = total_length - end_length
        segments.append((last_start, end_length, False, True))

    return segments


def _create_segmented_edge_boards(
    doc,
    deck_row,
    deck_label,
    total_length,
    deck_width,
    deck_thick,
    board_z,
    start_x,
    start_y,
    base_name,
    supplier,
    miter_start_type,
    miter_end_type,
    edge_axis,
    edge_position,
    first_joist_offset=None,
    joist_spacing=16.0,
    joist_thick=1.5,
):
    """
    Create edge boards with realistic lengths, splitting long edges into segments.

    For edges longer than MAX_DECK_BOARD_LENGTH_IN, creates multiple boards.
    If joist alignment is provided, splices land on joists.
    Otherwise, short board is placed in the middle.

    Args:
        doc: FreeCAD document
        deck_row: Catalog row for deck boards
        deck_label: Catalog label
        total_length: Total edge length (inches)
        deck_width: Board width (5.5" for 5/4x6)
        deck_thick: Board thickness
        board_z: Z position
        start_x, start_y: Starting position of edge
        base_name: Base name for parts (e.g., "PictureFrame_Front")
        supplier: Supplier for BOM
        miter_start_type: Miter type at start ("left", "front", etc.)
        miter_end_type: Miter type at end ("right", "back", etc.)
        edge_axis: "X" or "Y" - direction edge runs
        edge_position: "front", "back", "left", or "right"
        first_joist_offset: Distance from edge start to first joist center (inches).
                           If None, uses legacy center-split algorithm.
        joist_spacing: Joist spacing on-center (inches), default 16"
        joist_thick: Joist thickness for splice calculations (default 1.5")

    Returns:
        List of edge board objects
    """
    boards = []

    # Calculate segments for this edge (with optional joist alignment)
    segments = _calculate_board_segments(
        total_length,
        MAX_DECK_BOARD_LENGTH_IN,
        deck_width,
        joist_spacing=joist_spacing,
        first_joist_offset=first_joist_offset,
        joist_thick=joist_thick,
    )

    for idx, (seg_start, seg_length, has_miter_start, has_miter_end) in enumerate(segments):
        # Determine miter settings for this segment
        seg_miter_start = miter_start_type if has_miter_start else None
        seg_miter_end = miter_end_type if has_miter_end else None

        # Calculate position for this segment
        if edge_axis == "X":
            seg_x = start_x + seg_start
            seg_y = start_y
        else:  # edge_axis == "Y"
            seg_x = start_x
            seg_y = start_y + seg_start

        # Create segment name
        if len(segments) == 1:
            seg_name = base_name
        else:
            seg_name = f"{base_name}_{idx + 1}"

        # Create the board segment
        if seg_miter_start or seg_miter_end:
            board = _make_mitered_edge_board(
                doc,
                deck_row,
                deck_label,
                edge_length_in=seg_length,
                deck_width=deck_width,
                deck_thick=deck_thick,
                board_z=board_z,
                x_pos=seg_x,
                y_pos=seg_y,
                name=seg_name,
                supplier=supplier,
                miter_start=seg_miter_start,
                miter_end=seg_miter_end,
                edge_axis=edge_axis,
                edge_position=edge_position,
            )
        else:
            # No miters - simple rectangular board
            if edge_axis == "X":
                board = doc.addObject("Part::Feature", seg_name)
                board.Shape = Part.makeBox(
                    lc.inch(seg_length), lc.inch(deck_width), lc.inch(deck_thick)
                )
                board.Placement.Base = App.Vector(lc.inch(seg_x), lc.inch(seg_y), lc.inch(board_z))
            else:
                board = doc.addObject("Part::Feature", seg_name)
                board.Shape = Part.makeBox(
                    lc.inch(deck_width), lc.inch(seg_length), lc.inch(deck_thick)
                )
                board.Placement.Base = App.Vector(lc.inch(seg_x), lc.inch(seg_y), lc.inch(board_z))
            lc.attach_metadata(board, deck_row, deck_label, supplier=supplier)

        boards.append(board)

    return boards


# ============================================================
# UNIFIED DECK SURFACE WITH PICTURE FRAME
# ============================================================


def create_unified_deck_surface(
    doc,
    catalog_rows,
    perimeter,
    zones,
    assembly_name="Unified_Deck_Surface",
    z_base=0.0,
    supplier="lowes",
    joist_depth_in=11.25,
    picture_frame_ew_joist_offset=None,
    picture_frame_ns_joist_offset=None,
):
    """
    Create a unified deck surface with picture frame edge boards.

    This function builds the entire deck surface as one module, with:
    - Picture frame edge boards around the outer perimeter (with mitered corners)
    - Field boards that run perpendicular to joists in each zone
    - Seam boards where board direction changes or boards splice

    Args:
        doc: FreeCAD document
        catalog_rows: Catalog data (list of dicts)
        perimeter: Dict defining the outer deck perimeter:
            {
                "x_min_in": float,  # West edge (inches)
                "x_max_in": float,  # East edge (inches)
                "y_min_in": float,  # South edge (inches)
                "y_max_in": float,  # North edge (inches)
            }
        zones: List of dicts defining board zones (areas with same joist orientation):
            [
                {
                    "name": str,           # Zone identifier
                    "x_min_in": float,     # Zone west edge
                    "x_max_in": float,     # Zone east edge
                    "y_min_in": float,     # Zone south edge
                    "y_max_in": float,     # Zone north edge
                    "joist_direction": str,  # "NS" or "EW" (direction joists run)
                    "seam_positions_in": list,  # Optional seam positions
                },
                ...
            ]
        assembly_name: Name for the assembly
        z_base: Z offset in inches
        supplier: Supplier preference
        joist_depth_in: Joist depth for Z positioning (default 11.25" for 2x12)
        picture_frame_ew_joist_offset: Distance from frame start to first joist for
                                       EW picture frame boards (front/back edges).
                                       If None, uses legacy center-split algorithm.
        picture_frame_ns_joist_offset: Distance from frame start to first joist for
                                       NS picture frame boards (left/right edges).
                                       If None, uses legacy center-split algorithm.

    Returns:
        App::Part assembly containing picture frame and field boards
    """
    # Find deck board stock
    deck_label = DECK_BOARD_LABEL  # 12' boards
    deck_row = lc.find_stock(catalog_rows, deck_label)
    if not deck_row:
        raise ValueError(f"Deck board label '{deck_label}' not found in catalog.")

    # Dimensions from catalog
    deck_thick = float(deck_row["actual_thickness_in"])
    deck_width = float(deck_row["actual_width_in"])  # 5.5" for 5/4x6
    deck_gap = DECK_BOARD_GAP_IN

    # Board Z position (top of joists)
    board_z = joist_depth_in

    # Extract perimeter dimensions
    x_min = perimeter["x_min_in"]
    x_max = perimeter["x_max_in"]
    y_min = perimeter["y_min_in"]
    y_max = perimeter["y_max_in"]

    # Picture frame extends beyond framing by overhang
    frame_x_min = x_min - DECK_OVERHANG_IN
    frame_x_max = x_max + DECK_OVERHANG_IN
    frame_y_min = y_min - DECK_OVERHANG_IN
    frame_y_max = y_max + DECK_OVERHANG_IN

    created = []
    edge_boards = []

    # ============================================================
    # STEP 1: Create picture frame edge boards with mitered corners
    # ============================================================
    # Uses segmented boards for realistic lengths (max 16' per board)
    # Short boards are placed in the middle when multiple boards needed

    # Front edge (runs EW along south side)
    # Mitered at both corners (SW and SE)
    # EW boards land on NS joists at X positions
    front_length = frame_x_max - frame_x_min
    front_boards = _create_segmented_edge_boards(
        doc,
        deck_row,
        deck_label,
        total_length=front_length,
        deck_width=deck_width,
        deck_thick=deck_thick,
        board_z=board_z,
        start_x=frame_x_min,
        start_y=frame_y_min,
        base_name="PictureFrame_Front",
        supplier=supplier,
        miter_start_type="left",
        miter_end_type="right",
        edge_axis="X",
        edge_position="front",
        first_joist_offset=picture_frame_ew_joist_offset,
    )
    edge_boards.extend(front_boards)

    # Back edge (runs EW along north side)
    # Mitered at both corners (NW and NE)
    back_length = frame_x_max - frame_x_min
    back_boards = _create_segmented_edge_boards(
        doc,
        deck_row,
        deck_label,
        total_length=back_length,
        deck_width=deck_width,
        deck_thick=deck_thick,
        board_z=board_z,
        start_x=frame_x_min,
        start_y=frame_y_max - deck_width,
        base_name="PictureFrame_Back",
        supplier=supplier,
        miter_start_type="left",
        miter_end_type="right",
        edge_axis="X",
        edge_position="back",
        first_joist_offset=picture_frame_ew_joist_offset,
    )
    edge_boards.extend(back_boards)

    # Left edge (runs NS along west side)
    # Full length with mitered corners at SW and NW
    # NS boards land on EW joists at Y positions
    left_length = frame_y_max - frame_y_min
    left_boards = _create_segmented_edge_boards(
        doc,
        deck_row,
        deck_label,
        total_length=left_length,
        deck_width=deck_width,
        deck_thick=deck_thick,
        board_z=board_z,
        start_x=frame_x_min,
        start_y=frame_y_min,
        base_name="PictureFrame_Left",
        supplier=supplier,
        miter_start_type="front",
        miter_end_type="back",
        edge_axis="Y",
        edge_position="left",
        first_joist_offset=picture_frame_ns_joist_offset,
    )
    edge_boards.extend(left_boards)

    # Right edge (runs NS along east side)
    right_length = frame_y_max - frame_y_min
    right_boards = _create_segmented_edge_boards(
        doc,
        deck_row,
        deck_label,
        total_length=right_length,
        deck_width=deck_width,
        deck_thick=deck_thick,
        board_z=board_z,
        start_x=frame_x_max - deck_width,
        start_y=frame_y_min,
        base_name="PictureFrame_Right",
        supplier=supplier,
        miter_start_type="front",
        miter_end_type="back",
        edge_axis="Y",
        edge_position="right",
        first_joist_offset=picture_frame_ns_joist_offset,
    )
    edge_boards.extend(right_boards)

    created.extend(edge_boards)

    # ============================================================
    # STEP 2: Create seam boards and field boards in each zone
    # ============================================================
    # Order: Picture frame (step 1) -> Seam boards (step 2a) -> Field boards (step 2b)
    # Seam boards are placed at splice positions perpendicular to field boards
    # All board ends are supported - no floating ends allowed

    field_boards = []
    seam_boards = []
    all_blocking = []
    for zone in zones:
        zone_name = zone.get("name", "Zone")
        zone_x_min = zone["x_min_in"]
        zone_x_max = zone["x_max_in"]
        zone_y_min = zone["y_min_in"]
        zone_y_max = zone["y_max_in"]
        joist_dir = zone.get("joist_direction", "NS")
        seam_positions = zone.get("seam_positions_in", [])

        # Boards run perpendicular to joists
        if joist_dir == "NS":
            # Joists run NS, boards run EW
            board_direction = "EW"
        else:
            # Joists run EW, boards run NS
            board_direction = "NS"

        # Account for picture frame edges
        # Field boards start after edge boards
        if zone_x_min <= frame_x_min + deck_width:
            field_x_min = frame_x_min + deck_width + deck_gap
        else:
            field_x_min = zone_x_min

        if zone_x_max >= frame_x_max - deck_width:
            field_x_max = frame_x_max - deck_width - deck_gap
        else:
            field_x_max = zone_x_max

        if zone_y_min <= frame_y_min + deck_width:
            field_y_min = frame_y_min + deck_width + deck_gap
        else:
            field_y_min = zone_y_min

        if zone_y_max >= frame_y_max - deck_width:
            field_y_max = frame_y_max - deck_width - deck_gap
        else:
            field_y_max = zone_y_max

        # Get layout direction for NS boards (default left_to_right)
        ns_layout_dir = zone.get("ns_layout_direction", "left_to_right")

        # Get first joist offset for seam alignment
        # This is the distance from field board start to the first joist center
        # For front deck (EW boards), joists run NS at X positions:
        #   - Left rim center: module_origin_x + 0.75"
        #   - Interior joists: module_origin_x + 15.25", then 16" O.C.
        # For side decks (NS boards), joists run EW at Y positions (same pattern)
        #
        # If not specified, defaults to joist_thick/2 (0.75")
        first_joist_offset = zone.get("first_joist_offset_in", None)

        # Create field boards, seam boards, and blocking for this zone
        zone_field_boards, zone_seam_boards, zone_blocking = _create_zone_field_boards(
            doc,
            deck_row,
            deck_label,
            field_x_min,
            field_x_max,
            field_y_min,
            field_y_max,
            board_direction,
            board_z,
            deck_width,
            deck_thick,
            deck_gap,
            supplier,
            zone_name,
            seam_positions,
            ns_layout_direction=ns_layout_dir,
            catalog_rows=catalog_rows,
            joist_thick=1.5,  # 2x lumber
            joist_depth=joist_depth_in,
            first_joist_offset=first_joist_offset,
        )
        field_boards.extend(zone_field_boards)
        seam_boards.extend(zone_seam_boards)
        all_blocking.extend(zone_blocking)

    # Add boards to created list in construction order (for design visualization):
    # 1. Picture frame (already added above)
    # 2. Seam boards (perpendicular splice boards)
    # 3. Field boards (main deck surface)
    # 4. Blocking (underneath, placed last for design purposes)
    created.extend(seam_boards)
    created.extend(field_boards)
    created.extend(all_blocking)

    # Create assembly
    App.Console.PrintMessage(
        f"[deck_assemblies] Created unified deck surface: {assembly_name} (type: App::Part)\n"
    )
    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    for obj in created:
        assembly.addObject(obj)

    # Apply Z offset
    assembly.Placement.Base = App.Vector(0, 0, lc.inch(z_base))

    doc.recompute()

    App.Console.PrintMessage(
        f"[deck_assemblies] ✓ Unified deck surface complete: {assembly_name} "
        f"({len(edge_boards)} frame boards, {len(seam_boards)} seam boards, "
        f"{len(field_boards)} field boards, {len(all_blocking)} blocking)\n"
    )

    return assembly


def _create_zone_field_boards(
    doc,
    deck_row,
    deck_label,
    x_min,
    x_max,
    y_min,
    y_max,
    board_direction,
    board_z,
    deck_width,
    deck_thick,
    deck_gap,
    supplier,
    zone_name,
    seam_positions,
    ns_layout_direction="left_to_right",
    joist_spacing=JOIST_SPACING_OC_IN,
    catalog_rows=None,
    joist_thick=1.5,
    joist_depth=11.25,
    first_joist_offset=None,
):
    """
    Create field boards for a zone within the deck surface.

    Real-world construction workflow:
    1. Picture frame is installed first (done in parent function)
    2. Lay full-length field boards (16'), starting from picture frame
    3. Trim field boards over a joist (chalk line), leaving >= half joist covered
    4. Place perpendicular seam board starting at the trim line
    5. Seam board spans to a second joist (double-joist at each seam)
    6. Continue with next set of field boards from the second joist

    Args:
        doc: FreeCAD document
        deck_row: Catalog row for deck boards
        deck_label: Catalog label
        x_min, x_max, y_min, y_max: Zone boundaries (inches)
        board_direction: "EW" or "NS"
        board_z: Z position for boards
        deck_width, deck_thick, deck_gap: Board dimensions
        supplier: Supplier for BOM
        zone_name: Zone name for part naming
        seam_positions: List of positions for seam boards (legacy, ignored - now auto-calculated)
        ns_layout_direction: For NS boards, which direction to lay out:
            - "left_to_right": Start from x_min (west), rip at x_max (east)
            - "right_to_left": Start from x_max (east), rip at x_min (west)
        joist_spacing: Joist spacing on-center (inches)
        catalog_rows: Catalog data for finding blocking lumber
        joist_thick: Joist thickness (1.5" for 2x lumber)
        joist_depth: Joist depth (11.25" for 2x12)
        first_joist_offset: Distance from field board start to first joist center (inches).
                           If None, defaults to joist_thick/2 (0.75" for 2x lumber).
                           This aligns board splices with actual joist positions.

    Returns:
        Tuple of (field_boards, seam_boards, blocking) lists
    """
    field_boards = []
    seam_boards = []
    blocking = []
    board_count = 0
    seam_count = 0
    step = deck_width + deck_gap

    if board_direction == "EW":
        # Boards run E-W (X direction), laid out along Y
        # Seam boards run N-S (perpendicular to field boards)
        total_board_length = x_max - x_min
        zone_depth = y_max - y_min

        # Calculate seam zones using new algorithm
        seam_zones = _calculate_seam_zones(
            total_board_length,
            MAX_DECK_BOARD_LENGTH_IN,
            joist_spacing,
            joist_thick=joist_thick,
            seam_board_width=deck_width,
            first_joist_offset=first_joist_offset,
        )

        # Create seam boards first (they run perpendicular, N-S)
        # Also create sister joists at joist2_center for each seam (double-joist support)
        for segment in seam_zones:
            if segment["type"] == "seam":
                seam_count += 1
                seam_name = f"{zone_name}_Seam_{seam_count}"
                seam = doc.addObject("Part::Feature", seam_name)

                # Seam board position (runs N-S at this X position)
                seam_x = x_min + segment["start"]
                seam_length = segment["end"] - segment["start"]

                seam.Shape = Part.makeBox(
                    lc.inch(seam_length), lc.inch(zone_depth), lc.inch(deck_thick)
                )
                seam.Placement.Base = App.Vector(lc.inch(seam_x), lc.inch(y_min), lc.inch(board_z))
                lc.attach_metadata(seam, deck_row, deck_label, supplier=supplier)
                seam_boards.append(seam)

                # Create sister joist at joist2_center (runs NS like regular joists)
                # This is the second joist of the double-joist pair supporting the seam board
                # Sister joist fits INSIDE the rim joists, same as interior joists
                if catalog_rows is not None and "joist2_center" in segment:
                    joist2_x = x_min + segment["joist2_center"]
                    sister_joist_z = board_z - joist_depth  # Below deck boards

                    # Sister joist runs inside the rims (like interior joists)
                    # Zone includes rim faces, so joist runs from y_min + rim_thick to y_max - rim_thick
                    rim_thick = joist_thick  # Rims use same 2x lumber thickness
                    sister_joist_length = (
                        zone_depth - 2 * rim_thick
                    )  # Fit between front and back rims
                    sister_joist_y_start = y_min + rim_thick  # Start inside front rim

                    # Find joist stock (2x12 for deck joists, match sister joist length)
                    for try_length in [144, 96, 192, 48]:
                        try_label = f"2x12x{try_length}_PT"
                        joist_row = lc.find_stock(catalog_rows, try_label)
                        if joist_row and float(joist_row["length_in"]) >= sister_joist_length:
                            break
                    else:
                        joist_row = None

                    if joist_row:
                        sister_name = f"{zone_name}_SisterJoist_{seam_count}"
                        sister = doc.addObject("Part::Feature", sister_name)
                        # Joist: thickness (X) × length (Y) × depth (Z)
                        sister.Shape = Part.makeBox(
                            lc.inch(joist_thick), lc.inch(sister_joist_length), lc.inch(joist_depth)
                        )
                        # Position at joist2 center (X centered on joist), inside rims
                        sister.Placement.Base = App.Vector(
                            lc.inch(joist2_x - joist_thick / 2.0),
                            lc.inch(sister_joist_y_start),
                            lc.inch(sister_joist_z),
                        )
                        lc.attach_metadata(sister, joist_row, try_label, supplier=supplier)
                        blocking.append(sister)

        # Create field boards for each field segment
        y_pos = y_min
        while y_pos < y_max - 0.1:
            remaining_width = y_max - y_pos
            actual_width = min(deck_width, remaining_width)

            if actual_width < 0.25:
                break

            board_count += 1
            is_rip = actual_width < deck_width - 0.1

            # Create board segments for each field zone
            seg_idx = 0
            for segment in seam_zones:
                if segment["type"] == "field":
                    seg_idx += 1
                    seg_start = segment["start"]
                    seg_end = segment["end"]
                    seg_length = seg_end - seg_start

                    if seg_length < 0.25:
                        continue

                    num_field_segments = sum(1 for s in seam_zones if s["type"] == "field")
                    if num_field_segments == 1:
                        seg_name = f"{zone_name}_EW_{board_count}" + ("_RIP" if is_rip else "")
                    else:
                        seg_name = f"{zone_name}_EW_{board_count}_{seg_idx}" + (
                            "_RIP" if is_rip else ""
                        )

                    board = doc.addObject("Part::Feature", seg_name)
                    board.Shape = Part.makeBox(
                        lc.inch(seg_length), lc.inch(actual_width), lc.inch(deck_thick)
                    )
                    board.Placement.Base = App.Vector(
                        lc.inch(x_min + seg_start), lc.inch(y_pos), lc.inch(board_z)
                    )
                    lc.attach_metadata(board, deck_row, deck_label, supplier=supplier)
                    field_boards.append(board)

            y_pos += step

    else:
        # Boards run N-S (Y direction), laid out along X
        # Seam boards run E-W (perpendicular to field boards)
        total_board_length = y_max - y_min
        zone_width = x_max - x_min

        # Calculate seam zones using new algorithm
        seam_zones = _calculate_seam_zones(
            total_board_length,
            MAX_DECK_BOARD_LENGTH_IN,
            joist_spacing,
            joist_thick=joist_thick,
            seam_board_width=deck_width,
            first_joist_offset=first_joist_offset,
        )

        # Create seam boards first (they run perpendicular, E-W)
        # Also create sister joists at joist2_center for each seam (double-joist support)
        for segment in seam_zones:
            if segment["type"] == "seam":
                seam_count += 1
                seam_name = f"{zone_name}_Seam_{seam_count}"
                seam = doc.addObject("Part::Feature", seam_name)

                # Seam board position (runs E-W at this Y position)
                seam_y = y_min + segment["start"]
                seam_length = segment["end"] - segment["start"]

                seam.Shape = Part.makeBox(
                    lc.inch(zone_width), lc.inch(seam_length), lc.inch(deck_thick)
                )
                seam.Placement.Base = App.Vector(lc.inch(x_min), lc.inch(seam_y), lc.inch(board_z))
                lc.attach_metadata(seam, deck_row, deck_label, supplier=supplier)
                seam_boards.append(seam)

                # Create sister joist at joist2_center (runs EW like floor joists)
                # This is the second joist of the double-joist pair supporting the seam board
                if catalog_rows is not None and "joist2_center" in segment:
                    joist2_y = y_min + segment["joist2_center"]
                    sister_joist_z = board_z - joist_depth  # Below deck boards

                    # Find joist stock (2x12 for joists, match zone width)
                    for try_length in [144, 96, 192, 48]:
                        try_label = f"2x12x{try_length}_PT"
                        joist_row = lc.find_stock(catalog_rows, try_label)
                        if joist_row and float(joist_row["length_in"]) >= zone_width:
                            break
                    else:
                        joist_row = None

                    if joist_row:
                        sister_name = f"{zone_name}_SisterJoist_{seam_count}"
                        sister = doc.addObject("Part::Feature", sister_name)
                        # Joist runs EW: length (X) × thickness (Y) × depth (Z)
                        sister.Shape = Part.makeBox(
                            lc.inch(zone_width), lc.inch(joist_thick), lc.inch(joist_depth)
                        )
                        # Position at joist2 center (Y centered on joist)
                        sister.Placement.Base = App.Vector(
                            lc.inch(x_min),
                            lc.inch(joist2_y - joist_thick / 2.0),
                            lc.inch(sister_joist_z),
                        )
                        lc.attach_metadata(sister, joist_row, try_label, supplier=supplier)
                        blocking.append(sister)

        # Create field boards based on layout direction
        if ns_layout_direction == "right_to_left":
            # Start from east (x_max) and work toward west (x_min)
            x_pos = x_max - deck_width

            while x_pos > x_min - deck_width + 0.1:
                if x_pos < x_min:
                    actual_width = deck_width - (x_min - x_pos)
                    actual_x_pos = x_min
                else:
                    actual_width = deck_width
                    actual_x_pos = x_pos

                if actual_width < 0.25:
                    break

                board_count += 1
                is_rip = actual_width < deck_width - 0.1

                # Create board segments for each field zone
                seg_idx = 0
                for segment in seam_zones:
                    if segment["type"] == "field":
                        seg_idx += 1
                        seg_start = segment["start"]
                        seg_end = segment["end"]
                        seg_length = seg_end - seg_start

                        if seg_length < 0.25:
                            continue

                        num_field_segments = sum(1 for s in seam_zones if s["type"] == "field")
                        if num_field_segments == 1:
                            seg_name = f"{zone_name}_NS_{board_count}" + ("_RIP" if is_rip else "")
                        else:
                            seg_name = f"{zone_name}_NS_{board_count}_{seg_idx}" + (
                                "_RIP" if is_rip else ""
                            )

                        board = doc.addObject("Part::Feature", seg_name)
                        board.Shape = Part.makeBox(
                            lc.inch(actual_width), lc.inch(seg_length), lc.inch(deck_thick)
                        )
                        board.Placement.Base = App.Vector(
                            lc.inch(actual_x_pos), lc.inch(y_min + seg_start), lc.inch(board_z)
                        )
                        lc.attach_metadata(board, deck_row, deck_label, supplier=supplier)
                        field_boards.append(board)

                x_pos -= step
        else:
            # Default: left_to_right
            x_pos = x_min

            while x_pos < x_max - 0.1:
                remaining_width = x_max - x_pos
                actual_width = min(deck_width, remaining_width)

                if actual_width < 0.25:
                    break

                board_count += 1
                is_rip = actual_width < deck_width - 0.1

                # Create board segments for each field zone
                seg_idx = 0
                for segment in seam_zones:
                    if segment["type"] == "field":
                        seg_idx += 1
                        seg_start = segment["start"]
                        seg_end = segment["end"]
                        seg_length = seg_end - seg_start

                        if seg_length < 0.25:
                            continue

                        num_field_segments = sum(1 for s in seam_zones if s["type"] == "field")
                        if num_field_segments == 1:
                            seg_name = f"{zone_name}_NS_{board_count}" + ("_RIP" if is_rip else "")
                        else:
                            seg_name = f"{zone_name}_NS_{board_count}_{seg_idx}" + (
                                "_RIP" if is_rip else ""
                            )

                        board = doc.addObject("Part::Feature", seg_name)
                        board.Shape = Part.makeBox(
                            lc.inch(actual_width), lc.inch(seg_length), lc.inch(deck_thick)
                        )
                        board.Placement.Base = App.Vector(
                            lc.inch(x_pos), lc.inch(y_min + seg_start), lc.inch(board_z)
                        )
                        lc.attach_metadata(board, deck_row, deck_label, supplier=supplier)
                        field_boards.append(board)

                x_pos += step

    return (field_boards, seam_boards, blocking)


# ============================================================
# FLEXIBLE DECK SURFACE FUNCTION
# ============================================================


def create_deck_surface(
    doc,
    catalog_rows,
    width_ft=16.0,
    depth_ft=8.0,
    assembly_name="Deck_Surface",
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    supplier="lowes",
    board_direction="EW",
    include_front_edge=False,
    include_back_edge=False,
    include_left_edge=False,
    include_right_edge=False,
    joist_depth_in=11.25,
    seam_positions_in=None,
    joist_spacing_in=16.0,
    ns_layout_direction="left_to_right",
    miter_corners=False,
    post_positions=None,
    include_blocking=False,
):
    """
    Create a deck surface assembly of any size with configurable board direction.

    This is the main deck surface function - all specific size functions should
    call this one with appropriate parameters.

    Board Direction:
        - "EW": Boards run East-West (X direction) - for front/rear decks
                Joists run N-S, boards perpendicular to joists
        - "NS": Boards run North-South (Y direction) - for side decks
                Joists run E-W, boards perpendicular to joists

    Edge Boards (picture frame):
        - Edge boards run perpendicular to main boards
        - For EW boards: left/right edges run N-S
        - For NS boards: front/back edges run E-W
        - With miter_corners=True, edges get 45-degree cuts at corners

    Seam Boards (seam_positions_in):
        - Perpendicular boards at specified positions (in inches from start)
        - Main boards are cut to fit between seam boards
        - Provides visual break and eliminates butt joints
        - For EW boards: seam boards run N-S at X positions
        - For NS boards: seam boards run E-W at Y positions

    Railing Post Support (post_positions):
        - List of (x, y) tuples for railing post locations (in inches from assembly origin)
        - Deck boards will be notched/cut around these positions
        - Posts are built separately before deck surface (railings first)

    Args:
        doc: FreeCAD document
        catalog_rows: Catalog data (list of dicts)
        width_ft: Deck width in feet (X direction)
        depth_ft: Deck depth in feet (Y direction)
        assembly_name: Name for the assembly
        x_base, y_base, z_base: Position offsets (inches)
        supplier: Supplier preference ("lowes" or "hd")
        board_direction: "EW" (east-west) or "NS" (north-south)
        include_front_edge: Include edge board on front (south) side
        include_back_edge: Include edge board on back (north) side
        include_left_edge: Include edge board on left (west) side
        include_right_edge: Include edge board on right (east) side
        joist_depth_in: Joist depth for Z positioning (default 11.25" for 2x12)
        seam_positions_in: List of positions (in inches) for perpendicular seam boards
        joist_spacing_in: Joist spacing (for reference, default 16" OC)
        ns_layout_direction: For NS boards, which direction to lay out:
            - "left_to_right": Start from left (west) edge, rip on right (for LEFT side deck)
            - "right_to_left": Start from right (east) edge, rip on left (for RIGHT side deck)
        miter_corners: If True, edge boards get 45-degree mitered corners
        post_positions: List of (x, y) tuples for railing post locations to cut around
        include_blocking: If True, add blocking under seam boards and edges (future)

    Returns:
        App::Part assembly containing deck boards and edge boards
    """
    # Convert to inches
    width_in = width_ft * 12.0
    depth_in = depth_ft * 12.0

    # Select deck board stock based on dimensions
    # For EW boards, length = width_in; for NS boards, length = depth_in
    if board_direction.upper() == "EW":
        board_run_in = width_in
    else:
        board_run_in = depth_in

    # Select appropriate stock length (round up to nearest standard length)
    # Using 12' (144") as default, 16' (192") for longer runs
    if board_run_in <= 144:
        deck_label = DECK_BOARD_LABEL  # 12' stock
    else:
        deck_label = "deckboard_5_4x6x192_PT"  # 16' stock for longer runs

    # Find stock
    deck_row = lc.find_stock(catalog_rows, deck_label)
    if not deck_row:
        # Fallback to default board length
        deck_label = DECK_BOARD_LABEL
        deck_row = lc.find_stock(catalog_rows, deck_label)
        if not deck_row:
            raise ValueError(f"Deck board label '{deck_label}' not found in catalog.")

    # Dimensions from catalog
    deck_thick = float(deck_row["actual_thickness_in"])
    deck_width = float(deck_row["actual_width_in"])  # 5.5" for 5/4x6
    deck_gap = DECK_BOARD_GAP_IN

    created = []
    boards = []
    edge_boards = []

    # Board Z position (top of joists)
    board_z = joist_depth_in

    # Seam boards list (perpendicular boards at seam positions)
    seam_boards = []

    if board_direction.upper() == "EW":
        # Boards run E-W (X direction), laid out along Y
        # Main boards span from left to right, stepping front to back

        # Calculate board length accounting for edge boards
        board_x_start = deck_width if include_left_edge else 0.0
        usable_width = width_in
        if include_left_edge:
            usable_width -= deck_width
        if include_right_edge:
            usable_width -= deck_width

        # Build list of Y zones (segments between seams in Y direction)
        # Seam boards run E-W (parallel to main boards) at specified Y positions
        # Each zone is (y_start, y_end) in inches, with main boards filling each zone
        y_zones = []
        if seam_positions_in:
            # Sort seam positions (these are Y positions for EW boards)
            seams = sorted([s for s in seam_positions_in if 0 < s < depth_in])
            prev_y = -DECK_OVERHANG_IN  # Start with overhang
            for seam_y in seams:
                # Zone ends at seam_y minus half deck_width (seam board is centered on position)
                zone_end = seam_y - deck_width / 2.0 - deck_gap / 2.0
                if zone_end > prev_y:
                    y_zones.append((prev_y, zone_end))
                prev_y = seam_y + deck_width / 2.0 + deck_gap / 2.0
            # Final zone to end (with overhang)
            if prev_y < depth_in + DECK_OVERHANG_IN:
                y_zones.append((prev_y, depth_in + DECK_OVERHANG_IN))

            # Create seam boards (run E-W at each seam Y position)
            # Seam boards span the full width (including left/right edge board areas)
            seam_length = width_in  # Full deck width
            for seam_y in seams:
                seam_board = doc.addObject("Part::Feature", f"Seam_{len(seam_boards)+1}")
                seam_board.Shape = Part.makeBox(
                    lc.inch(seam_length), lc.inch(deck_width), lc.inch(deck_thick)
                )
                seam_board.Placement.Base = App.Vector(
                    0, lc.inch(seam_y - deck_width / 2.0), lc.inch(board_z)
                )
                lc.attach_metadata(seam_board, deck_row, deck_label, supplier=supplier)
                seam_boards.append(seam_board)
        else:
            # No seams - single zone spanning full depth (with overhangs)
            y_zones = [(-DECK_OVERHANG_IN, depth_in + DECK_OVERHANG_IN)]

        # Layout boards in each Y zone
        board_count = 0
        for zone_y_start, zone_y_end in y_zones:
            step = deck_width + deck_gap
            y_pos = zone_y_start

            while y_pos < zone_y_end - 0.1:
                board_length = min(deck_width, zone_y_end - y_pos)
                if board_length < 0.25:
                    break

                board_count += 1
                if board_length < deck_width - 0.1:
                    # Ripped board at zone end
                    board = doc.addObject("Part::Feature", f"Deck_{board_count}_RIP")
                else:
                    board = doc.addObject("Part::Feature", f"Deck_{board_count}")

                board.Shape = Part.makeBox(
                    lc.inch(usable_width), lc.inch(board_length), lc.inch(deck_thick)
                )
                board.Placement.Base = App.Vector(
                    lc.inch(board_x_start), lc.inch(y_pos), lc.inch(board_z)
                )
                lc.attach_metadata(board, deck_row, deck_label, supplier=supplier)
                boards.append(board)
                y_pos += step

        # Edge boards for EW direction run N-S (along Y)
        edge_length = depth_in + 2 * DECK_OVERHANG_IN  # Extends overhang each direction

        if include_left_edge:
            # Left edge board runs N-S at west side
            # Miter at front (south) if front_edge exists, at back (north) if back_edge exists
            miter_start = "front" if (miter_corners and include_front_edge) else None
            miter_end = "back" if (miter_corners and include_back_edge) else None

            if miter_corners and (miter_start or miter_end):
                left_edge = _make_mitered_edge_board(
                    doc,
                    deck_row,
                    deck_label,
                    edge_length_in=edge_length,
                    deck_width=deck_width,
                    deck_thick=deck_thick,
                    board_z=board_z,
                    x_pos=0,
                    y_pos=-DECK_OVERHANG_IN,
                    name="Edge_Left",
                    supplier=supplier,
                    miter_start=miter_start,
                    miter_end=miter_end,
                    edge_axis="Y",
                )
            else:
                left_edge = doc.addObject("Part::Feature", "Edge_Left")
                left_edge.Shape = Part.makeBox(
                    lc.inch(deck_width), lc.inch(edge_length), lc.inch(deck_thick)
                )
                left_edge.Placement.Base = App.Vector(
                    0, lc.inch(-DECK_OVERHANG_IN), lc.inch(board_z)
                )
                lc.attach_metadata(left_edge, deck_row, deck_label, supplier=supplier)
            edge_boards.append(left_edge)

        if include_right_edge:
            # Right edge board runs N-S at east side
            # Miter at front (south) if front_edge exists, at back (north) if back_edge exists
            miter_start = "front" if (miter_corners and include_front_edge) else None
            miter_end = "back" if (miter_corners and include_back_edge) else None

            if miter_corners and (miter_start or miter_end):
                right_edge = _make_mitered_edge_board(
                    doc,
                    deck_row,
                    deck_label,
                    edge_length_in=edge_length,
                    deck_width=deck_width,
                    deck_thick=deck_thick,
                    board_z=board_z,
                    x_pos=width_in - deck_width,
                    y_pos=-DECK_OVERHANG_IN,
                    name="Edge_Right",
                    supplier=supplier,
                    miter_start=miter_start,
                    miter_end=miter_end,
                    edge_axis="Y",
                )
            else:
                right_edge = doc.addObject("Part::Feature", "Edge_Right")
                right_edge.Shape = Part.makeBox(
                    lc.inch(deck_width), lc.inch(edge_length), lc.inch(deck_thick)
                )
                right_edge.Placement.Base = App.Vector(
                    lc.inch(width_in - deck_width), lc.inch(-DECK_OVERHANG_IN), lc.inch(board_z)
                )
                lc.attach_metadata(right_edge, deck_row, deck_label, supplier=supplier)
            edge_boards.append(right_edge)

    else:
        # Boards run N-S (Y direction), laid out along X
        # Main boards span from front to back, stepping left to right

        # Calculate board length accounting for edge boards
        board_y_start = deck_width if include_front_edge else 0.0
        board_length = depth_in
        if include_front_edge:
            board_length -= deck_width
        if include_back_edge:
            board_length -= deck_width

        # Layout boards along X
        # Direction determines where full boards start and where rip cut ends up
        step = deck_width + deck_gap
        board_count = 0

        if ns_layout_direction == "right_to_left":
            # Start from RIGHT (outer) edge, work toward LEFT (house)
            # Rip cut ends up on LEFT side (toward house, less visible)
            # If right edge board exists, start after it with a gap
            # Edge board: left edge at width_in + overhang - deck_width
            # First main board: right edge at edge_left - gap
            if include_right_edge:
                # Start after edge board with gap
                x_pos = width_in + DECK_OVERHANG_IN - deck_width - deck_gap - deck_width
            else:
                # No edge board: first full board overhangs
                x_pos = width_in + DECK_OVERHANG_IN - deck_width
            last_full_start = None

            while True:
                if x_pos < 0:
                    # Rip last board to remaining space on left side (NO overhang on house side)
                    rip_end = (
                        last_full_start if last_full_start is not None else x_pos + deck_width
                    ) - deck_gap
                    remaining = rip_end  # From x=0 to last full board
                    if remaining > 0.25:
                        board_count += 1
                        rip = doc.addObject("Part::Feature", f"Deck_{board_count}_RIP")
                        rip.Shape = Part.makeBox(
                            lc.inch(remaining), lc.inch(board_length), lc.inch(deck_thick)
                        )
                        rip.Placement.Base = App.Vector(0, lc.inch(board_y_start), lc.inch(board_z))
                        lc.attach_metadata(rip, deck_row, deck_label, supplier=supplier)
                        boards.append(rip)
                    break

                board_count += 1
                board = doc.addObject("Part::Feature", f"Deck_{board_count}")
                board.Shape = Part.makeBox(
                    lc.inch(deck_width), lc.inch(board_length), lc.inch(deck_thick)
                )
                board.Placement.Base = App.Vector(
                    lc.inch(x_pos), lc.inch(board_y_start), lc.inch(board_z)
                )
                lc.attach_metadata(board, deck_row, deck_label, supplier=supplier)
                boards.append(board)
                last_full_start = x_pos
                x_pos -= step
        else:
            # Default: left_to_right - Start from LEFT (outer) edge, work toward RIGHT (house)
            # Rip cut ends up on RIGHT side (toward house, less visible)
            # If left edge board exists, start after it with a gap
            # Edge board: right edge at -overhang + deck_width
            # First main board: left edge at edge_right + gap
            if include_left_edge:
                # Start after edge board with gap
                x_pos = -DECK_OVERHANG_IN + deck_width + deck_gap
            else:
                # No edge board: first full board overhangs
                x_pos = -DECK_OVERHANG_IN
            last_full_end = None

            while True:
                next_x = x_pos + deck_width
                if next_x > width_in:
                    # Rip last board to remaining space on right side (NO overhang on house side)
                    rip_start = (last_full_end if last_full_end is not None else x_pos) + deck_gap
                    remaining = (
                        width_in - rip_start
                    )  # From last full board to width_in (no overhang)
                    if remaining > 0.25:
                        board_count += 1
                        rip = doc.addObject("Part::Feature", f"Deck_{board_count}_RIP")
                        rip.Shape = Part.makeBox(
                            lc.inch(remaining), lc.inch(board_length), lc.inch(deck_thick)
                        )
                        rip.Placement.Base = App.Vector(
                            lc.inch(rip_start), lc.inch(board_y_start), lc.inch(board_z)
                        )
                        lc.attach_metadata(rip, deck_row, deck_label, supplier=supplier)
                        boards.append(rip)
                    break

                board_count += 1
                board = doc.addObject("Part::Feature", f"Deck_{board_count}")
                board.Shape = Part.makeBox(
                    lc.inch(deck_width), lc.inch(board_length), lc.inch(deck_thick)
                )
                board.Placement.Base = App.Vector(
                    lc.inch(x_pos), lc.inch(board_y_start), lc.inch(board_z)
                )
                lc.attach_metadata(board, deck_row, deck_label, supplier=supplier)
                boards.append(board)
                last_full_end = next_x
                x_pos += step

        # Edge boards for NS direction
        # Front/back edges run E-W (along X), left/right edges run N-S (along Y)

        if include_front_edge:
            # Front edge runs E-W at Y=0
            # Miter at left (west) if left_edge exists, at right (east) if right_edge exists
            edge_length_x = width_in + 2 * DECK_OVERHANG_IN  # Extends overhang each direction
            miter_start = "left" if (miter_corners and include_left_edge) else None
            miter_end = "right" if (miter_corners and include_right_edge) else None

            if miter_corners and (miter_start or miter_end):
                front_edge = _make_mitered_edge_board(
                    doc,
                    deck_row,
                    deck_label,
                    edge_length_in=edge_length_x,
                    deck_width=deck_width,
                    deck_thick=deck_thick,
                    board_z=board_z,
                    x_pos=-DECK_OVERHANG_IN,
                    y_pos=0,
                    name="Edge_Front",
                    supplier=supplier,
                    miter_start=miter_start,
                    miter_end=miter_end,
                    edge_axis="X",
                )
            else:
                front_edge = doc.addObject("Part::Feature", "Edge_Front")
                front_edge.Shape = Part.makeBox(
                    lc.inch(edge_length_x), lc.inch(deck_width), lc.inch(deck_thick)
                )
                front_edge.Placement.Base = App.Vector(
                    lc.inch(-DECK_OVERHANG_IN), 0, lc.inch(board_z)
                )
                lc.attach_metadata(front_edge, deck_row, deck_label, supplier=supplier)
            edge_boards.append(front_edge)

        if include_back_edge:
            # Back edge runs E-W at Y=depth
            # Miter at left (west) if left_edge exists, at right (east) if right_edge exists
            edge_length_x = width_in + 2 * DECK_OVERHANG_IN
            miter_start = "left" if (miter_corners and include_left_edge) else None
            miter_end = "right" if (miter_corners and include_right_edge) else None

            if miter_corners and (miter_start or miter_end):
                back_edge = _make_mitered_edge_board(
                    doc,
                    deck_row,
                    deck_label,
                    edge_length_in=edge_length_x,
                    deck_width=deck_width,
                    deck_thick=deck_thick,
                    board_z=board_z,
                    x_pos=-DECK_OVERHANG_IN,
                    y_pos=depth_in - deck_width,
                    name="Edge_Back",
                    supplier=supplier,
                    miter_start=miter_start,
                    miter_end=miter_end,
                    edge_axis="X",
                )
            else:
                back_edge = doc.addObject("Part::Feature", "Edge_Back")
                back_edge.Shape = Part.makeBox(
                    lc.inch(edge_length_x), lc.inch(deck_width), lc.inch(deck_thick)
                )
                back_edge.Placement.Base = App.Vector(
                    lc.inch(-DECK_OVERHANG_IN), lc.inch(depth_in - deck_width), lc.inch(board_z)
                )
                lc.attach_metadata(back_edge, deck_row, deck_label, supplier=supplier)
            edge_boards.append(back_edge)

        if include_left_edge:
            # Left edge runs N-S (along Y) at X=-overhang (outer edge with overhang)
            # Miter at front (south) if front_edge exists, at back (north) if back_edge exists
            edge_length_y = depth_in + 2 * DECK_OVERHANG_IN  # Extends overhang each direction
            miter_start = "front" if (miter_corners and include_front_edge) else None
            miter_end = "back" if (miter_corners and include_back_edge) else None

            if miter_corners and (miter_start or miter_end):
                left_edge = _make_mitered_edge_board(
                    doc,
                    deck_row,
                    deck_label,
                    edge_length_in=edge_length_y,
                    deck_width=deck_width,
                    deck_thick=deck_thick,
                    board_z=board_z,
                    x_pos=-DECK_OVERHANG_IN,
                    y_pos=-DECK_OVERHANG_IN,
                    name="Edge_Left",
                    supplier=supplier,
                    miter_start=miter_start,
                    miter_end=miter_end,
                    edge_axis="Y",
                )
            else:
                left_edge = doc.addObject("Part::Feature", "Edge_Left")
                left_edge.Shape = Part.makeBox(
                    lc.inch(deck_width), lc.inch(edge_length_y), lc.inch(deck_thick)
                )
                left_edge.Placement.Base = App.Vector(
                    lc.inch(-DECK_OVERHANG_IN), lc.inch(-DECK_OVERHANG_IN), lc.inch(board_z)
                )
                lc.attach_metadata(left_edge, deck_row, deck_label, supplier=supplier)
            edge_boards.append(left_edge)

        if include_right_edge:
            # Right edge runs N-S (along Y) at X = width_in - deck_width (no overhang, matches EW)
            # Miter at front (south) if front_edge exists, at back (north) if back_edge exists
            edge_length_y = depth_in + 2 * DECK_OVERHANG_IN
            miter_start = "front" if (miter_corners and include_front_edge) else None
            miter_end = "back" if (miter_corners and include_back_edge) else None

            if miter_corners and (miter_start or miter_end):
                right_edge = _make_mitered_edge_board(
                    doc,
                    deck_row,
                    deck_label,
                    edge_length_in=edge_length_y,
                    deck_width=deck_width,
                    deck_thick=deck_thick,
                    board_z=board_z,
                    x_pos=width_in - deck_width,
                    y_pos=-DECK_OVERHANG_IN,
                    name="Edge_Right",
                    supplier=supplier,
                    miter_start=miter_start,
                    miter_end=miter_end,
                    edge_axis="Y",
                )
            else:
                right_edge = doc.addObject("Part::Feature", "Edge_Right")
                right_edge.Shape = Part.makeBox(
                    lc.inch(deck_width), lc.inch(edge_length_y), lc.inch(deck_thick)
                )
                right_edge.Placement.Base = App.Vector(
                    lc.inch(width_in - deck_width), lc.inch(-DECK_OVERHANG_IN), lc.inch(board_z)
                )
            lc.attach_metadata(right_edge, deck_row, deck_label, supplier=supplier)
            edge_boards.append(right_edge)

    created.extend(boards)
    created.extend(edge_boards)
    created.extend(seam_boards)

    # Create assembly
    App.Console.PrintMessage(
        f"[deck_assemblies] Created assembly: {assembly_name} (type: App::Part)\n"
    )
    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    for obj in created:
        assembly.addObject(obj)

    # Apply global position offset
    assembly.Placement.Base = App.Vector(lc.inch(x_base), lc.inch(y_base), lc.inch(z_base))

    doc.recompute()

    direction_str = "E-W" if board_direction.upper() == "EW" else "N-S"
    seam_str = f", {len(seam_boards)} seam boards" if seam_boards else ""
    App.Console.PrintMessage(
        f"[deck_assemblies] ✓ Assembly complete: {assembly_name} "
        f"({width_ft:.0f}' x {depth_ft:.0f}', {len(boards)} boards {direction_str}, "
        f"{len(edge_boards)} edge boards{seam_str})\n"
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
    deck_label = DECK_BOARD_LABEL
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
    _deck_len = float(deck_row["length_in"])  # noqa: F841 - kept for reference
    deck_gap = DECK_BOARD_GAP_IN
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
    y_pos = -DECK_OVERHANG_IN  # shift first board toward house by overhang
    last_full_end = None

    while True:
        next_y = y_pos + deck_width
        if next_y > proj_y_in:
            # Rip last board to remaining space
            rip_start = (last_full_end if last_full_end is not None else y_pos) + deck_gap
            remaining = proj_y_in - rip_start + DECK_OVERHANG_IN  # widen rip by overhang
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
        # Left edge board (at X=0, runs from Y=-overhang to Y=proj_y_in+overhang)
        left_edge = doc.addObject("Part::Feature", "Edge_Left")
        left_edge.Shape = Part.makeBox(
            lc.inch(deck_width),  # 5.5" wide
            lc.inch(proj_y_in + 2 * DECK_OVERHANG_IN),  # Extends overhang each direction
            lc.inch(deck_thick),
        )
        left_edge.Placement.Base = App.Vector(0, lc.inch(-DECK_OVERHANG_IN), lc.inch(joist_depth))
        lc.attach_metadata(left_edge, deck_row, deck_label, supplier=supplier)
        edge_boards.append(left_edge)

    if include_right_edge:
        # Right edge board (at X=length_x_in - deck_width, runs from Y=-overhang to Y=proj_y_in+overhang)
        right_edge = doc.addObject("Part::Feature", "Edge_Right")
        right_edge.Shape = Part.makeBox(
            lc.inch(deck_width),  # 5.5" wide
            lc.inch(proj_y_in + 2 * DECK_OVERHANG_IN),  # Extends overhang each direction
            lc.inch(deck_thick),
        )
        right_edge.Placement.Base = App.Vector(
            lc.inch(length_x_in - deck_width), lc.inch(-DECK_OVERHANG_IN), lc.inch(joist_depth)
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


def create_deck_surface_filler(
    doc,
    catalog_rows,
    width_in=9.0,
    depth_ft=8.0,
    assembly_name="Deck_Surface_Filler",
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    supplier="lowes",
    include_front_edge=False,
    include_back_edge=False,
    include_left_edge=False,
    include_right_edge=True,
    miter_corners=False,
):
    """
    Create a narrow deck surface filler module.

    This is used to fill the gap between deck modules and floor modules
    when they don't perfectly align (e.g., 9" filler for 3x16' decks
    to match 3x195" floor modules).

    Args:
        doc: FreeCAD document
        catalog_rows: Catalog data (list of dicts)
        width_in: Width of filler in inches (X direction)
        depth_ft: Depth of filler in feet (Y direction)
        assembly_name: Name for the assembly
        x_base, y_base, z_base: Position offsets (inches)
        supplier: Supplier preference ("lowes" or "hd")
        include_front_edge: Include edge board on front (south) side
        include_back_edge: Include edge board on back (north) side
        include_left_edge: Include edge board on left side
        include_right_edge: Include edge board on right side
        miter_corners: If True, edge boards get 45-degree mitered corners

    Returns:
        App::Part assembly containing deck boards and optional edge boards
    """
    # Parameters
    length_x_in = width_in
    proj_y_in = depth_ft * 12.0
    deck_label = DECK_BOARD_LABEL
    joist_depth = 11.25  # 2x12 depth

    # Find stock
    deck_row = lc.find_stock(catalog_rows, deck_label)

    if not deck_row:
        raise ValueError(f"Deck board label '{deck_label}' not found in catalog.")

    # Dimensions
    deck_thick = float(deck_row["actual_thickness_in"])
    deck_width = float(deck_row["actual_width_in"])
    deck_gap = DECK_BOARD_GAP_IN

    created = []

    # Calculate board length and X offset based on edge boards
    board_x_start = deck_width if include_left_edge else 0.0
    board_length = length_x_in
    if include_left_edge:
        board_length -= deck_width
    if include_right_edge:
        board_length -= deck_width

    # If filler is narrower than board width, just use edge board(s)
    if board_length <= 0:
        App.Console.PrintMessage(
            f'[deck_assemblies] Filler {assembly_name} is narrow ({width_in:.1f}"), using edge boards only\n'
        )
    else:

        def make_deck_board(name, y_local):
            box = Part.makeBox(lc.inch(board_length), lc.inch(deck_width), lc.inch(deck_thick))
            obj = doc.addObject("Part::Feature", name)
            obj.Shape = box
            obj.Placement.Base = App.Vector(
                lc.inch(board_x_start), lc.inch(y_local), lc.inch(joist_depth)
            )
            lc.attach_metadata(obj, deck_row, deck_label, supplier=supplier)
            return obj

        # Deck boards running along X, 1/8" gaps
        boards = []
        board_count = 0
        step = deck_width + deck_gap
        y_pos = -DECK_OVERHANG_IN  # shift first board toward house by overhang
        last_full_end = None

        while True:
            next_y = y_pos + deck_width
            if next_y > proj_y_in:
                # Rip last board to remaining space
                rip_start = (last_full_end if last_full_end is not None else y_pos) + deck_gap
                remaining = proj_y_in - rip_start + DECK_OVERHANG_IN  # widen rip by overhang
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
    edge_boards = []

    if include_left_edge:
        left_edge = doc.addObject("Part::Feature", "Edge_Left")
        left_edge.Shape = Part.makeBox(
            lc.inch(deck_width),
            lc.inch(proj_y_in + 2 * DECK_OVERHANG_IN),
            lc.inch(deck_thick),
        )
        left_edge.Placement.Base = App.Vector(0, lc.inch(-DECK_OVERHANG_IN), lc.inch(joist_depth))
        lc.attach_metadata(left_edge, deck_row, deck_label, supplier=supplier)
        edge_boards.append(left_edge)

    if include_right_edge:
        right_edge = doc.addObject("Part::Feature", "Edge_Right")
        right_edge.Shape = Part.makeBox(
            lc.inch(deck_width),
            lc.inch(proj_y_in + 2 * DECK_OVERHANG_IN),
            lc.inch(deck_thick),
        )
        right_edge.Placement.Base = App.Vector(
            lc.inch(length_x_in - deck_width), lc.inch(-DECK_OVERHANG_IN), lc.inch(joist_depth)
        )
        lc.attach_metadata(right_edge, deck_row, deck_label, supplier=supplier)
        edge_boards.append(right_edge)

    created.extend(edge_boards)

    # Create assembly (App::Part)
    App.Console.PrintMessage(
        f"[deck_assemblies] Created assembly: {assembly_name} (type: App::Part)\n"
    )
    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    for obj in created:
        assembly.addObject(obj)

    assembly.Placement.Base = App.Vector(lc.inch(x_base), lc.inch(y_base), lc.inch(z_base))

    doc.recompute()

    num_boards = len([o for o in created if o not in edge_boards])
    App.Console.PrintMessage(
        f"[deck_assemblies] ✓ Assembly complete: {assembly_name} "
        f"({num_boards} deck boards, {len(edge_boards)} edge boards, {width_in:.1f}\" x {depth_ft}' filler)\n"
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
    deck_label_main = DECK_BOARD_LABEL  # 12' boards for main deck boards (cut to 105")
    deck_label_edge = DECK_BOARD_LABEL  # 12' boards for edge boards (cut to fit)
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
    deck_gap = DECK_BOARD_GAP_IN
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
    y_pos = -DECK_OVERHANG_IN  # shift first board toward house by overhang
    last_full_end = None

    while True:
        next_y = y_pos + deck_width
        if next_y > proj_y_in:
            # Rip last board to remaining space
            rip_start = (last_full_end if last_full_end is not None else y_pos) + deck_gap
            remaining = proj_y_in - rip_start + DECK_OVERHANG_IN  # widen rip by overhang
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
        # Left edge board (at X=0, runs from Y=-overhang to Y=proj_y_in+overhang)
        edge_length = proj_y_in + 2 * DECK_OVERHANG_IN
        left_edge = doc.addObject("Part::Feature", "Edge_Left")
        left_edge.Shape = Part.makeBox(
            lc.inch(deck_width),  # 5.5" wide
            lc.inch(edge_length),  # Extends overhang each direction
            lc.inch(deck_thick),
        )
        left_edge.Placement.Base = App.Vector(0, lc.inch(-DECK_OVERHANG_IN), lc.inch(joist_depth))
        lc.attach_metadata(left_edge, deck_row_edge, deck_label_edge, supplier=supplier)
        try:
            if "cut_length_in" not in left_edge.PropertiesList:
                left_edge.addProperty("App::PropertyString", "cut_length_in")
            left_edge.cut_length_in = f"{edge_length}"
        except Exception:
            pass
        edge_boards.append(left_edge)

    if include_right_edge:
        # Right edge board (at X=length_x_in - deck_width, runs from Y=-overhang to Y=proj_y_in+overhang)
        edge_length = proj_y_in + 2 * DECK_OVERHANG_IN
        right_edge = doc.addObject("Part::Feature", "Edge_Right")
        right_edge.Shape = Part.makeBox(
            lc.inch(deck_width),  # 5.5" wide
            lc.inch(edge_length),  # Extends overhang each direction
            lc.inch(deck_thick),
        )
        right_edge.Placement.Base = App.Vector(
            lc.inch(length_x_in - deck_width), lc.inch(-DECK_OVERHANG_IN), lc.inch(joist_depth)
        )
        lc.attach_metadata(right_edge, deck_row_edge, deck_label_edge, supplier=supplier)
        try:
            if "cut_length_in" not in right_edge.PropertiesList:
                right_edge.addProperty("App::PropertyString", "cut_length_in")
            right_edge.cut_length_in = f"{edge_length}"
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
    rim_label = "2x12x192"
    joist_label = "2x12x96"
    deck_label = DECK_BOARD_LABEL
    post_label = "post_6x6x144_PT"

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
    _joist_len = float(joist_row["length_in"])  # 96" - noqa: F841 - kept for reference
    deck_thick = float(deck_row["actual_thickness_in"])  # 1.0"
    deck_width = float(deck_row["actual_width_in"])  # 5.5"
    deck_len = float(deck_row["length_in"])  # 192"
    deck_gap = DECK_BOARD_GAP_IN
    post_thick = float(post_row["actual_thickness_in"])  # 5.5"
    post_width = float(post_row["actual_width_in"])  # 5.5"
    _post_len = float(post_row["length_in"])  # 144" stock - noqa: F841 - kept for reference
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
        c += JOIST_SPACING_OC_IN
    if not centers or centers[-1] < last_center - 1e-6:
        centers.append(last_center)

    for idx, cx in enumerate(centers, start=1):
        x_pos = cx - (joist_thick / 2.0)
        created.append(make_joist(f"Joist_{idx}", x_pos))

    # Deck boards running along X, 1/8" gaps
    boards = []
    board_count = 0
    step = deck_width + deck_gap
    y_pos = -DECK_OVERHANG_IN  # shift first board toward house by overhang
    last_full_end = None

    while True:
        next_y = y_pos + deck_width
        if next_y > proj_y_in:
            # Rip last board to remaining space
            rip_start = (last_full_end if last_full_end is not None else y_pos) + deck_gap
            remaining = proj_y_in - rip_start + DECK_OVERHANG_IN  # widen rip by overhang
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
            _pz = p.Placement.Base.z / lc.inch(1)  # noqa: F841 - kept for reference
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

    # Hangers on house rim and outboard rim for each interior joist
    hangs = _create_deck_hangers(
        doc,
        centers,
        joist_thick,
        joist_depth,
        proj_y_in,
        HANGER_THICKNESS_IN,
        HANGER_HEIGHT_IN,
        HANGER_SEAT_DEPTH_IN,
        HANGER_LABEL,
    )
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


def create_deck_surface_perpendicular_over_stair(
    doc,
    catalog_rows,
    assembly_name="Deck_Surface_Stair_Perpendicular",
    stair_config=None,
    x_base=0.0,
    y_base=0.0,
    z_base=0.0,
    supplier="lowes",
):
    """
    Create perpendicular deck boards (running north-south) over stair opening.

    Design:
        - Deck boards run perpendicular (north-south) to span across stair opening
        - Boards start at stair rim east face (west end of boards)
        - Extend east to cover stair area (tread width = 3')
        - Match standard deck board spacing (1/8" gaps)

    Args:
        doc: FreeCAD document
        catalog_rows: Catalog data
        assembly_name: Name for the assembly
        stair_config: STAIRS config dict with keys:
            - tread_width_ft: Stair width (3.0' typical, determines board length)
            - stair_y_snap_ft: Y position where top tread south edge meets rim
        x_base, y_base, z_base: Position offsets (inches)
        supplier: Supplier preference

    Returns:
        App::Part assembly containing perpendicular deck boards
    """
    if stair_config is None:
        raise ValueError("stair_config required for perpendicular stair deck boards")

    # Parameters
    deck_label = DECK_BOARD_LABEL  # 12' boards (will be cut to length)
    tread_width_ft = stair_config.get("tread_width_ft", 3.0)  # 3' stair width
    stair_y_snap_ft = stair_config.get("stair_y_snap_ft", 0.0)  # Top tread south edge

    # Find stock
    deck_row = lc.find_stock(catalog_rows, deck_label)
    if not deck_row:
        raise ValueError(f"Deck board label '{deck_label}' not found in catalog.")

    # Dimensions
    deck_thick = float(deck_row["actual_thickness_in"])  # 1.0" for 5/4
    deck_width = float(deck_row["actual_width_in"])  # 5.5" actual
    board_length_in = tread_width_ft * 12.0  # 36" (cut to stair width)
    gap_in = 0.125  # 1/8" gap between boards

    # Coverage area: front rim (28') to back of stair opening
    # Deck boards span from front rim north edge to where stairs descend
    # For now, cover 8' depth (typical front deck depth)
    coverage_depth_in = 96.0  # 8' (will extend north from front rim)

    # Calculate number of boards needed
    board_pitch = deck_width + gap_in  # 5.5" + 0.125" = 5.625"
    num_boards = int(coverage_depth_in / board_pitch) + 1

    # Create assembly
    assembly = lc.create_assembly(doc, assembly_name)
    boards = []

    # Create boards running north-south (perpendicular to main deck boards)
    for i in range(num_boards):
        y_offset_in = stair_y_snap_ft * 12.0 + (i * board_pitch)

        board = doc.addObject("Part::Feature", f"{assembly_name}_Board_{i+1}")
        board_box = Part.makeBox(
            lc.inch(board_length_in),  # Length in X direction (east-west, 3' stair width)
            lc.inch(deck_width),  # Width in Y direction (north-south, 5.5" nominal)
            lc.inch(deck_thick),  # Thickness in Z direction (1.0")
        )
        board_box.Placement.Base = App.Vector(
            0.0,  # X position (will be offset by x_base in assembly placement)
            lc.inch(
                y_offset_in - (stair_y_snap_ft * 12.0)
            ),  # Y position relative to assembly origin
            0.0,  # Z position (will be offset by z_base in assembly placement)
        )
        board.Shape = board_box

        # Attach metadata
        lc.attach_metadata(board, deck_row, deck_label, supplier=supplier)
        boards.append(board)

    # Add all boards to assembly
    for board in boards:
        assembly.addObject(board)

    # Apply global position offset
    assembly.Placement.Base = App.Vector(lc.inch(x_base), lc.inch(y_base), lc.inch(z_base))

    doc.recompute()

    App.Console.PrintMessage(
        f"[deck_assemblies] ✓ Assembly complete: {assembly_name} "
        f"({len(boards)} perpendicular deck boards over stair opening)\n"
    )

    return assembly
