# -*- coding: utf-8 -*-
"""
Deck railing assembly creation functions for FreeCAD.

SAFETY-CRITICAL COMPONENT
=========================
This code creates structural railings that prevent falls from elevated decks.
If these railings fail, people can die. All design decisions prioritize
structural integrity and code compliance over aesthetics or material cost.

IRC Code Requirements (2021 International Residential Code):
- R312.1.1: Guards REQUIRED when deck is >30" above grade
- R312.1.3: Max 4" sphere opening between balusters (child safety)
- R312.2: Guard height minimum 36" (residential), 42" for commercial
- R312.2.1: Opening limitation applies to entire guard height
- R317.1: Decay-resistant or preservative-treated wood required
- R507.2.4: Post-to-beam connections per manufacturer specs
- R507.9.1: Post spacing max 6' on-center (we use 4' for safety)
- R507.9.2: Posts must be mechanically fastened to structure

Structural Design Philosophy:
- Posts: 4x4 PT lumber, bolted through rim joists (not surface-mounted)
- Post spacing: 48" (4') on-center for extra strength (IRC allows 6')
- Post height: Extends from joist bottom to 48" above deck surface
- Post position: Inside rim face, directly against rim for bolting
- Blocking: Added between joists at post locations for lateral support
- Top rail: 2x4 PT laid flat on top of posts, continuous where possible
- Bottom rail: 2x4 PT between posts, 3.5" above deck surface
- Balusters: 2x2 PT, spaced 3.5" apart (provides 4" sphere clearance)

Post Connection Detail:
- Post sits inside rim joist, face against rim inside face
- Through-bolts (2x 1/2" carriage bolts) connect post to rim
- Blocking connects adjacent joists at post location
- Blocking hugs post on face opposite rim (lateral support)
- This creates a rigid connection that transfers load to deck frame

For Luke Dombrowski. Stay Alive.
"""

import os
import sys

import Part

import FreeCAD as App

# Add macros directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    import lumber_common as lc
except ImportError:
    from . import lumber_common as lc


# ============================================================
# CONSTANTS - IRC Code Requirements (No Magic Numbers)
# ============================================================
# All dimensions are in inches unless noted otherwise.
# All values derived from IRC 2021 or explicit structural engineering decisions.

# --- Guard/Railing Height (IRC R312.2) ---
# Minimum guard height for residential is 36", commercial is 42"
# We use 48" for beach house (higher deck = more conservative)
RAILING_HEIGHT_RESIDENTIAL_MIN_IN = 36.0  # IRC R312.2 minimum for residential
RAILING_HEIGHT_COMMERCIAL_MIN_IN = 42.0  # IRC R312.2 minimum for commercial
RAILING_HEIGHT_IN = 48.0  # Our design: 48" for elevated beach deck (exceeds code)

# --- Baluster Spacing (IRC R312.1.3 - 4" Sphere Rule) ---
# IRC requires that a 4" sphere cannot pass through openings
# Baluster thickness (2x2 = 1.5" actual) plus gap must prevent 4" sphere
IRC_SPHERE_DIAMETER_IN = 4.0  # IRC R312.1.3: max sphere that can pass
BALUSTER_ACTUAL_THICKNESS_IN = 1.5  # 2x2 PT actual dimension
BALUSTER_SPACING_IN = 3.5  # Gap between balusters (< 4" per code)

# --- Post Spacing (IRC R507.9.1) ---
# IRC allows max 6' (72") between posts, but we use 4' (48") for safety
# This is SAFETY-CRITICAL: closer spacing = more posts = stronger railing
# If this railing fails, someone could die from a fall
IRC_MAX_POST_SPACING_IN = 72.0  # 6' max per IRC R507.9.1
MAX_POST_SPACING_IN = 48.0  # Our design: 4' for structural integrity

# --- Post Dimensions (4x4 PT) ---
POST_NOMINAL_SIZE = "4x4"  # Nominal post size
POST_ACTUAL_THICKNESS_IN = 3.5  # 4x4 actual dimension
POST_ACTUAL_WIDTH_IN = 3.5  # 4x4 actual dimension (square)

# --- Rail Dimensions (2x4 PT) ---
RAIL_NOMINAL_SIZE = "2x4"  # Nominal rail size
RAIL_ACTUAL_THICKNESS_IN = 1.5  # 2x4 actual thickness
RAIL_ACTUAL_WIDTH_IN = 3.5  # 2x4 actual width

# --- Rim Joist Dimensions (2x12 PT) ---
RIM_JOIST_ACTUAL_THICKNESS_IN = 1.5  # 2x12 actual thickness

# --- Rail Heights (Above Deck Surface) ---
# Bottom rail sits above deck to allow water drainage and prevent rot
BOTTOM_RAIL_HEIGHT_ABOVE_DECK_IN = 3.5  # Bottom rail clearance above deck
# Top rail is flush with post tops (rail thickness is subtracted)
TOP_RAIL_OFFSET_FROM_POST_TOP_IN = RAIL_ACTUAL_THICKNESS_IN  # 1.5"


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def _calculate_post_positions(
    run_length_in, max_spacing_in=MAX_POST_SPACING_IN, post_thick_in=POST_ACTUAL_THICKNESS_IN
):
    """
    Calculate post positions along a railing run.

    Posts are placed at:
    - Both ends of the run
    - Interior posts spaced <= max_spacing_in apart

    Args:
        run_length_in: Total length of railing run (inches)
        max_spacing_in: Maximum spacing between posts (inches)
        post_thick_in: Post thickness for centering (inches)

    Returns:
        List of post center positions (inches from start)
    """
    if run_length_in <= max_spacing_in:
        # Short run: posts at both ends only
        return [post_thick_in / 2.0, run_length_in - post_thick_in / 2.0]

    # Calculate number of spans needed
    num_spans = int((run_length_in - post_thick_in) / max_spacing_in) + 1
    actual_spacing = (run_length_in - post_thick_in) / num_spans

    positions = []
    pos = post_thick_in / 2.0
    while pos <= run_length_in - post_thick_in / 2.0 + 0.1:
        positions.append(pos)
        pos += actual_spacing

    # Ensure end post is included
    end_pos = run_length_in - post_thick_in / 2.0
    if not positions or abs(positions[-1] - end_pos) > 0.1:
        positions.append(end_pos)

    return positions


def _calculate_baluster_positions(
    span_length_in, baluster_thick_in=BALUSTER_ACTUAL_THICKNESS_IN, max_gap_in=BALUSTER_SPACING_IN
):
    """
    Calculate baluster positions within a span between posts.

    Balusters are evenly distributed with gaps <= max_gap_in.

    Args:
        span_length_in: Distance between post faces (inches)
        baluster_thick_in: Baluster thickness (inches)
        max_gap_in: Maximum gap between balusters (inches)

    Returns:
        List of baluster center positions (inches from span start)
    """
    if span_length_in <= 0:
        return []

    # Calculate number of balusters needed
    # Each baluster takes up baluster_thick + gap, except last has no trailing gap
    # span = n * baluster_thick + (n + 1) * gap
    # Solve for n: n = (span - gap) / (baluster_thick + gap)
    available = span_length_in - max_gap_in  # Start with one gap at each end
    if available <= 0:
        return []

    num_balusters = max(1, int(available / (baluster_thick_in + max_gap_in)) + 1)

    # Calculate actual gap to distribute balusters evenly
    total_baluster_width = num_balusters * baluster_thick_in
    total_gap_space = span_length_in - total_baluster_width
    actual_gap = total_gap_space / (num_balusters + 1)

    # Generate positions
    positions = []
    pos = actual_gap + baluster_thick_in / 2.0
    for _ in range(num_balusters):
        positions.append(pos)
        pos += baluster_thick_in + actual_gap

    return positions


# ============================================================
# RAILING SECTION CREATION
# ============================================================


def create_railing_section(
    doc,
    catalog_rows,
    start_x_in,
    start_y_in,
    end_x_in,
    end_y_in,
    deck_surface_z_in,
    section_name="Railing_Section",
    supplier="lowes",
    include_start_post=True,
    include_end_post=True,
    post_height_above_deck_in=None,
    post_base_z_in=None,
):
    """
    Create a railing section between two points.

    The railing runs from (start_x, start_y) to (end_x, end_y) and consists of:
    - Posts at each end and interior positions (max 6' spacing)
    - Top rail running along post tops
    - Bottom rail 3.5" above deck surface
    - Balusters between posts (max 3.5" gaps)

    Args:
        doc: FreeCAD document
        catalog_rows: Lumber catalog data
        start_x_in, start_y_in: Start point (inches)
        end_x_in, end_y_in: End point (inches)
        deck_surface_z_in: Z position of deck surface top (inches)
        section_name: Name prefix for parts
        supplier: Supplier for BOM
        include_start_post: If True, include post at start of run (for corner deduplication)
        include_end_post: If True, include post at end of run (for corner deduplication)
        post_height_above_deck_in: Height of post above deck surface (default: RAILING_HEIGHT_IN)
        post_base_z_in: Z position for post bottom (default: deck_surface_z_in).
                        Set to joist bottom for posts that extend below deck.

    Returns:
        Tuple of (posts, rails, balusters) lists
    """
    import math

    posts = []
    rails = []
    balusters = []

    # Determine railing direction and length
    dx = end_x_in - start_x_in
    dy = end_y_in - start_y_in
    run_length = math.sqrt(dx * dx + dy * dy)

    if run_length < 1.0:
        App.Console.PrintWarning(
            f"[railing] Section {section_name} too short ({run_length:.1f}in)\n"
        )
        return (posts, rails, balusters)

    # Normalize direction
    dir_x = dx / run_length
    dir_y = dy / run_length

    # Determine if railing runs primarily E-W or N-S
    is_ew = abs(dx) > abs(dy)

    # Get lumber from catalog
    post_label = "post_4x4x96_PT"
    rail_label = "2x4x96_PT"  # Will be cut to length
    baluster_label = "baluster_2x2x42_PT"

    post_row = lc.find_stock(catalog_rows, post_label)
    rail_row = lc.find_stock(catalog_rows, rail_label)
    baluster_row = lc.find_stock(catalog_rows, baluster_label)

    if not post_row:
        App.Console.PrintWarning(f"[railing] Post stock '{post_label}' not found\n")
        return (posts, rails, balusters)

    # Dimensions
    post_thick = float(post_row["actual_thickness_in"])  # 3.5"
    post_width = float(post_row["actual_width_in"])  # 3.5"

    rail_thick = RAIL_ACTUAL_THICKNESS_IN  # 2x4 thickness
    rail_width = RAIL_ACTUAL_WIDTH_IN  # 2x4 width

    if baluster_row:
        baluster_thick = float(baluster_row["actual_thickness_in"])
        baluster_width = float(baluster_row["actual_width_in"])
    else:
        baluster_thick = BALUSTER_ACTUAL_THICKNESS_IN  # 2x2 fallback
        baluster_width = BALUSTER_ACTUAL_THICKNESS_IN  # 2x2 fallback (square)

    # Post and rail heights
    if post_height_above_deck_in is None:
        post_height_above_deck_in = RAILING_HEIGHT_IN

    # Post base Z position (where post bottom sits)
    if post_base_z_in is None:
        post_base_z_in = deck_surface_z_in

    # Total post height from base to top (extends above deck)
    post_height_in = (deck_surface_z_in - post_base_z_in) + post_height_above_deck_in

    # Calculate post positions along the run
    post_positions = _calculate_post_positions(run_length, MAX_POST_SPACING_IN, post_thick)

    # Remove start/end posts for corner deduplication
    if not include_start_post and post_positions:
        post_positions = post_positions[1:]
    if not include_end_post and post_positions:
        post_positions = post_positions[:-1]

    # Create posts
    for idx, pos in enumerate(post_positions, start=1):
        post_name = f"{section_name}_Post_{idx}"

        # Post position along run direction
        px = start_x_in + dir_x * pos - post_thick / 2.0
        py = start_y_in + dir_y * pos - post_thick / 2.0

        post = doc.addObject("Part::Feature", post_name)
        post.Shape = Part.makeBox(
            lc.inch(post_thick),
            lc.inch(post_width),
            lc.inch(post_height_in),
        )
        post.Placement.Base = App.Vector(
            lc.inch(px),
            lc.inch(py),
            lc.inch(post_base_z_in),
        )
        if post_row:
            lc.attach_metadata(post, post_row, post_label, supplier=supplier)
        posts.append(post)

    # Create rails between posts
    if len(post_positions) >= 2:
        for i in range(len(post_positions) - 1):
            span_start = post_positions[i] + post_thick / 2.0
            span_end = post_positions[i + 1] - post_thick / 2.0
            span_length = span_end - span_start

            if span_length < 1.0:
                continue

            # Top rail
            top_rail_name = f"{section_name}_TopRail_{i + 1}"
            top_rail = doc.addObject("Part::Feature", top_rail_name)

            # Top rail Z: at top of post, laid flat
            # Post top = post_base_z + post_height, rail sits below that
            top_rail_z = post_base_z_in + post_height_in - rail_thick

            if is_ew:
                # Rail runs E-W (X direction)
                top_rail.Shape = Part.makeBox(
                    lc.inch(span_length),
                    lc.inch(rail_width),
                    lc.inch(rail_thick),
                )
                top_rail.Placement.Base = App.Vector(
                    lc.inch(start_x_in + span_start),
                    lc.inch(start_y_in - rail_width / 2.0),
                    lc.inch(top_rail_z),
                )
            else:
                # Rail runs N-S (Y direction)
                top_rail.Shape = Part.makeBox(
                    lc.inch(rail_width),
                    lc.inch(span_length),
                    lc.inch(rail_thick),
                )
                top_rail.Placement.Base = App.Vector(
                    lc.inch(start_x_in - rail_width / 2.0),
                    lc.inch(start_y_in + span_start),
                    lc.inch(top_rail_z),
                )

            if rail_row:
                lc.attach_metadata(top_rail, rail_row, rail_label, supplier=supplier)
            rails.append(top_rail)

            # Bottom rail
            bottom_rail_name = f"{section_name}_BottomRail_{i + 1}"
            bottom_rail = doc.addObject("Part::Feature", bottom_rail_name)

            bottom_rail_z = deck_surface_z_in + BOTTOM_RAIL_HEIGHT_ABOVE_DECK_IN

            if is_ew:
                bottom_rail.Shape = Part.makeBox(
                    lc.inch(span_length),
                    lc.inch(rail_width),
                    lc.inch(rail_thick),
                )
                bottom_rail.Placement.Base = App.Vector(
                    lc.inch(start_x_in + span_start),
                    lc.inch(start_y_in - rail_width / 2.0),
                    lc.inch(bottom_rail_z),
                )
            else:
                bottom_rail.Shape = Part.makeBox(
                    lc.inch(rail_width),
                    lc.inch(span_length),
                    lc.inch(rail_thick),
                )
                bottom_rail.Placement.Base = App.Vector(
                    lc.inch(start_x_in - rail_width / 2.0),
                    lc.inch(start_y_in + span_start),
                    lc.inch(bottom_rail_z),
                )

            if rail_row:
                lc.attach_metadata(bottom_rail, rail_row, rail_label, supplier=supplier)
            rails.append(bottom_rail)

            # Create balusters in this span
            baluster_positions = _calculate_baluster_positions(span_length, baluster_thick)

            # Baluster height: from top of bottom rail to bottom of top rail
            baluster_z_bottom = bottom_rail_z + rail_thick
            baluster_z_top = top_rail_z
            baluster_height = baluster_z_top - baluster_z_bottom

            if baluster_height < 1.0:
                continue

            for j, bpos in enumerate(baluster_positions, start=1):
                bal_name = f"{section_name}_Baluster_{i + 1}_{j}"
                bal = doc.addObject("Part::Feature", bal_name)

                bal.Shape = Part.makeBox(
                    lc.inch(baluster_thick),
                    lc.inch(baluster_width),
                    lc.inch(baluster_height),
                )

                if is_ew:
                    bal.Placement.Base = App.Vector(
                        lc.inch(start_x_in + span_start + bpos - baluster_thick / 2.0),
                        lc.inch(start_y_in - baluster_width / 2.0),
                        lc.inch(baluster_z_bottom),
                    )
                else:
                    bal.Placement.Base = App.Vector(
                        lc.inch(start_x_in - baluster_thick / 2.0),
                        lc.inch(start_y_in + span_start + bpos - baluster_width / 2.0),
                        lc.inch(baluster_z_bottom),
                    )

                if baluster_row:
                    lc.attach_metadata(bal, baluster_row, baluster_label, supplier=supplier)
                balusters.append(bal)

    return (posts, rails, balusters)


def create_deck_railings(
    doc,
    catalog_rows,
    perimeter,
    deck_surface_z_in,
    assembly_name="Deck_Railings",
    supplier="lowes",
    exclude_sides=None,
    gate_openings=None,
    post_height_above_deck_in=48.0,
    post_base_z_in=None,
    joist_depth_in=11.25,
    deck_board_thick_in=1.0,
):
    """
    Create railings around a deck perimeter.

    Args:
        doc: FreeCAD document
        catalog_rows: Lumber catalog data
        perimeter: Dict with x_min_in, x_max_in, y_min_in, y_max_in
        deck_surface_z_in: Z position of deck surface top (inches)
        assembly_name: Name for the assembly
        supplier: Supplier for BOM
        exclude_sides: List of sides to exclude ("north", "south", "east", "west")
                       Typically exclude the house side
        gate_openings: List of dicts defining gate openings:
                       [{"side": "south", "start_in": 100, "width_in": 36}, ...]
        post_height_above_deck_in: Height of posts above deck surface (default 48")
        post_base_z_in: Z position for post bottoms. If None, calculated as
                        deck_surface_z_in - deck_board_thick - joist_depth
        joist_depth_in: Depth of deck joists (default 11.25" for 2x12)
        deck_board_thick_in: Thickness of deck boards (default 1.0" for 5/4)

    Returns:
        App::Part assembly containing all railing components
    """
    if exclude_sides is None:
        exclude_sides = []
    if gate_openings is None:
        gate_openings = []

    # Calculate post base Z if not provided
    # Post bottom at joist bottom: deck_surface - deck_board_thick - joist_depth
    if post_base_z_in is None:
        post_base_z_in = deck_surface_z_in - deck_board_thick_in - joist_depth_in

    # Extract perimeter
    x_min = perimeter["x_min_in"]
    x_max = perimeter["x_max_in"]
    y_min = perimeter["y_min_in"]
    y_max = perimeter["y_max_in"]

    # Post inset from perimeter edge
    # Posts go INSIDE the rim joist, directly against the rim inside face
    # Post is bolted to rim for strength, blocking added later for lateral support
    rim_thick = RIM_JOIST_ACTUAL_THICKNESS_IN  # 1.5" (2x lumber)
    post_thick = POST_ACTUAL_THICKNESS_IN  # 3.5" (4x4 actual)
    # Inset = rim thickness + post_thick/2 (post face touches rim inside face)
    post_inset = rim_thick + post_thick / 2.0  # 3.25" (rim + half post)

    # Adjust perimeter inward for post centerline positions
    x_min_posts = x_min + post_inset
    x_max_posts = x_max - post_inset
    y_min_posts = y_min + post_inset
    y_max_posts = y_max - post_inset

    all_posts = []
    all_rails = []
    all_balusters = []

    # Create railing on each side (unless excluded)
    # Using adjusted post positions (inset from perimeter)
    #
    # Corner deduplication strategy:
    # - Corners are shared between two perpendicular sides
    # - SW corner: shared by south (start) and west (start)
    # - SE corner: shared by south (end) and east (start)
    # - NW corner: shared by north (start) and west (end)
    # - NE corner: shared by north (end) and east (end)
    #
    # Convention: E-W sides (south, north) own corner posts
    #            N-S sides (west, east) skip corner posts where E-W side exists

    sides = {
        "south": (x_min_posts, y_min_posts, x_max_posts, y_min_posts),  # Front edge
        "north": (x_min_posts, y_max_posts, x_max_posts, y_max_posts),  # Back edge
        "west": (x_min_posts, y_min_posts, x_min_posts, y_max_posts),  # Left edge
        "east": (x_max_posts, y_min_posts, x_max_posts, y_max_posts),  # Right edge
    }

    # Determine which sides are included
    excluded_lower = [s.lower() for s in exclude_sides]
    included_sides = {name: name.lower() not in excluded_lower for name in sides}

    for side_name, (sx, sy, ex, ey) in sides.items():
        if not included_sides[side_name]:
            continue

        # Determine which end posts to include based on corner deduplication
        # E-W sides always include their corner posts
        # N-S sides skip corner posts if the perpendicular E-W side exists
        include_start = True
        include_end = True

        if side_name == "west":
            # West start (SW corner) - skip if south is included
            if included_sides["south"]:
                include_start = False
            # West end (NW corner) - skip if north is included
            if included_sides["north"]:
                include_end = False
        elif side_name == "east":
            # East start (SE corner) - skip if south is included
            if included_sides["south"]:
                include_start = False
            # East end (NE corner) - skip if north is included
            if included_sides["north"]:
                include_end = False

        # Check for gate openings on this side
        side_gates = [g for g in gate_openings if g.get("side", "").lower() == side_name.lower()]

        if not side_gates:
            # Full railing on this side
            section_name = f"{assembly_name}_{side_name.capitalize()}"
            posts, rails, bals = create_railing_section(
                doc,
                catalog_rows,
                sx,
                sy,
                ex,
                ey,
                deck_surface_z_in,
                section_name=section_name,
                supplier=supplier,
                include_start_post=include_start,
                include_end_post=include_end,
                post_height_above_deck_in=post_height_above_deck_in,
                post_base_z_in=post_base_z_in,
            )
            all_posts.extend(posts)
            all_rails.extend(rails)
            all_balusters.extend(bals)
        else:
            # Split railing around gate openings
            # TODO: Implement gate opening support
            App.Console.PrintWarning(
                f"[railing] Gate openings not yet implemented for {side_name}\n"
            )
            # For now, create full railing
            section_name = f"{assembly_name}_{side_name.capitalize()}"
            posts, rails, bals = create_railing_section(
                doc,
                catalog_rows,
                sx,
                sy,
                ex,
                ey,
                deck_surface_z_in,
                section_name=section_name,
                supplier=supplier,
                include_start_post=include_start,
                include_end_post=include_end,
                post_height_above_deck_in=post_height_above_deck_in,
                post_base_z_in=post_base_z_in,
            )
            all_posts.extend(posts)
            all_rails.extend(rails)
            all_balusters.extend(bals)

    # Create assembly
    assembly = doc.addObject("App::Part", assembly_name)
    assembly.Label = assembly_name

    for obj in all_posts + all_rails + all_balusters:
        assembly.addObject(obj)

    App.Console.PrintMessage(
        f"[railing] ✓ Deck railings complete: {assembly_name} "
        f"({len(all_posts)} posts, {len(all_rails)} rails, {len(all_balusters)} balusters)\n"
    )

    return assembly


# ============================================================
# MODULE ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print("[railing_assemblies] Deck railing assembly module.")
    print("[railing_assemblies] Import into your macro: import railing_assemblies as ra")
    print("[railing_assemblies] Main function: create_deck_railings()")
