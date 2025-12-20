#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
septic_utilities.py - Septic system, utilities, and concrete slab for 950 Surf.

Underground Infrastructure:
  1. Septic tank (1000-1500 gallon, buried in northern back lot, centered at X=37.0')
  2. Leach field (drain field with multiple trenches)
  3. Drain line (4" PVC from house to tank via pile gap routing)
  4. Concrete slab (6" thick, driveway grade)
  5. Plumbing stub-ups (kitchen, bath, laundry)
  6. Electrical stub-ups (service entrance, sub-panel)

Design Notes:
  - Septic tank: 10' x 5' x 5' deep (typical 1500 gallon), centered at X=37.0'
  - Leach field: 30' x 20' with 3 trenches @ 5' OC
  - Drain line routing (aligns with stair module at Floor_Middle_Right_16x8):
    * Vertical stub-up through slab at pile 4,5 east face (X=33.635', Y=52.46875')
    * Underground 90° elbow at slab bottom
    * Underground horizontal run EAST to gap middle at X=37.0' (between pile columns 4 and 5)
    * Underground 90° elbow at gap middle
    * North-south "home run" in pile gap directly to tank inlet (all underground with slope)
  - Concrete slab: 6" thick (driveway grade per ACI 332)
  - Stub-ups: Extend 12" above slab for future plumbing/electrical

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

import beach_common as bc  # noqa: E402


def create_pipe_hanger(doc, x_ft, y_ft, z_ft, pipe_od_in, pile_size_in=12.0):
    """
    Create a pipe hanger/clamp to attach vertical drain pipe to pile.

    Design:
        - U-shaped bracket that wraps around pipe
        - Two mounting holes for fastening to pile
        - Positioned beside pile (pipe runs along pile edge)

    Args:
        doc: FreeCAD document
        x_ft: X position (same as pipe center)
        y_ft: Y position (same as pipe center)
        z_ft: Z position (height along pile)
        pipe_od_in: Pipe outer diameter (4" for drain line)
        pile_size_in: Pile width (default 12")

    Returns:
        Part::Feature object (pipe hanger)
    """
    # Hanger dimensions
    hanger_width_in = pipe_od_in + 1.0  # Wide enough to wrap around pipe + clearance
    hanger_height_in = 3.0  # Height of U-bracket
    hanger_thickness_in = 0.25  # Steel thickness
    mounting_hole_dia_in = 0.5  # 1/2" bolt holes

    # Create U-shaped bracket (simplified as rectangular band)
    # This wraps around the pipe from the pile side
    hanger = doc.addObject("Part::Feature", f"Pipe_Hanger_{int(z_ft)}ft")

    # Simplified hanger: rectangular ring around pipe
    outer_ring = Part.makeCylinder(
        bc.inch((pipe_od_in / 2.0) + hanger_thickness_in),
        bc.inch(hanger_height_in),
        App.Vector(bc.ft(x_ft), bc.ft(y_ft), bc.ft(z_ft)),
        App.Vector(0, 0, 1),
    )
    inner_cutout = Part.makeCylinder(
        bc.inch(pipe_od_in / 2.0),
        bc.inch(hanger_height_in + 0.1),
        App.Vector(bc.ft(x_ft), bc.ft(y_ft), bc.ft(z_ft) - bc.inch(0.05)),
        App.Vector(0, 0, 1),
    )

    # Cut out pipe clearance
    hanger_ring = outer_ring.cut(inner_cutout)

    # Cut out back half (open toward pile for installation)
    # This creates the U-shape
    back_cutout = Part.makeBox(
        bc.inch(hanger_width_in),
        bc.inch(hanger_width_in / 2.0),
        bc.inch(hanger_height_in + 0.2),
    )
    back_cutout.Placement.Base = App.Vector(
        bc.ft(x_ft) - bc.inch(hanger_width_in / 2.0),
        bc.ft(y_ft),  # Cut from pipe center toward pile
        bc.ft(z_ft) - bc.inch(0.1),
    )

    hanger_shape = hanger_ring.cut(back_cutout)
    hanger.Shape = hanger_shape

    return hanger


def create_septic_tank(doc, config):
    """
    Create septic tank geometry (underground).

    Args:
        doc: FreeCAD document
        config: SEPTIC_SYSTEM config dict

    Returns:
        Septic tank Part::Feature object
    """
    tank_x_ft = config["tank_x_ft"]
    tank_y_ft = config["tank_y_ft"]
    tank_length_ft = config["tank_length_ft"]
    tank_width_ft = config["tank_width_ft"]
    tank_depth_ft = config["tank_depth_ft"]

    # Tank positioned with center at (tank_x_ft, tank_y_ft)
    # Bottom at -tank_depth_ft (below grade)
    tank = doc.addObject("Part::Feature", "Septic_Tank")
    tank.Shape = Part.makeBox(bc.ft(tank_length_ft), bc.ft(tank_width_ft), bc.ft(tank_depth_ft))
    tank.Placement.Base = App.Vector(
        bc.ft(tank_x_ft - tank_length_ft / 2.0),
        bc.ft(tank_y_ft - tank_width_ft / 2.0),
        bc.ft(-tank_depth_ft),  # Underground
    )

    return tank


def create_leach_field(doc, config):
    """
    Create leach field trenches (drain field).

    Args:
        doc: FreeCAD document
        config: SEPTIC_SYSTEM config dict

    Returns:
        List of leach field trench Part::Feature objects
    """
    x_start_ft = config["leach_field_x_start_ft"]
    y_start_ft = config["leach_field_y_start_ft"]
    length_ft = config["leach_field_length_ft"]
    width_ft = config["leach_field_width_ft"]  # noqa: F841 (reserved for future use)
    trench_count = config["leach_field_trench_count"]
    trench_spacing_ft = config["leach_field_trench_spacing_ft"]

    trenches = []
    trench_width_ft = 2.0  # Typical trench width
    trench_depth_ft = 3.0  # Typical trench depth (below grade)

    for i in range(trench_count):
        y_pos_ft = y_start_ft + (i * trench_spacing_ft)
        trench_name = f"Leach_Field_Trench_{i}"
        trench = doc.addObject("Part::Feature", trench_name)
        trench.Shape = Part.makeBox(
            bc.ft(length_ft), bc.ft(trench_width_ft), bc.ft(trench_depth_ft)
        )
        trench.Placement.Base = App.Vector(
            bc.ft(x_start_ft), bc.ft(y_pos_ft), bc.ft(-trench_depth_ft)  # Underground
        )
        trenches.append(trench)

    return trenches


def create_drain_line(doc, config, start_x_ft, start_y_ft, end_x_ft, end_y_ft):
    """
    Create drain line from house to septic tank (4" PVC cylinders with couplings).

    Design:
        - 4" Schedule 40 PVC (typical sewer drain)
        - Solid cylinders (not hollow - simplified for construction planning)
        - 10' pipe sections with couplings
        - Slope: 1/4" per foot (2% grade, typical for 4" drain per IPC 704.1)

    Routing Strategy (for 950 Surf):
        1. Vertical stub-up through concrete slab at pile 4,5 east face (X=33.635', Y=52.46875')
        2. Underground 90-degree elbow at slab bottom
        3. Underground horizontal run EAST (with slope) to gap middle: (33.635, 52.46875) → (37.0, 52.46875)
        4. Underground 90-degree elbow at gap middle
        5. Underground horizontal run NORTH in pile gap: (37.0, 52.46875) → (37.0, 88.0)
        6. Septic tank centered at X=37.0' (north-south run goes straight into tank)

        The north-south "home run" is positioned in the middle of pile gaps (between pile
        columns 4 and 5 at X=37.0') to avoid alignment issues with piles.

    Args:
        doc: FreeCAD document
        config: SEPTIC_SYSTEM config dict with keys:
            - drain_line_diameter_in: Pipe diameter (4")
            - drain_line_depth_in: Burial depth (24" below grade)
            - drain_line_lateral_x_ft: X position for vertical drop (gap middle)
            - drain_line_waypoint_x_ft: X waypoint (same as lateral for straight run)
            - drain_line_waypoint_y_ft: Y waypoint (tank inlet position)
        start_x_ft: Starting X position (house stub-up at pile east face)
        start_y_ft: Starting Y position (house stub-up Y)
        end_x_ft: Ending X position (septic tank inlet X)
        end_y_ft: Ending Y position (septic tank inlet Y)

    Returns:
        List of Part::Feature objects (pipe sections and couplings)
    """
    # DEBUG: Log the Y position being received
    App.Console.PrintMessage(
        f"[DEBUG create_drain_line] start_x_ft={start_x_ft}, start_y_ft={start_y_ft}\n"
    )

    diameter_in = config["drain_line_diameter_in"]  # 4"
    depth_start_in = config["drain_line_depth_in"]  # 24" below grade at house

    # Lateral X position for vertical drop (if routing to gap middle before dropping)
    lateral_x_ft = config.get("drain_line_lateral_x_ft", start_x_ft)

    # Waypoint to route around piles
    waypoint_x_ft = config.get("drain_line_waypoint_x_ft", lateral_x_ft)
    waypoint_y_ft = config.get("drain_line_waypoint_y_ft", start_y_ft)

    # Calculate slope (1/4" per foot = 0.02083 ft/ft)
    slope_in_per_ft = 0.25

    # Calculate total horizontal run including waypoint routing
    # If lateral_x differs from start_x, we have an initial horizontal segment at Z=25' (above grade)
    lateral_run_ft = abs(lateral_x_ft - start_x_ft)
    run_1_ft = ((waypoint_x_ft - lateral_x_ft) ** 2 + (waypoint_y_ft - start_y_ft) ** 2) ** 0.5
    run_2_ft = ((end_x_ft - waypoint_x_ft) ** 2 + (end_y_ft - waypoint_y_ft) ** 2) ** 0.5

    depth_at_waypoint_in = depth_start_in + (run_1_ft * slope_in_per_ft)
    depth_end_in = depth_start_in + ((run_1_ft + run_2_ft) * slope_in_per_ft)

    # PVC pipe parameters
    pipe_od_in = diameter_in  # 4" nominal (outer diameter)
    pipe_section_length_ft = 10.0  # Standard 10' sections
    coupling_length_in = 6.0  # Typical coupling length
    coupling_od_in = pipe_od_in + 0.5  # Coupling slightly larger

    created = []

    # SEGMENT 1: Vertical stub-up from underground (Z=-24") to above foundation (Z=25')
    # This runs UP from underground through slab at the pile east face position (start_x_ft, start_y_ft)
    seg1_start = App.Vector(bc.ft(start_x_ft), bc.ft(start_y_ft), bc.inch(-depth_start_in))
    seg1_end = App.Vector(
        bc.ft(start_x_ft), bc.ft(start_y_ft), bc.ft(25.0)
    )  # 25' above grade (5' above foundation)
    seg1_vec = seg1_end - seg1_start
    seg1_length_mm = seg1_vec.Length

    if seg1_length_mm > 0.1:
        # Create 10' pipe sections for vertical run
        seg1_length_ft = seg1_length_mm / 304.8
        num_sections = int(seg1_length_ft / pipe_section_length_ft) + 1

        for i in range(num_sections):
            section_start_z_mm = seg1_start.z + (i * bc.ft(pipe_section_length_ft))
            section_end_z_mm = min(
                seg1_start.z + ((i + 1) * bc.ft(pipe_section_length_ft)), seg1_end.z
            )
            section_height_mm = section_end_z_mm - section_start_z_mm

            if section_height_mm > 1.0:
                pipe_name = f"Drain_Pipe_Vertical_{i}"
                pipe = doc.addObject("Part::Feature", pipe_name)
                pipe.Shape = Part.makeCylinder(
                    bc.inch(pipe_od_in / 2.0),
                    section_height_mm,
                    App.Vector(0, 0, 0),
                    App.Vector(0, 0, 1),
                )
                pipe.Placement.Base = App.Vector(seg1_start.x, seg1_start.y, section_start_z_mm)

                # DEBUG: Log cylinder position
                App.Console.PrintMessage(
                    f"[DEBUG] {pipe_name} created at X={seg1_start.x/304.8:.5f}', "
                    f"Y={seg1_start.y/304.8:.5f}', Z={pipe.Placement.Base.z/304.8:.2f}'\n"
                )

                created.append(pipe)

                # Add coupling at top of section (except last)
                if i < num_sections - 1:
                    coupling_name = f"Drain_Coupling_Vertical_{i}"
                    coupling = doc.addObject("Part::Feature", coupling_name)
                    coupling.Shape = Part.makeCylinder(
                        bc.inch(coupling_od_in / 2.0),
                        bc.inch(coupling_length_in),
                        App.Vector(0, 0, 0),
                        App.Vector(0, 0, 1),
                    )
                    coupling.Placement.Base = App.Vector(
                        seg1_start.x,
                        seg1_start.y,
                        section_end_z_mm - bc.inch(coupling_length_in / 2.0),
                    )
                    created.append(coupling)

        # Add pipe hangers every 4 feet along vertical run (IRC P2605.1 - max 4' spacing)
        # Hangers mount to pile at start_x_ft position (stub-up location)
        hanger_spacing_ft = 4.0
        num_hangers = int(seg1_length_ft / hanger_spacing_ft)
        for i in range(num_hangers + 1):
            hanger_z_ft = (seg1_start.z / 304.8) + (i * hanger_spacing_ft)
            # Don't exceed pipe end
            if hanger_z_ft <= (seg1_end.z / 304.8):
                hanger = create_pipe_hanger(doc, start_x_ft, start_y_ft, hanger_z_ft, pipe_od_in)
                created.append(hanger)

    # SEGMENT 2: Underground horizontal run EAST from stub-up to gap middle (lateral position)
    # This segment includes a 90-degree elbow at the bottom of the vertical stub-up
    lateral_run_ft = abs(lateral_x_ft - start_x_ft)
    if lateral_run_ft > 0.1:
        seg2_start = App.Vector(bc.ft(start_x_ft), bc.ft(start_y_ft), bc.inch(-depth_start_in))
        seg2_end = App.Vector(
            bc.ft(lateral_x_ft),
            bc.ft(start_y_ft),
            bc.inch(-depth_start_in - (lateral_run_ft * slope_in_per_ft)),
        )
        seg2_vec = seg2_end - seg2_start
        seg2_length_mm = seg2_vec.Length

        if seg2_length_mm > 0.1:
            seg2_axis = seg2_vec.normalize()
            seg2_length_ft = seg2_length_mm / 304.8
            num_sections = int(seg2_length_ft / pipe_section_length_ft) + 1

            for i in range(num_sections):
                section_start_mm = bc.ft(i * pipe_section_length_ft)
                section_end_mm = min(bc.ft((i + 1) * pipe_section_length_ft), seg2_length_mm)
                section_length_mm = section_end_mm - section_start_mm

                if section_length_mm > 1.0:
                    section_start_pos = seg2_start + (seg2_axis * section_start_mm)
                    pipe_name = f"Drain_Pipe_East_{i}"
                    pipe = doc.addObject("Part::Feature", pipe_name)
                    pipe.Shape = Part.makeCylinder(
                        bc.inch(pipe_od_in / 2.0), section_length_mm, section_start_pos, seg2_axis
                    )
                    created.append(pipe)

                    # Add coupling at end of section (except last)
                    if i < num_sections - 1:
                        coupling_pos = (
                            seg2_start
                            + (seg2_axis * section_end_mm)
                            - (seg2_axis * bc.inch(coupling_length_in / 2.0))
                        )
                        coupling_name = f"Drain_Coupling_East_{i}"
                        coupling = doc.addObject("Part::Feature", coupling_name)
                        coupling.Shape = Part.makeCylinder(
                            bc.inch(coupling_od_in / 2.0),
                            bc.inch(coupling_length_in),
                            coupling_pos,
                            seg2_axis,
                        )
                        created.append(coupling)

    # SEGMENT 3: Underground horizontal run NORTH from gap middle to tank
    # This runs UNDERGROUND from lateral position (gap middle) to tank inlet (waypoint)
    # Since waypoint_x = lateral_x = 37.0' (straight run), this is just north-south
    depth_at_lateral = depth_start_in + (lateral_run_ft * slope_in_per_ft)
    run_north_ft = abs(waypoint_y_ft - start_y_ft)
    depth_at_tank = depth_at_lateral + (run_north_ft * slope_in_per_ft)

    seg3_start = App.Vector(bc.ft(lateral_x_ft), bc.ft(start_y_ft), bc.inch(-depth_at_lateral))
    seg3_end = App.Vector(bc.ft(waypoint_x_ft), bc.ft(waypoint_y_ft), bc.inch(-depth_at_tank))
    seg3_vec = seg3_end - seg3_start
    seg3_length_mm = seg3_vec.Length

    if seg3_length_mm > 0.1:
        seg3_axis = seg3_vec.normalize()
        seg3_length_ft = seg3_length_mm / 304.8
        num_sections = int(seg3_length_ft / pipe_section_length_ft) + 1

        for i in range(num_sections):
            section_start_mm = bc.ft(i * pipe_section_length_ft)
            section_end_mm = min(bc.ft((i + 1) * pipe_section_length_ft), seg3_length_mm)
            section_length_mm = section_end_mm - section_start_mm

            if section_length_mm > 1.0:
                section_start_pos = seg3_start + (seg3_axis * section_start_mm)
                pipe_name = f"Drain_Pipe_North_{i}"
                pipe = doc.addObject("Part::Feature", pipe_name)
                pipe.Shape = Part.makeCylinder(
                    bc.inch(pipe_od_in / 2.0), section_length_mm, section_start_pos, seg3_axis
                )
                created.append(pipe)

                # Add coupling at end of section (except last)
                if i < num_sections - 1:
                    coupling_pos = (
                        seg3_start
                        + (seg3_axis * section_end_mm)
                        - (seg3_axis * bc.inch(coupling_length_in / 2.0))
                    )
                    coupling_name = f"Drain_Coupling_North_{i}"
                    coupling = doc.addObject("Part::Feature", coupling_name)
                    coupling.Shape = Part.makeCylinder(
                        bc.inch(coupling_od_in / 2.0),
                        bc.inch(coupling_length_in),
                        coupling_pos,
                        seg3_axis,
                    )
                    created.append(coupling)

    return created


def create_pile_sill_seal(
    doc, pile_x_ft, pile_y_ft, pile_size_in, slab_thickness_in, foam_thickness_in=0.5
):
    """
    Create closed-cell foam sill seal around pile penetration through concrete slab.

    Design:
        - 1/2" closed-cell polyethylene foam (typical sill seal material)
        - Forms rectangular frame around pile perimeter
        - Fills gap between pile and concrete cutout
        - Full slab height (6")

    Construction Note:
        - Foam compresses during installation to seal against moisture
        - Prevents concrete from bonding to pile (allows differential movement)
        - Material: Frost King E-O 1/2" x 5.5" sill sealer or equivalent

    Args:
        doc: FreeCAD document
        pile_x_ft: Pile center X position (feet)
        pile_y_ft: Pile center Y position (feet)
        pile_size_in: Pile cross-section size (actual, e.g., 11.25")
        slab_thickness_in: Concrete slab thickness (6")
        foam_thickness_in: Foam thickness (default 0.5" = 1/2")

    Returns:
        Part::Feature object (foam sill seal frame)
    """
    # Foam strip dimensions
    foam_width_in = foam_thickness_in  # 0.5" thick foam
    pile_half_in = pile_size_in / 2.0

    # Create four foam strips forming a square frame around pile
    # Each strip is foam_thickness wide, extends from pile edge outward

    # Build composite shape from four rectangular strips
    strips = []

    # North strip (top edge, +Y side)
    north_strip = Part.makeBox(
        bc.inch(pile_size_in),  # Full pile width
        bc.inch(foam_width_in),  # Foam thickness
        bc.inch(slab_thickness_in),  # Full slab height
    )
    north_strip.Placement.Base = App.Vector(
        bc.ft(pile_x_ft) - bc.inch(pile_half_in),
        bc.ft(pile_y_ft) + bc.inch(pile_half_in),  # Pile edge + foam outward
        bc.inch(-slab_thickness_in),  # Slab bottom
    )
    strips.append(north_strip)

    # South strip (bottom edge, -Y side)
    south_strip = Part.makeBox(
        bc.inch(pile_size_in),
        bc.inch(foam_width_in),
        bc.inch(slab_thickness_in),
    )
    south_strip.Placement.Base = App.Vector(
        bc.ft(pile_x_ft) - bc.inch(pile_half_in),
        bc.ft(pile_y_ft) - bc.inch(pile_half_in) - bc.inch(foam_width_in),  # Pile edge - foam
        bc.inch(-slab_thickness_in),
    )
    strips.append(south_strip)

    # East strip (right edge, +X side) - shortened to avoid corner overlaps
    east_strip = Part.makeBox(
        bc.inch(foam_width_in),
        bc.inch(pile_size_in - 2 * foam_width_in),  # Shortened to fit between N/S strips
        bc.inch(slab_thickness_in),
    )
    east_strip.Placement.Base = App.Vector(
        bc.ft(pile_x_ft) + bc.inch(pile_half_in),  # Pile edge + foam outward
        bc.ft(pile_y_ft) - bc.inch(pile_half_in) + bc.inch(foam_width_in),  # Inset from south strip
        bc.inch(-slab_thickness_in),
    )
    strips.append(east_strip)

    # West strip (left edge, -X side) - shortened to avoid corner overlaps
    west_strip = Part.makeBox(
        bc.inch(foam_width_in),
        bc.inch(pile_size_in - 2 * foam_width_in),  # Shortened to fit between N/S strips
        bc.inch(slab_thickness_in),
    )
    west_strip.Placement.Base = App.Vector(
        bc.ft(pile_x_ft) - bc.inch(pile_half_in) - bc.inch(foam_width_in),  # Pile edge - foam
        bc.ft(pile_y_ft) - bc.inch(pile_half_in) + bc.inch(foam_width_in),  # Inset from south strip
        bc.inch(-slab_thickness_in),
    )
    strips.append(west_strip)

    # Fuse all strips into single shape
    foam_shape = strips[0]
    for strip in strips[1:]:
        foam_shape = foam_shape.fuse(strip)

    # Create FreeCAD object
    foam_obj = doc.addObject("Part::Feature", f"Sill_Seal_Pile_{int(pile_x_ft)}_{int(pile_y_ft)}")
    foam_obj.Shape = foam_shape

    # Attach BOM metadata for material tracking
    # Load catalog to get sill seal row
    catalog_candidates = [
        os.path.join(
            SCRIPT_DIR, "..", "lumber", "lumber_catalog.csv"
        ),  # DesignHouse/lumber/lumber_catalog.csv
    ]
    catalog_path = None
    for candidate in catalog_candidates:
        if os.path.exists(candidate):
            catalog_path = candidate
            break

    if catalog_path:
        from lumber_common import attach_metadata, find_stock, load_catalog

        rows = load_catalog(catalog_path)
        sill_seal_row = find_stock(rows, "sill_seal_0.5x5.5x600")
        if sill_seal_row:
            # Calculate linear feet of foam needed (perimeter)
            perimeter_in = 4 * pile_size_in
            perimeter_ft = perimeter_in / 12.0

            attach_metadata(foam_obj, sill_seal_row, "sill_seal_0.5x5.5x600", supplier="lowes")

            # Add custom property for cut length
            try:
                if "cut_length_ft" not in foam_obj.PropertiesList:
                    foam_obj.addProperty("App::PropertyString", "cut_length_ft")
                foam_obj.cut_length_ft = f"{perimeter_ft:.2f}"
            except Exception:
                pass

    # Color: light gray foam
    try:
        if hasattr(foam_obj, "ViewObject") and foam_obj.ViewObject:
            foam_obj.ViewObject.ShapeColor = (0.8, 0.8, 0.8)  # Light gray
    except Exception:
        pass

    return foam_obj


def create_rebar_grid(
    doc,
    x_start_ft,
    y_start_ft,
    width_ft,
    depth_ft,
    z_position_in,
    spacing_in=12.0,
    rebar_dia_in=0.5,
    exclusion_zones=None,
):
    """
    Create rebar grid for concrete slab reinforcement (#4 rebar @ 12\" OC both ways).

    Design:
        - #4 rebar (1/2\" diameter, Grade 60 steel)
        - 12\" on-center spacing both directions (typical per ACI 332)
        - Grid positioned 2-3\" above bottom of slab (typical chair height)
        - Runs continuous across slab, bent around pile cutouts
        - Skips bars that pass through exclusion zones (e.g., water box cutouts)

    Args:
        doc: FreeCAD document
        x_start_ft: Slab X start position (feet)
        y_start_ft: Slab Y start position (feet)
        width_ft: Slab width (X direction, feet)
        depth_ft: Slab depth (Y direction, feet)
        z_position_in: Z position for rebar (inches above grade, typically -3\" for 6\" slab)
        spacing_in: Rebar spacing on-center (default 12\")
        rebar_dia_in: Rebar diameter (default 0.5\" = #4 rebar)
        exclusion_zones: List of dicts with keys (x_center_ft, y_center_ft, width_ft, depth_ft) for zones to skip

    Returns:
        List of Part::Feature objects (rebar pieces)
    """
    created = []

    # Rebar color: dark gray steel
    rebar_color = (0.3, 0.3, 0.3)

    def intersects_exclusion(bar_position_ft, bar_direction, exclusion_zones):
        """Check if a rebar bar intersects any exclusion zone."""
        if not exclusion_zones:
            return False

        for zone in exclusion_zones:
            zone_x_min = zone["x_center_ft"] - zone["width_ft"] / 2.0
            zone_x_max = zone["x_center_ft"] + zone["width_ft"] / 2.0
            zone_y_min = zone["y_center_ft"] - zone["depth_ft"] / 2.0
            zone_y_max = zone["y_center_ft"] + zone["depth_ft"] / 2.0

            if bar_direction == "X":
                # X-direction bar runs along X axis at fixed Y position
                if zone_y_min <= bar_position_ft <= zone_y_max:
                    return True  # Bar passes through exclusion zone
            else:  # Y-direction
                # Y-direction bar runs along Y axis at fixed X position
                if zone_x_min <= bar_position_ft <= zone_x_max:
                    return True  # Bar passes through exclusion zone

        return False

    # X-direction rebar (runs along X axis, spaced in Y)
    num_x_bars = int(depth_ft * 12.0 / spacing_in) + 1
    for i in range(num_x_bars):
        y_pos_in = i * spacing_in
        y_pos_ft = y_start_ft + (y_pos_in / 12.0)

        # Skip bars that pass through exclusion zones
        if intersects_exclusion(y_pos_ft, "X", exclusion_zones):
            continue

        # Create cylinder along X direction
        start_vec = App.Vector(bc.ft(x_start_ft), bc.ft(y_pos_ft), bc.inch(z_position_in))
        end_vec = App.Vector(bc.ft(x_start_ft + width_ft), bc.ft(y_pos_ft), bc.inch(z_position_in))

        rebar_x = create_pipe_straight(
            doc, f"Rebar_X_{i}", start_vec, end_vec, rebar_dia_in, rebar_color
        )
        if rebar_x:
            created.append(rebar_x)

    # Y-direction rebar (runs along Y axis, spaced in X)
    num_y_bars = int(width_ft * 12.0 / spacing_in) + 1
    for i in range(num_y_bars):
        x_pos_in = i * spacing_in
        x_pos_ft = x_start_ft + (x_pos_in / 12.0)

        # Skip bars that pass through exclusion zones
        if intersects_exclusion(x_pos_ft, "Y", exclusion_zones):
            continue

        # Create cylinder along Y direction
        start_vec = App.Vector(bc.ft(x_pos_ft), bc.ft(y_start_ft), bc.inch(z_position_in))
        end_vec = App.Vector(bc.ft(x_pos_ft), bc.ft(y_start_ft + depth_ft), bc.inch(z_position_in))

        rebar_y = create_pipe_straight(
            doc, f"Rebar_Y_{i}", start_vec, end_vec, rebar_dia_in, rebar_color
        )
        if rebar_y:
            created.append(rebar_y)

    return created


def create_concrete_slab(doc, config, pile_positions_ft=None, pile_size_in=12.0):
    """
    Create concrete slab (6" thick, driveway grade) with pile cutouts.

    Design:
        - 6" thick concrete slab (ACI 332 driveway grade)
        - Cutouts for piles (slab goes AROUND piles, not through them)
        - Bottom of slab at -6" (grade level at Z=0)

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict
        pile_positions_ft: List of (x_ft, y_ft) tuples for pile centers
        pile_size_in: Pile cross-section size (default 12")

    Returns:
        Concrete slab Part::Feature object (with pile cutouts)
    """
    x_start_ft = config["slab_x_start_ft"]
    y_start_ft = config["slab_y_start_ft"]
    width_ft = config["slab_width_ft"]
    depth_ft = config["slab_depth_ft"]
    thickness_in = config["slab_thickness_in"]

    # Create base slab
    slab_box = Part.makeBox(bc.ft(width_ft), bc.ft(depth_ft), bc.inch(thickness_in))
    slab_base = App.Vector(
        bc.ft(x_start_ft), bc.ft(y_start_ft), bc.inch(-thickness_in)  # Bottom of slab at -6"
    )
    slab_box.Placement.Base = slab_base

    # Cut out piles if positions provided
    if pile_positions_ft:
        for pile_x_ft, pile_y_ft in pile_positions_ft:
            # Check if pile is within slab bounds
            if (
                x_start_ft <= pile_x_ft <= x_start_ft + width_ft
                and y_start_ft <= pile_y_ft <= y_start_ft + depth_ft
            ):

                # Create cutout box for pile (minimal clearance for construction)
                cutout_size_in = pile_size_in + 0.125  # 1/8" clearance (minimal for construction)
                cutout_half_in = cutout_size_in / 2.0

                cutout = Part.makeBox(
                    bc.inch(cutout_size_in),
                    bc.inch(cutout_size_in),
                    bc.inch(thickness_in + 1.0),  # Extra height to ensure clean cut
                )
                cutout.Placement.Base = App.Vector(
                    bc.ft(pile_x_ft) - bc.inch(cutout_half_in),
                    bc.ft(pile_y_ft) - bc.inch(cutout_half_in),
                    bc.inch(-thickness_in - 0.5),  # Start below slab
                )

                # Cut pile from slab
                slab_box = slab_box.cut(cutout)

    # Create slab object
    slab = doc.addObject("Part::Feature", "Concrete_Slab_6in")
    slab.Shape = slab_box

    return slab


def create_plumbing_stub_ups(doc, config):
    """
    Create plumbing stub-ups (4" PVC, extend 12" above slab).

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict

    Returns:
        List of plumbing stub-up Part::Feature objects
    """
    stub_positions = config["plumbing_stub_positions"]
    slab_thickness_in = config["slab_thickness_in"]
    stub_height_in = 12.0  # Extend 12" above slab

    stubs = []
    for stub_config in stub_positions:
        name = stub_config["name"]
        x_ft = stub_config["x_ft"]
        y_ft = stub_config["y_ft"]
        diameter_in = stub_config["diameter_in"]

        # Create vertical cylinder (stub-up)
        stub_name = f"Plumbing_Stub_{name}"
        stub = doc.addObject("Part::Feature", stub_name)

        # Cylinder: radius, height
        radius_mm = bc.inch(diameter_in / 2.0)
        height_mm = bc.inch(slab_thickness_in + stub_height_in)

        stub.Shape = Part.makeCylinder(radius_mm, height_mm)
        stub.Placement.Base = App.Vector(
            bc.ft(x_ft), bc.ft(y_ft), bc.inch(-slab_thickness_in)  # Start at bottom of slab
        )
        stubs.append(stub)

    return stubs


def create_pipe_straight(doc, name, start_vec, end_vec, diameter_in, color=None):
    """
    Create straight pipe segment (cylinder) from start to end point.

    Args:
        doc: FreeCAD document
        name: Object name
        start_vec: Start point (App.Vector in mm)
        end_vec: End point (App.Vector in mm)
        diameter_in: Pipe outer diameter (inches)
        color: Optional RGB tuple (0-1 range)

    Returns:
        Part::Feature object (pipe segment)
    """
    direction = end_vec - start_vec
    length_mm = direction.Length

    if length_mm < 0.1:
        return None

    # Create cylinder along direction vector
    pipe = doc.addObject("Part::Feature", name)
    pipe.Shape = Part.makeCylinder(
        bc.inch(diameter_in / 2.0),  # Radius
        length_mm,  # Length
        start_vec,  # Base position
        direction,  # Direction vector
    )

    # Apply color if specified
    if color and hasattr(pipe, "ViewObject") and pipe.ViewObject:
        try:
            pipe.ViewObject.ShapeColor = color
        except Exception:
            pass

    return pipe


def create_90_degree_elbow(
    doc, name, center_vec, diameter_in, bend_radius_in, axis1, axis2, color=None
):
    """
    Create 90-degree elbow fitting (realistic bend radius).

    Design:
        - Torus section swept through 90 degrees
        - Bend radius typically 4x-6x pipe diameter (NEC/IRC minimum)
        - axis1: incoming direction
        - axis2: outgoing direction (90 degrees from axis1)

    Args:
        doc: FreeCAD document
        name: Object name
        center_vec: Center point of bend (App.Vector in mm)
        diameter_in: Pipe outer diameter (inches)
        bend_radius_in: Centerline bend radius (inches)
        axis1: Incoming direction ("+X", "-X", "+Y", "-Y", "+Z", "-Z")
        axis2: Outgoing direction (must be 90° from axis1)
        color: Optional RGB tuple (0-1 range)

    Returns:
        Part::Feature object (90° elbow)
    """
    # Map axis strings to vectors
    axis_map = {
        "+X": App.Vector(1, 0, 0),
        "-X": App.Vector(-1, 0, 0),
        "+Y": App.Vector(0, 1, 0),
        "-Y": App.Vector(0, -1, 0),
        "+Z": App.Vector(0, 0, 1),
        "-Z": App.Vector(0, 0, -1),
    }

    vec1 = axis_map.get(axis1)
    vec2 = axis_map.get(axis2)

    if not vec1 or not vec2:
        App.Console.PrintError(f"[create_90_degree_elbow] Invalid axis: {axis1}, {axis2}\n")
        return None

    # Verify axes are perpendicular
    if abs(vec1.dot(vec2)) > 0.01:
        App.Console.PrintError(
            f"[create_90_degree_elbow] Axes not perpendicular: {axis1}, {axis2}\n"
        )
        return None

    # Create torus and extract 90-degree section
    # Simplified: use two cylinders meeting at 90 degrees (future: proper torus sweep)
    # For now, create a simplified L-shaped connector with two short cylinders

    radius_mm = bc.inch(diameter_in / 2.0)
    bend_radius_mm = bc.inch(bend_radius_in)

    # Arm length: extend from center by bend_radius
    arm_length_mm = bend_radius_mm

    # Cylinder 1: along axis1 direction
    cyl1_start = center_vec - (vec1 * arm_length_mm)
    cyl1 = Part.makeCylinder(radius_mm, arm_length_mm, cyl1_start, vec1)

    # Cylinder 2: along axis2 direction
    cyl2_start = center_vec
    cyl2 = Part.makeCylinder(radius_mm, arm_length_mm, cyl2_start, vec2)

    # Sphere at corner to smooth transition
    corner_sphere = Part.makeSphere(radius_mm, center_vec)

    # Fuse all three shapes
    elbow_shape = cyl1.fuse(cyl2).fuse(corner_sphere)

    elbow = doc.addObject("Part::Feature", name)
    elbow.Shape = elbow_shape

    # Apply color if specified
    if color and hasattr(elbow, "ViewObject") and elbow.ViewObject:
        try:
            elbow.ViewObject.ShapeColor = color
        except Exception:
            pass

    return elbow


def create_water_service_line(doc, config):
    """
    Create water supply line from street to house (1" PVC with lateral routing).

    Routing Strategy:
        1. Vertical stub-up through slab at pile 5,4 west face (X=40.49', Y=44.46875')
        2. Underground horizontal run WEST to gap middle at X=37.0'
        3. Underground horizontal run SOUTH in pile gap from house to street
        All underground segments maintain constant depth (42" below grade per IRC P2603.6)

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict with keys:
            - water_service_line_diameter_in: Pipe diameter (1")
            - water_service_depth_in: Burial depth (42")
            - water_stub_x_ft, water_stub_y_ft: Stub-up position at pile west face
            - water_lateral_x_ft: X position for north-south run (gap middle)
            - water_entry_from_street_y_ft: Street connection point

    Returns:
        List of Part::Feature objects (line segments for water service)
    """
    diameter_in = config["water_service_line_diameter_in"]  # 1"
    depth_in = config["water_service_depth_in"]  # 42"
    stub_x_ft = config["water_stub_x_ft"]
    stub_y_ft = config["water_stub_y_ft"]
    lateral_x_ft = config.get("water_lateral_x_ft", stub_x_ft)
    street_y_ft = config["water_entry_from_street_y_ft"]

    # Bend radius: 6x diameter (typical for 1" PVC per IRC/NEC)
    bend_radius_in = diameter_in * 6.0

    # Color: blue for water
    water_color = (0.2, 0.4, 0.8)

    created = []

    # SEGMENT 1a: Vertical stub-up from underground to shutoff valve (at slab top, 0")
    shutoff_z_in = 0.0  # Shutoff valve at slab surface
    seg1a_start = App.Vector(bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(-depth_in))
    seg1a_end = App.Vector(bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(shutoff_z_in))
    water_stub_lower = create_pipe_straight(
        doc, "Water_Stub_Up_Lower", seg1a_start, seg1a_end, diameter_in, water_color
    )
    if water_stub_lower:
        created.append(water_stub_lower)

    # SEGMENT 1b: Shutoff valve at slab surface
    # This allows shutting off water to the house and draining the system via the drain bib
    shutoff_valve = create_water_shutoff_valve(
        doc, "Water_Shutoff_House", stub_x_ft, stub_y_ft, shutoff_z_in + 3.0, diameter_in
    )
    created.append(shutoff_valve)

    # SEGMENT 1c: Short vertical pipe from shutoff to drain hose bib
    drain_bib_z_in = shutoff_z_in + 6.0  # Drain bib 6" above shutoff
    seg1c_start = App.Vector(
        bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(shutoff_z_in + 1.5)
    )  # After shutoff
    seg1c_end = App.Vector(bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(drain_bib_z_in))
    water_stub_mid = create_pipe_straight(
        doc, "Water_Stub_Up_Mid", seg1c_start, seg1c_end, diameter_in, water_color
    )
    if water_stub_mid:
        created.append(water_stub_mid)

    # SEGMENT 1d: Drain hose bib (allows draining entire house water system)
    drain_bib = create_hose_bib(
        doc, "Water_Drain_Bib", stub_x_ft, stub_y_ft, drain_bib_z_in, diameter_in
    )
    created.append(drain_bib)

    # SEGMENT 1e: Vertical continuation from drain bib to house entry (12" above slab)
    seg1e_start = App.Vector(
        bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(drain_bib_z_in + 1.5)
    )  # After drain bib
    seg1e_end = App.Vector(
        bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(12.0)
    )  # 12" above slab (house entry)
    water_stub_upper = create_pipe_straight(
        doc, "Water_Stub_Up_Upper", seg1e_start, seg1e_end, diameter_in, water_color
    )
    if water_stub_upper:
        created.append(water_stub_upper)

    # SEGMENT 2: Underground horizontal WEST from stub to gap middle
    if abs(lateral_x_ft - stub_x_ft) > 0.1:
        seg2_start = App.Vector(bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(-depth_in))
        seg2_end = App.Vector(bc.ft(lateral_x_ft), bc.ft(stub_y_ft), bc.inch(-depth_in))
        water_west = create_pipe_straight(
            doc, "Water_Line_West", seg2_start, seg2_end, diameter_in, water_color
        )
        if water_west:
            created.append(water_west)

    # SEGMENT 3: Underground horizontal SOUTH in pile gap from house to street
    seg3_start = App.Vector(bc.ft(lateral_x_ft), bc.ft(stub_y_ft), bc.inch(-depth_in))
    seg3_end = App.Vector(bc.ft(lateral_x_ft), bc.ft(street_y_ft), bc.inch(-depth_in))
    water_south = create_pipe_straight(
        doc, "Water_Line_South", seg3_start, seg3_end, diameter_in, water_color
    )
    if water_south:
        created.append(water_south)

    return created


def create_electrical_service_line(doc, config):
    """
    Create electrical service conduit from street to house (2.5" conduit with lateral routing).

    Routing Strategy:
        1. Vertical stub-up through slab at pile 4,4 east face (X=33.51', Y=44.46875')
        2. Underground horizontal run EAST to gap middle at X=37.0'
        3. Underground horizontal run SOUTH in pile gap from house to street
        All underground segments maintain constant depth (24" below grade per NEC 300.5)
        NOTE: Vertical stub-up is created separately by create_electrical_stub_up()

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict with keys:
            - electrical_service_conduit_diameter_in: Conduit diameter (2.5" for 200A)
            - electrical_service_depth_in: Burial depth (24")
            - electrical_equipment_x_ft, electrical_equipment_y_ft: Stub-up position (equipment mounting location)
            - electrical_lateral_x_ft: X position for north-south run (gap middle)
            - electrical_entry_from_street_y_ft: Street connection point

    Returns:
        List of Part::Feature objects (line segments for electrical service)
    """
    diameter_in = config["electrical_service_conduit_diameter_in"]  # 2.5" for 200A service
    depth_in = config["electrical_service_depth_in"]  # 24"
    # Use equipment position (NOT offset stub position) to align with vertical stub-up
    stub_x_ft = config.get("electrical_equipment_x_ft", config.get("electrical_stub_x_ft", 33.51))
    stub_y_ft = config.get(
        "electrical_equipment_y_ft", config.get("electrical_stub_y_ft", 44.46875)
    )
    lateral_x_ft = config.get("electrical_lateral_x_ft", stub_x_ft)
    street_y_ft = config["electrical_entry_from_street_y_ft"]

    # Bend radius: 6x diameter (NEC 300.5, IRC E3802.3 for PVC conduit)
    bend_radius_in = diameter_in * 6.0

    # Color: orange for electrical (standard conduit color)
    elec_color = (1.0, 0.5, 0.0)

    created = []

    # SEGMENT 1: Vertical stub-up from underground to slab bottom
    # This connects the underground horizontal line to the separate above-ground stub-up
    # Running from underground depth (-24") up to slab bottom (-6")
    # NOTE: The above-ground stub (Electrical_Stub_Up_2in) is offset by +radius_mm in X,
    # so we need to match that offset here for alignment
    slab_thickness_in = 6.0  # Standard slab thickness
    radius_mm = bc.inch(diameter_in / 2.0)
    seg1_start = App.Vector(bc.ft(stub_x_ft) + radius_mm, bc.ft(stub_y_ft), bc.inch(-depth_in))
    seg1_end = App.Vector(
        bc.ft(stub_x_ft) + radius_mm, bc.ft(stub_y_ft), bc.inch(-slab_thickness_in)
    )
    elec_stub_underground = create_pipe_straight(
        doc, "Electrical_Line_Vertical_Underground", seg1_start, seg1_end, diameter_in, elec_color
    )
    if elec_stub_underground:
        created.append(elec_stub_underground)

    # SEGMENT 2: Underground horizontal EAST from stub to gap middle
    # NOTE: Start point uses radius offset to align with vertical stub, end point at lateral position
    if abs(lateral_x_ft - stub_x_ft) > 0.1:
        seg2_start = App.Vector(bc.ft(stub_x_ft) + radius_mm, bc.ft(stub_y_ft), bc.inch(-depth_in))
        seg2_end = App.Vector(bc.ft(lateral_x_ft), bc.ft(stub_y_ft), bc.inch(-depth_in))
        elec_east = create_pipe_straight(
            doc, "Electrical_Line_East", seg2_start, seg2_end, diameter_in, elec_color
        )
        if elec_east:
            created.append(elec_east)

    # SEGMENT 3: Underground horizontal SOUTH in pile gap from house to street
    # NOTE: Both start and end at lateral position (no radius offset needed here)
    seg3_start = App.Vector(bc.ft(lateral_x_ft), bc.ft(stub_y_ft), bc.inch(-depth_in))
    seg3_end = App.Vector(bc.ft(lateral_x_ft), bc.ft(street_y_ft), bc.inch(-depth_in))
    elec_south = create_pipe_straight(
        doc, "Electrical_Line_South", seg3_start, seg3_end, diameter_in, elec_color
    )
    if elec_south:
        created.append(elec_south)

    return created


def create_water_stub_up(doc, config):
    """
    Create water supply stub-up (1" PVC, extend 12" above slab).

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict

    Returns:
        Water stub-up Part::Feature object
    """
    diameter_in = config["water_service_line_diameter_in"]
    x_ft = config["water_stub_x_ft"]
    y_ft = config["water_stub_y_ft"]
    slab_thickness_in = config["slab_thickness_in"]
    stub_height_in = 12.0  # Extend 12" above slab

    stub = doc.addObject("Part::Feature", "Water_Stub_Up_1in")
    radius_mm = bc.inch(diameter_in / 2.0)
    height_mm = bc.inch(slab_thickness_in + stub_height_in)

    stub.Shape = Part.makeCylinder(radius_mm, height_mm)
    stub.Placement.Base = App.Vector(
        bc.ft(x_ft), bc.ft(y_ft), bc.inch(-slab_thickness_in)  # Start at bottom of slab
    )

    return stub


def create_electrical_stub_up(doc, config):
    """
    Create electrical service stub-up (2" conduit, extend to meter box bottom).

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict

    Returns:
        Electrical stub-up Part::Feature object
    """
    diameter_in = config["electrical_service_conduit_diameter_in"]
    x_ft = config.get("electrical_equipment_x_ft", config["electrical_stub_x_ft"])
    y_ft = config.get("electrical_equipment_y_ft", config["electrical_stub_y_ft"])
    slab_thickness_in = config["slab_thickness_in"]
    meter_box_offset_z_in = config.get("meter_box_offset_z_in", 48.0)  # Meter bottom height
    stub_height_in = meter_box_offset_z_in  # Extend to meter box bottom

    stub = doc.addObject("Part::Feature", "Electrical_Stub_Up_2in")
    radius_mm = bc.inch(diameter_in / 2.0)
    height_mm = bc.inch(slab_thickness_in + stub_height_in)

    stub.Shape = Part.makeCylinder(radius_mm, height_mm)
    # Position: west face of pipe at pile east face (x_ft), center at pile center Y (y_ft)
    # Cylinder center is offset by radius in X to align west face with pile east face
    stub.Placement.Base = App.Vector(
        bc.ft(x_ft) + radius_mm,  # Offset by radius so west face aligns with pile east face
        bc.ft(y_ft),  # Center at pile center Y
        bc.inch(-slab_thickness_in),  # Start at bottom of slab
    )

    return stub


def create_electrical_meter_box(doc, config):
    """
    Create electrical meter box (200A service).

    Typical dimensions for 200A meter box:
    - Width: 12" to 18" (using 14")
    - Height: 24" to 30" (using 28")
    - Depth: 4" to 6" (using 5")

    Position: Mounted at same location as electrical stub-up (pile 4,4).

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict with keys:
            - electrical_equipment_x_ft, electrical_equipment_y_ft: Equipment mounting position
            - meter_box_offset_z_in: Height above slab (default: 48" - bottom at 4')

    Returns:
        Part::Feature object (meter box)
    """
    x_ft = config.get("electrical_equipment_x_ft", config["electrical_stub_x_ft"])
    y_ft = config.get("electrical_equipment_y_ft", config["electrical_stub_y_ft"])
    offset_z_in = config.get("meter_box_offset_z_in", 48.0)  # Bottom at 4' above slab

    # Meter box dimensions (typical 200A residential meter)
    width_in = 14.0
    height_in = 28.0
    depth_in = 5.0

    meter_box = doc.addObject("Part::Feature", "Electrical_Meter_Box_200A")
    # Orient for east-facing mount: X=depth, Y=width, Z=height
    meter_box.Shape = Part.makeBox(
        bc.inch(depth_in),  # X: depth (shallow, projects east from pile)
        bc.inch(width_in),  # Y: width (runs north-south)
        bc.inch(height_in),  # Z: height (vertical)
    )
    # Position meter box centered on stub-up X/Y position, facing east
    meter_box.Placement.Base = App.Vector(
        bc.ft(x_ft),  # X: align to pile east face
        bc.ft(y_ft) - bc.inch(width_in / 2.0),  # Y: center on stub-up Y
        bc.inch(offset_z_in),
    )

    return meter_box


def create_electrical_disconnect(doc, config):
    """
    Create electrical disconnect switch (200A service).

    Typical dimensions for 200A disconnect:
    - Width: 12"
    - Height: 20"
    - Depth: 6"

    NEC 230.70: Service disconnect must be accessible and labeled.
    Position: Mounted above meter box (stacked vertically).

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict with keys:
            - electrical_equipment_x_ft, electrical_equipment_y_ft: Equipment mounting position
            - meter_box_offset_z_in: Meter bottom height (default: 48")
            - disconnect_offset_z_in: Disconnect bottom height (calculated from meter top)

    Returns:
        Part::Feature object (disconnect switch)
    """
    x_ft = config.get("electrical_equipment_x_ft", config["electrical_stub_x_ft"])
    y_ft = config.get("electrical_equipment_y_ft", config["electrical_stub_y_ft"])
    meter_bottom_z_in = config.get("meter_box_offset_z_in", 48.0)
    meter_height_in = 28.0  # From meter box function

    # Disconnect dimensions (200A fused disconnect or breaker-type)
    width_in = 12.0
    height_in = 20.0
    depth_in = 6.0

    # Position disconnect above meter (with small gap for wiring)
    gap_in = 2.0
    disconnect_bottom_z_in = meter_bottom_z_in + meter_height_in + gap_in

    disconnect = doc.addObject("Part::Feature", "Electrical_Disconnect_200A")
    # Orient for east-facing mount: X=depth, Y=width, Z=height
    disconnect.Shape = Part.makeBox(
        bc.inch(depth_in),  # X: depth (shallow, projects east from pile)
        bc.inch(width_in),  # Y: width (runs north-south)
        bc.inch(height_in),  # Z: height (vertical)
    )
    # Position disconnect centered on stub-up X/Y, stacked above meter, facing east
    disconnect.Placement.Base = App.Vector(
        bc.ft(x_ft),  # X: align to pile east face
        bc.ft(y_ft) - bc.inch(width_in / 2.0),  # Y: center on stub-up Y
        bc.inch(disconnect_bottom_z_in),
    )

    return disconnect


def create_electrical_panel(doc, config):
    """
    Create main electrical panel (200A service, 40-circuit panel).

    Typical dimensions for 200A main panel:
    - Width: 14" to 20" (using 17.5")
    - Height: 40" to 48" (using 42")
    - Depth: 3.5" to 5.5" (using 4.5", flush-mount)

    NEC 110.26: Panel must have 36" working clearance in front.
    Position: Temporarily stacked above disconnect (will move to house interior later).

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict with keys:
            - electrical_stub_x_ft, electrical_stub_y_ft: Stub-up position
            - meter_box_offset_z_in: Meter bottom height (default: 48")
            - panel_offset_z_in: Panel bottom height (calculated from disconnect top)

    Returns:
        Part::Feature object (electrical panel)
    """
    x_ft = config.get("electrical_equipment_x_ft", config["electrical_stub_x_ft"])
    y_ft = config.get("electrical_equipment_y_ft", config["electrical_stub_y_ft"])
    meter_bottom_z_in = config.get("meter_box_offset_z_in", 48.0)
    meter_height_in = 28.0
    disconnect_height_in = 20.0
    gap_in = 2.0  # Gap between components

    # Panel dimensions (200A main breaker, 40-circuit load center)
    width_in = 17.5
    height_in = 42.0
    depth_in = 4.5  # Recessed/flush mount

    # Position panel above disconnect (temporary location)
    panel_bottom_z_in = meter_bottom_z_in + meter_height_in + gap_in + disconnect_height_in + gap_in

    panel = doc.addObject("Part::Feature", "Electrical_Panel_200A_40ckt")
    # Orient for east-facing mount: X=depth, Y=width, Z=height
    panel.Shape = Part.makeBox(
        bc.inch(depth_in),  # X: depth (shallow, projects east from pile)
        bc.inch(width_in),  # Y: width (runs north-south)
        bc.inch(height_in),  # Z: height (vertical)
    )
    # Position panel centered on stub-up X/Y, stacked above disconnect, facing east
    panel.Placement.Base = App.Vector(
        bc.ft(x_ft),  # X: align to pile east face
        bc.ft(y_ft) - bc.inch(width_in / 2.0),  # Y: center on stub-up Y
        bc.inch(panel_bottom_z_in),
    )

    return panel


def create_water_meter_box(doc, config):
    """
    Create water meter box at street (utility company access).

    Typical dimensions for residential water meter box:
    - Width: 18" to 24" (using 20")
    - Length: 24" to 30" (using 26")
    - Depth: 18" to 24" (using 20", underground vault)

    Position: At street connection point (Y=0), centered on water service line.

    IRC P2603.5.1: Water meter must be accessible for reading and maintenance.
    Typically installed in underground vault (meter box) at or near property line.

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict with keys:
            - water_lateral_x_ft: X position for north-south water run (gap middle)
            - water_entry_from_street_y_ft: Street connection point (Y=0)
            - water_meter_depth_in: Burial depth for top of meter box (default: 12" below grade)

    Returns:
        Part::Feature object (meter box vault)
    """
    x_ft = config.get("water_lateral_x_ft", 37.0)  # Centered on north-south water line
    street_y_ft = config["water_entry_from_street_y_ft"]  # Y=0 at street
    water_line_depth_in = config.get("water_service_depth_in", 42.0)  # Water line depth (42")

    # Meter box vault dimensions (underground concrete/polymer vault)
    width_in = 20.0  # X direction (across water line)
    length_in = 26.0  # Y direction (along water line)
    depth_in = 20.0  # Z direction (vault depth)

    meter_box = doc.addObject("Part::Feature", "Water_Meter_Box")
    # Underground vault: positioned below grade
    meter_box.Shape = Part.makeBox(
        bc.inch(width_in),  # X: width (perpendicular to water line)
        bc.inch(length_in),  # Y: length (along water line)
        bc.inch(depth_in),  # Z: depth (underground)
    )
    # Position meter box centered on water line (water line passes through center of box)
    # Box centered vertically on water line at Z=-42"
    meter_box.Placement.Base = App.Vector(
        bc.ft(x_ft) - bc.inch(width_in / 2.0),  # X: center on water line
        bc.ft(street_y_ft) - bc.inch(length_in / 2.0),  # Y: center at street
        bc.inch(-water_line_depth_in - depth_in / 2.0),  # Z: center box on water line depth
    )

    # Color: gray concrete vault
    try:
        if hasattr(meter_box, "ViewObject") and meter_box.ViewObject:
            meter_box.ViewObject.ShapeColor = (0.6, 0.6, 0.6)  # Gray concrete
    except Exception:
        pass

    return meter_box


def create_water_shutoff_box(doc, config):
    """
    Create customer water shutoff valve box (near water meter at street).

    Typical dimensions for customer shutoff box:
    - Width: 12" to 14" (using 13")
    - Length: 14" to 16" (using 15")
    - Depth: 12" to 18" (using 14", underground vault)

    Position: Near water meter at street (within 1-5' per typical code).
    Customer shutoff typically installed immediately after utility meter.

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict with keys:
            - water_lateral_x_ft: X position for water line (gap middle)
            - water_entry_from_street_y_ft: Street connection point (Y=0)
            - water_shutoff_offset_y_ft: Offset from meter (default: 3.0' = 3' north of meter toward house)
            - water_shutoff_depth_in: Burial depth for top of box (default: 12" below grade)

    Returns:
        Part::Feature object (shutoff valve box)
    """
    x_ft = config.get("water_lateral_x_ft", 37.0)  # Same X as meter (on water line)
    street_y_ft = config["water_entry_from_street_y_ft"]  # Y=0 at street
    shutoff_offset_y_ft = config.get(
        "water_shutoff_offset_y_ft", 3.0
    )  # 3' north of meter (toward house)
    water_line_depth_in = config.get("water_service_depth_in", 42.0)  # Water line depth (42")

    # Shutoff box dimensions (smaller underground vault)
    width_in = 13.0  # X direction
    length_in = 15.0  # Y direction
    depth_in = 14.0  # Z direction (vault depth)

    shutoff_box = doc.addObject("Part::Feature", "Water_Shutoff_Box")
    # Underground vault: positioned below grade
    shutoff_box.Shape = Part.makeBox(
        bc.inch(width_in),  # X: width
        bc.inch(length_in),  # Y: length
        bc.inch(depth_in),  # Z: depth (underground)
    )
    # Position shutoff box centered on water line (water line passes through center of box)
    # Box centered vertically on water line at Z=-42"
    shutoff_box.Placement.Base = App.Vector(
        bc.ft(x_ft) - bc.inch(width_in / 2.0),  # X: center on water line
        bc.ft(street_y_ft + shutoff_offset_y_ft) - bc.inch(length_in / 2.0),  # Y: offset from meter
        bc.inch(-water_line_depth_in - depth_in / 2.0),  # Z: center box on water line depth
    )

    # Color: gray concrete vault (slightly lighter than meter box)
    try:
        if hasattr(shutoff_box, "ViewObject") and shutoff_box.ViewObject:
            shutoff_box.ViewObject.ShapeColor = (0.65, 0.65, 0.65)  # Light gray
    except Exception:
        pass

    return shutoff_box


def create_water_shutoff_valve(doc, name, x_ft, y_ft, z_in, diameter_in=1.0):
    """
    Create a water shutoff valve (ball valve or gate valve).

    Typical residential shutoff valve:
    - Body length: 2.5" to 3.5" (using 3.0")
    - Body diameter: 1.5x pipe diameter
    - Handle extends perpendicular to flow

    Args:
        doc: FreeCAD document
        name: Object name
        x_ft, y_ft: Horizontal position (feet)
        z_in: Vertical position at valve center (inches)
        diameter_in: Pipe diameter (inches)

    Returns:
        Part::Feature object (shutoff valve)
    """
    # Valve body dimensions
    body_length_in = 3.0  # Along pipe axis (vertical)
    body_diameter_in = diameter_in * 1.5  # Valve body wider than pipe
    handle_length_in = 4.0  # Handle extends perpendicular

    # Create valve body (cylinder)
    valve = doc.addObject("Part::Feature", name)
    valve_body = Part.makeCylinder(
        bc.inch(body_diameter_in / 2.0),  # Radius
        bc.inch(body_length_in),  # Height (along Z)
        App.Vector(
            bc.ft(x_ft), bc.ft(y_ft), bc.inch(z_in - body_length_in / 2.0)
        ),  # Center at z_in
        App.Vector(0, 0, 1),  # Vertical orientation
    )

    # Create handle (small cylinder perpendicular to valve body)
    handle = Part.makeCylinder(
        bc.inch(0.25),  # Handle diameter
        bc.inch(handle_length_in),  # Handle length
        App.Vector(
            bc.ft(x_ft) - bc.inch(handle_length_in / 2.0), bc.ft(y_ft), bc.inch(z_in)
        ),  # Extends in +X
        App.Vector(1, 0, 0),  # Horizontal orientation
    )

    # Combine body and handle
    valve.Shape = valve_body.fuse(handle)

    # Color: brass/bronze for valve
    try:
        valve.ViewObject.ShapeColor = (0.8, 0.6, 0.2)  # Brass color
        valve.ViewObject.Transparency = 0
    except Exception:
        pass

    return valve


def create_hose_bib(doc, name, x_ft, y_ft, z_in, diameter_in=0.75, angle_deg=45):
    """
    Create a hose bib (outdoor faucet).

    Typical residential hose bib:
    - Body length: 4" to 6" (using 5.0")
    - Spout extends at 45° downward angle
    - Spout diameter: 0.75" (standard garden hose thread)

    Args:
        doc: FreeCAD document
        name: Object name
        x_ft, y_ft: Horizontal position (feet)
        z_in: Vertical position at connection point (inches)
        diameter_in: Connection diameter (inches)
        angle_deg: Spout angle from horizontal (45° typical)

    Returns:
        Part::Feature object (hose bib)
    """
    # Hose bib dimensions
    body_length_in = 5.0  # Main body length
    spout_length_in = 3.0  # Spout extension
    spout_diameter_in = 0.75  # Garden hose thread

    # Create valve body (horizontal cylinder)
    bib = doc.addObject("Part::Feature", name)
    body = Part.makeCylinder(
        bc.inch(diameter_in / 2.0),  # Body radius
        bc.inch(body_length_in),  # Body length
        App.Vector(bc.ft(x_ft), bc.ft(y_ft), bc.inch(z_in)),  # Horizontal along +X
        App.Vector(1, 0, 0),  # Horizontal orientation
    )

    # Create spout (angled downward at 45°)
    import math

    angle_rad = math.radians(angle_deg)
    spout_dx_in = spout_length_in * math.cos(angle_rad)
    spout_dz_in = -spout_length_in * math.sin(angle_rad)  # Downward

    spout = Part.makeCylinder(
        bc.inch(spout_diameter_in / 2.0),  # Spout radius
        bc.inch(spout_length_in),  # Spout length
        App.Vector(
            bc.ft(x_ft) + bc.inch(body_length_in), bc.ft(y_ft), bc.inch(z_in)
        ),  # At body end
        App.Vector(math.cos(angle_rad), 0, -math.sin(angle_rad)),  # Angled downward
    )

    # Combine body and spout
    bib.Shape = body.fuse(spout)

    # Color: brass for hose bib
    try:
        bib.ViewObject.ShapeColor = (0.8, 0.6, 0.2)  # Brass color
        bib.ViewObject.Transparency = 0
    except Exception:
        pass

    return bib


def create_foot_wash_station(doc, config, foundation_config, lot_config):
    """
    Create foot washing station on pile 5,6 north face (near stairs area).

    Position: North face of pile 5,6 (column 5, row 6)

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict with water service configuration
        foundation_config: FOUNDATION config dict with pile positions
        lot_config: LOT config dict for calculating pile positions

    Returns:
        List of Part::Feature objects (foot wash supply line and fixture)
    """
    # Use same pile positioning logic as pile hose bibs
    water_x_ft = config.get("water_lateral_x_ft", 37.0)
    water_depth_in = config["water_service_depth_in"]
    branch_diameter_in = 0.75

    pile_spacing_x_ft = foundation_config["pile_spacing_x_ft"]
    pile_spacing_y_ft = foundation_config["pile_spacing_y_ft"]
    pile_grid_x = foundation_config["pile_grid_x"]
    actual_pile_size_in = foundation_config.get("pile_actual_size_in", 11.25)

    lot_width_ft = lot_config["width_ft"]
    front_setback_ft = lot_config["front_setback_ft"]
    total_pile_span_x_ft = (pile_grid_x - 1) * pile_spacing_x_ft
    pile_start_x_ft = (lot_width_ft - total_pile_span_x_ft) / 2.0
    pile_thickness_ft = actual_pile_size_in / 12.0
    pile_start_y_ft = front_setback_ft + (pile_thickness_ft / 2.0)

    # Pile 5,6 position (column 4, row 5 in 0-based indexing)
    pile_i = 4
    pile_j = 5
    pile_center_x_ft = pile_start_x_ft + (pile_i * pile_spacing_x_ft)
    pile_center_y_ft = pile_start_y_ft + (pile_j * pile_spacing_y_ft)

    # North face position
    stub_x_ft = pile_center_x_ft
    stub_y_ft = (
        pile_center_y_ft + (actual_pile_size_in / 2.0) / 12.0 + (branch_diameter_in / 2.0) / 12.0
    )

    water_color = (0.2, 0.4, 0.8)
    created = []

    # Branch routing (same 3-segment strategy as pile hose bibs)
    water_stub_y_ft = config.get("water_stub_y_ft", 44.46875)
    connection_y_ft = water_stub_y_ft if stub_y_ft > water_stub_y_ft else stub_y_ft
    gap_y_ft = stub_y_ft - 4.0

    # SEGMENT 1: NS along main line
    seg1_start = App.Vector(bc.ft(water_x_ft), bc.ft(connection_y_ft), bc.inch(-water_depth_in))
    seg1_end = App.Vector(bc.ft(water_x_ft), bc.ft(gap_y_ft), bc.inch(-water_depth_in))
    branch_ns = create_pipe_straight(
        doc, "Foot_Wash_Branch_NS", seg1_start, seg1_end, branch_diameter_in, water_color
    )
    if branch_ns:
        created.append(branch_ns)

    # SEGMENT 2: EW to pile
    seg2_start = App.Vector(bc.ft(water_x_ft), bc.ft(gap_y_ft), bc.inch(-water_depth_in))
    seg2_end = App.Vector(bc.ft(stub_x_ft), bc.ft(gap_y_ft), bc.inch(-water_depth_in))
    branch_ew = create_pipe_straight(
        doc, "Foot_Wash_Branch_EW", seg2_start, seg2_end, branch_diameter_in, water_color
    )
    if branch_ew:
        created.append(branch_ew)

    # SEGMENT 3: NS to pile north face
    seg3_start = App.Vector(bc.ft(stub_x_ft), bc.ft(gap_y_ft), bc.inch(-water_depth_in))
    seg3_end = App.Vector(bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(-water_depth_in))
    branch_ns2 = create_pipe_straight(
        doc, "Foot_Wash_Branch_NS2", seg3_start, seg3_end, branch_diameter_in, water_color
    )
    if branch_ns2:
        created.append(branch_ns2)

    # SEGMENT 4: Vertical stub-up
    foot_wash_height_in = 12.0
    stub_start = App.Vector(bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(-water_depth_in))
    stub_end = App.Vector(bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(foot_wash_height_in))
    foot_wash_stub = create_pipe_straight(
        doc, "Foot_Wash_Stub_Up", stub_start, stub_end, branch_diameter_in, water_color
    )
    if foot_wash_stub:
        created.append(foot_wash_stub)

    # SEGMENT 5: Hose bib
    foot_wash_bib = create_hose_bib(
        doc, "Foot_Wash_Bib", stub_x_ft, stub_y_ft, foot_wash_height_in, branch_diameter_in
    )
    created.append(foot_wash_bib)

    return created


def create_pile_hose_bibs(doc, utilities_config, foundation_config, lot_config):
    """
    Create hose bibs mounted on pile faces at property corners.

    Position: West faces of pile 1,1 and pile 1,8 (south-west corners)
              East faces of pile 5,1 and pile 5,8 (south-east and north-east corners)

    Each hose bib has:
    - Underground branch line from main water supply (at 42" depth)
    - Vertical stub-up to pile face
    - Hose bib fixture mounted on pile face at accessible height (48")

    Args:
        doc: FreeCAD document
        utilities_config: UTILITIES config dict with water service configuration
        foundation_config: FOUNDATION config dict with pile positions
        lot_config: LOT config dict for calculating pile start positions

    Returns:
        List of Part::Feature objects (branch lines, stub-ups, and hose bibs)
    """
    # Water service configuration
    water_lateral_x_ft = utilities_config.get("water_lateral_x_ft", 37.0)  # Main line X position
    water_depth_in = utilities_config["water_service_depth_in"]  # 42" underground
    branch_diameter_in = 0.75  # 3/4" branch for hose bibs

    # Foundation pile configuration
    pile_spacing_x_ft = foundation_config["pile_spacing_x_ft"]  # 8'
    pile_spacing_y_ft = foundation_config["pile_spacing_y_ft"]  # 8'
    pile_grid_x = foundation_config["pile_grid_x"]  # 5 piles
    pile_size_in = foundation_config.get("pile_size_in", 12.0)  # 12" nominal
    actual_pile_size_in = foundation_config.get("pile_actual_size_in", 11.25)  # 11.25" actual

    # Calculate pile start positions (same logic as in BeachHouse Template.FCMacro)
    lot_width_ft = lot_config["width_ft"]  # 50'
    front_setback_ft = lot_config["front_setback_ft"]  # 20'

    # X start: center piles on lot width
    total_pile_span_x_ft = (pile_grid_x - 1) * pile_spacing_x_ft  # 4 gaps × 8' = 32'
    pile_start_x_ft = (lot_width_ft - total_pile_span_x_ft) / 2.0  # (50' - 32') / 2 = 9'

    # Y start: front setback + pile center offset
    pile_thickness_ft = actual_pile_size_in / 12.0
    pile_start_y_ft = front_setback_ft + (pile_thickness_ft / 2.0)  # 20' + 0.46875' = 20.46875'

    # Color: blue for water
    water_color = (0.2, 0.4, 0.8)

    created = []

    # Define hose bib positions at pile corners
    # Pile indices (i, j) where i=column (0-4), j=row (0-7)
    hose_bib_positions = [
        {
            "name": "HoseBib_SW_Front",
            "pile_i": 0,
            "pile_j": 0,
            "face": "west",
        },  # Pile 1,1 west face
        {"name": "HoseBib_SW_Back", "pile_i": 0, "pile_j": 7, "face": "west"},  # Pile 1,8 west face
        {
            "name": "HoseBib_SE_Front",
            "pile_i": 4,
            "pile_j": 0,
            "face": "east",
        },  # Pile 5,1 east face
        {"name": "HoseBib_SE_Back", "pile_i": 4, "pile_j": 7, "face": "east"},  # Pile 5,8 east face
    ]

    for bib_config in hose_bib_positions:
        name = bib_config["name"]
        pile_i = bib_config["pile_i"]
        pile_j = bib_config["pile_j"]
        face = bib_config["face"]

        # Calculate pile center position
        pile_center_x_ft = pile_start_x_ft + (pile_i * pile_spacing_x_ft)
        pile_center_y_ft = pile_start_y_ft + (pile_j * pile_spacing_y_ft)

        # Calculate stub-up position at pile face
        if face == "west":
            stub_x_ft = (
                pile_center_x_ft
                - (actual_pile_size_in / 2.0) / 12.0
                - (branch_diameter_in / 2.0) / 12.0
            )
        else:  # east
            stub_x_ft = (
                pile_center_x_ft
                + (actual_pile_size_in / 2.0) / 12.0
                + (branch_diameter_in / 2.0) / 12.0
            )
        stub_y_ft = pile_center_y_ft

        # Branch line routing: Avoid piles by routing in gap between pile rows
        # Strategy: Route to main water line, which runs from street (Y=0) to house stub (Y=44.47')
        # For piles beyond the main line (Y > 44.47'), connect at the house stub position
        # Piles are at Y positions: 20.47', 28.47', 36.47', 44.47', 52.47', 60.47', 68.47', 76.47'
        # Clear gaps (between piles) are approximately 4' south of each pile center

        # Determine connection point on main water line
        # Main line runs from Y=0 (street) to Y=44.47' (house stub)
        # If stub is beyond main line, connect at house stub position
        water_stub_y_ft = utilities_config.get("water_stub_y_ft", 44.46875)
        if stub_y_ft > water_stub_y_ft:
            # Pile is north of house stub - connect at house stub position
            connection_y_ft = water_stub_y_ft
        else:
            # Pile is south of or at house stub - connect directly at pile Y
            connection_y_ft = stub_y_ft

        # Use a waypoint 4' south of pile Y to route in the gap between pile rows
        gap_y_ft = stub_y_ft - 4.0  # 4' south of pile center = in the gap between rows

        # SEGMENT 1: North-south along main water line from connection point to gap Y position
        seg1_start = App.Vector(
            bc.ft(water_lateral_x_ft), bc.ft(connection_y_ft), bc.inch(-water_depth_in)
        )
        seg1_end = App.Vector(bc.ft(water_lateral_x_ft), bc.ft(gap_y_ft), bc.inch(-water_depth_in))
        branch_ns = create_pipe_straight(
            doc, f"{name}_Branch_NS", seg1_start, seg1_end, branch_diameter_in, water_color
        )
        if branch_ns:
            created.append(branch_ns)

        # SEGMENT 2: East-west from main line to stub X position (at gap Y, avoiding piles)
        seg2_start = App.Vector(
            bc.ft(water_lateral_x_ft), bc.ft(gap_y_ft), bc.inch(-water_depth_in)
        )
        seg2_end = App.Vector(bc.ft(stub_x_ft), bc.ft(gap_y_ft), bc.inch(-water_depth_in))
        branch_ew = create_pipe_straight(
            doc, f"{name}_Branch_EW", seg2_start, seg2_end, branch_diameter_in, water_color
        )
        if branch_ew:
            created.append(branch_ew)

        # SEGMENT 3: North-south from gap back to stub Y position
        seg3_start = App.Vector(bc.ft(stub_x_ft), bc.ft(gap_y_ft), bc.inch(-water_depth_in))
        seg3_end = App.Vector(bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(-water_depth_in))
        branch_ns2 = create_pipe_straight(
            doc, f"{name}_Branch_NS2", seg3_start, seg3_end, branch_diameter_in, water_color
        )
        if branch_ns2:
            created.append(branch_ns2)

        # Vertical stub-up: from underground to hose bib height (42" = 3.5')
        hose_bib_height_in = 42.0  # 3.5' height - convenient for outdoor hose connection
        stub_start = App.Vector(bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(-water_depth_in))
        stub_end = App.Vector(bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(hose_bib_height_in))
        stub_up = create_pipe_straight(
            doc, f"{name}_StubUp", stub_start, stub_end, branch_diameter_in, water_color
        )
        if stub_up:
            created.append(stub_up)

        # Hose bib fixture at pile face
        hose_bib = create_hose_bib(
            doc, name, stub_x_ft, stub_y_ft, hose_bib_height_in, branch_diameter_in
        )
        created.append(hose_bib)

    return created


def create_septic_system(doc, septic_config):
    """
    Create complete septic system (tank, leach field, drain line).

    Args:
        doc: FreeCAD document
        septic_config: SEPTIC_SYSTEM config dict

    Returns:
        Group containing all septic system objects
    """
    App.Console.PrintMessage("[septic_utilities] Creating septic system...\n")

    created = []

    # Septic tank
    tank = create_septic_tank(doc, septic_config)
    created.append(tank)

    # Leach field trenches
    trenches = create_leach_field(doc, septic_config)
    created.extend(trenches)

    # Drain line (from house stub-up to tank)
    # House stub-up position from config
    stub_x_ft = septic_config["stub_up_x_ft"]
    stub_y_ft = septic_config["stub_up_y_ft"]
    tank_x_ft = septic_config["tank_x_ft"]
    tank_y_ft = septic_config["tank_y_ft"]

    # DEBUG: Log the config values being read
    App.Console.PrintMessage(
        f"[DEBUG create_septic_system] stub_up_x_ft={stub_x_ft}, stub_up_y_ft={stub_y_ft}\n"
    )

    drain_line_parts = create_drain_line(
        doc,
        septic_config,
        start_x_ft=stub_x_ft,
        start_y_ft=stub_y_ft,
        end_x_ft=tank_x_ft,
        end_y_ft=tank_y_ft,
    )
    created.extend(drain_line_parts)  # Add all pipe sections and couplings

    # Group all septic objects
    septic_grp = bc.create_group(doc, "Septic_System")
    bc.add_to_group(septic_grp, created)

    App.Console.PrintMessage(
        f"[septic_utilities] Created septic system: "
        f"1 tank, {len(trenches)} leach trenches, 1 drain line\n"
    )

    return septic_grp


def create_slab_forms(doc, config, pile_positions_ft=None, pile_size_in=12.0):
    """
    Create formwork for concrete slab (2x12 boards around perimeter).

    Typical formwork:
    - 2x12 boards on edge around slab perimeter
    - Staked to ground with rebar or wood stakes
    - Removed after concrete cures

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict with keys:
            - slab_x_start_ft, slab_y_start_ft: Slab starting position
            - slab_width_ft, slab_depth_ft: Slab dimensions
            - slab_thickness_in: Slab thickness (determines form height)
        pile_positions_ft: List of (x_ft, y_ft) tuples for pile centers
        pile_size_in: Pile cross-section size (default 12")

    Returns:
        List of Part::Feature objects (form boards)
    """
    x_start_ft = config["slab_x_start_ft"]
    y_start_ft = config["slab_y_start_ft"]
    width_ft = config["slab_width_ft"]
    depth_ft = config["slab_depth_ft"]
    thickness_in = config["slab_thickness_in"]

    # Form board dimensions (2x12 on edge)
    form_thick_in = 1.5  # 2x12 actual thickness
    form_height_in = thickness_in  # Match slab thickness

    created = []

    # South form (front, along X at Y=y_start_ft)
    south_form = doc.addObject("Part::Feature", "Slab_Form_South")
    south_form.Shape = Part.makeBox(
        bc.ft(width_ft), bc.inch(form_thick_in), bc.inch(form_height_in)
    )
    south_form.Placement.Base = App.Vector(
        bc.ft(x_start_ft), bc.ft(y_start_ft) - bc.inch(form_thick_in), bc.inch(-form_height_in)
    )
    created.append(south_form)

    # North form (rear, along X at Y=y_start_ft+depth_ft)
    north_form = doc.addObject("Part::Feature", "Slab_Form_North")
    north_form.Shape = Part.makeBox(
        bc.ft(width_ft), bc.inch(form_thick_in), bc.inch(form_height_in)
    )
    north_form.Placement.Base = App.Vector(
        bc.ft(x_start_ft), bc.ft(y_start_ft + depth_ft), bc.inch(-form_height_in)
    )
    created.append(north_form)

    # West form (left, along Y at X=x_start_ft)
    west_form = doc.addObject("Part::Feature", "Slab_Form_West")
    west_form.Shape = Part.makeBox(bc.inch(form_thick_in), bc.ft(depth_ft), bc.inch(form_height_in))
    west_form.Placement.Base = App.Vector(
        bc.ft(x_start_ft) - bc.inch(form_thick_in), bc.ft(y_start_ft), bc.inch(-form_height_in)
    )
    created.append(west_form)

    # East form (right, along Y at X=x_start_ft+width_ft)
    east_form = doc.addObject("Part::Feature", "Slab_Form_East")
    east_form.Shape = Part.makeBox(bc.inch(form_thick_in), bc.ft(depth_ft), bc.inch(form_height_in))
    east_form.Placement.Base = App.Vector(
        bc.ft(x_start_ft + width_ft), bc.ft(y_start_ft), bc.inch(-form_height_in)
    )
    created.append(east_form)

    return created


def create_concrete_slab_group(doc, utilities_config, pile_positions_ft=None, pile_size_in=12.0):
    """
    Create concrete slab group (slab + optional formwork).

    Args:
        doc: FreeCAD document
        utilities_config: UTILITIES config dict
        pile_positions_ft: List of (x_ft, y_ft) tuples for pile centers
        pile_size_in: Pile cross-section size (default 12")

    Returns:
        Group containing concrete slab and forms
    """
    App.Console.PrintMessage("[septic_utilities] Creating concrete slab...\n")

    created = []

    # Concrete slab (with pile cutouts)
    slab = create_concrete_slab(doc, utilities_config, pile_positions_ft, pile_size_in)
    created.append(slab)

    # Sill seal foam around each pile penetration (realistic interface material)
    slab_thickness_in = utilities_config["slab_thickness_in"]
    x_start_ft = utilities_config["slab_x_start_ft"]
    y_start_ft = utilities_config["slab_y_start_ft"]
    width_ft = utilities_config["slab_width_ft"]
    depth_ft = utilities_config["slab_depth_ft"]

    sill_seals = []
    if pile_positions_ft:
        for pile_x_ft, pile_y_ft in pile_positions_ft:
            # Only create sill seal for piles within slab bounds
            if (
                x_start_ft <= pile_x_ft <= x_start_ft + width_ft
                and y_start_ft <= pile_y_ft <= y_start_ft + depth_ft
            ):
                foam = create_pile_sill_seal(
                    doc, pile_x_ft, pile_y_ft, pile_size_in, slab_thickness_in
                )
                sill_seals.append(foam)

    # Group sill seals if any exist
    if sill_seals:
        sill_seal_grp = bc.create_group(doc, "Sill_Seals")
        bc.add_to_group(sill_seal_grp, sill_seals)
        created.append(sill_seal_grp)

    # Rebar grid (#4 @ 12" OC both ways, positioned 3" above slab bottom)
    rebar_z_in = -slab_thickness_in + 3.0  # 3" up from bottom (typical chair height)
    rebar_grid = create_rebar_grid(
        doc,
        x_start_ft,
        y_start_ft,
        width_ft,
        depth_ft,
        rebar_z_in,
        spacing_in=12.0,
        rebar_dia_in=0.5,
    )

    # Group rebar if any exist
    if rebar_grid:
        rebar_grp = bc.create_group(doc, "Rebar_Grid")
        bc.add_to_group(rebar_grp, rebar_grid)
        created.append(rebar_grp)

    # Formwork (optional - can be removed after pour)
    forms = create_slab_forms(doc, utilities_config, pile_positions_ft, pile_size_in)
    created.extend(forms)

    # Group all slab objects
    slab_grp = bc.create_group(doc, "Concrete_Slab")
    bc.add_to_group(slab_grp, created)

    App.Console.PrintMessage(
        f"[septic_utilities] Created concrete slab: "
        f"1 slab (w/ pile cutouts), {len(sill_seals)} sill seals (grouped), "
        f"{len(rebar_grid)} rebar pieces (grouped), {len(forms)} form boards\n"
    )

    return slab_grp


def create_driveway_slab_group(doc, driveway_config, utilities_config=None):
    """
    Create driveway concrete slab with rebar (12' x 30' x 6" from street).

    Design:
        - 6" thick concrete slab (driveway grade per ACI 332)
        - #4 rebar @ 12" OC both ways
        - Positioned along west property line from street toward house
        - Cutouts for water meter and shutoff boxes (if provided)

    Args:
        doc: FreeCAD document
        driveway_config: DRIVEWAY config dict with keys:
            - slab_x_start_ft, slab_y_start_ft: Starting position
            - slab_width_ft, slab_depth_ft: Slab dimensions
            - slab_thickness_in: Slab thickness (6")
            - rebar_spacing_in, rebar_diameter_in: Rebar specs
        utilities_config: UTILITIES config dict (optional) with keys:
            - water_lateral_x_ft: X position for water service
            - water_entry_from_street_y_ft: Y position for meter box

    Returns:
        Group containing driveway slab, rebar, and forms
    """
    App.Console.PrintMessage("[septic_utilities] Creating driveway slab...\n")

    x_start_ft = driveway_config["slab_x_start_ft"]
    y_start_ft = driveway_config["slab_y_start_ft"]
    width_ft = driveway_config["slab_width_ft"]
    depth_ft = driveway_config["slab_depth_ft"]
    thickness_in = driveway_config["slab_thickness_in"]
    rebar_spacing_in = driveway_config.get("rebar_spacing_in", 12.0)
    rebar_dia_in = driveway_config.get("rebar_diameter_in", 0.5)

    created = []

    # Create driveway slab base
    slab = doc.addObject("Part::Feature", "Driveway_Slab_6in")
    slab_box = Part.makeBox(bc.ft(width_ft), bc.ft(depth_ft), bc.inch(thickness_in))
    slab_box.Placement.Base = App.Vector(
        bc.ft(x_start_ft), bc.ft(y_start_ft), bc.inch(-thickness_in)  # Bottom of slab at -6"
    )

    # Create cutouts for water boxes if utilities config provided
    if utilities_config:
        water_lateral_x_ft = utilities_config.get("water_lateral_x_ft", 37.0)
        street_y_ft = utilities_config.get("water_entry_from_street_y_ft", 0.0)

        # Water meter box dimensions and position (20" x 26" x 20")
        meter_width_in = 20.0  # X direction
        meter_length_in = 26.0  # Y direction
        meter_x_ft = water_lateral_x_ft
        meter_y_ft = street_y_ft

        # Water shutoff box dimensions and position (13" x 15" x 14", 3' north of meter)
        shutoff_width_in = 13.0  # X direction
        shutoff_length_in = 15.0  # Y direction
        shutoff_x_ft = water_lateral_x_ft
        shutoff_y_ft = street_y_ft + 3.0  # 3' north of meter

        # Create meter box cutout (extends through full slab thickness)
        meter_cutout = Part.makeBox(
            bc.inch(meter_width_in),
            bc.inch(meter_length_in),
            bc.inch(thickness_in + 1.0),  # Slightly taller to ensure clean cut
        )
        meter_cutout.Placement.Base = App.Vector(
            bc.ft(meter_x_ft) - bc.inch(meter_width_in / 2.0),
            bc.ft(meter_y_ft) - bc.inch(meter_length_in / 2.0),
            bc.inch(-thickness_in - 0.5),  # Start below slab bottom
        )

        # Create shutoff box cutout
        shutoff_cutout = Part.makeBox(
            bc.inch(shutoff_width_in), bc.inch(shutoff_length_in), bc.inch(thickness_in + 1.0)
        )
        shutoff_cutout.Placement.Base = App.Vector(
            bc.ft(shutoff_x_ft) - bc.inch(shutoff_width_in / 2.0),
            bc.ft(shutoff_y_ft) - bc.inch(shutoff_length_in / 2.0),
            bc.inch(-thickness_in - 0.5),
        )

        # Subtract cutouts from slab
        slab_with_cutouts = slab_box.cut(meter_cutout).cut(shutoff_cutout)
        slab.Shape = slab_with_cutouts

        App.Console.PrintMessage(
            f"[septic_utilities] Added water box cutouts: "
            f"meter @ X={meter_x_ft:.1f}', Y={meter_y_ft:.1f}', "
            f"shutoff @ X={shutoff_x_ft:.1f}', Y={shutoff_y_ft:.1f}'\n"
        )
    else:
        slab.Shape = slab_box

    created.append(slab)

    # Rebar grid (#4 @ 12" OC both ways, positioned 3" above slab bottom)
    # Create exclusion zones for water boxes if utilities config provided
    exclusion_zones = []
    if utilities_config:
        # Water meter box exclusion zone
        exclusion_zones.append(
            {
                "x_center_ft": meter_x_ft,
                "y_center_ft": meter_y_ft,
                "width_ft": meter_width_in / 12.0,
                "depth_ft": meter_length_in / 12.0,
            }
        )
        # Water shutoff box exclusion zone
        exclusion_zones.append(
            {
                "x_center_ft": shutoff_x_ft,
                "y_center_ft": shutoff_y_ft,
                "width_ft": shutoff_width_in / 12.0,
                "depth_ft": shutoff_length_in / 12.0,
            }
        )

    rebar_z_in = -thickness_in + 3.0  # 3" up from bottom
    rebar_grid = create_rebar_grid(
        doc,
        x_start_ft,
        y_start_ft,
        width_ft,
        depth_ft,
        rebar_z_in,
        rebar_spacing_in,
        rebar_dia_in,
        exclusion_zones=exclusion_zones if exclusion_zones else None,
    )

    # Group rebar if any exist
    if rebar_grid:
        rebar_grp = bc.create_group(doc, "Driveway_Rebar_Grid")
        bc.add_to_group(rebar_grp, rebar_grid)
        created.append(rebar_grp)

    # Group all driveway objects
    driveway_grp = bc.create_group(doc, "Driveway_Slab")
    bc.add_to_group(driveway_grp, created)

    App.Console.PrintMessage(
        f"[septic_utilities] Created driveway slab: "
        f"1 slab ({width_ft}' x {depth_ft}' x {thickness_in}\"), {len(rebar_grid)} rebar pieces (grouped)\n"
    )

    return driveway_grp


def create_exterior_stairs(doc, stairs_config, floor_z_ft=20.0, slab_z_ft=0.0):
    """
    Create exterior stairs descending from first floor to concrete slab (simple tread model).

    Design:
        - Treads only (no risers or stringers in simplified model)
        - 2x12 PT lumber treads
        - Running north-south along east side of house
        - DESCENDING from floor (south) to slab (north)
        - Rise: 7.25" per step (IRC R311.7.5.1 max 7-3/4")
        - Run: 10" per tread (IRC R311.7.5.2 min 10")
        - Width: 36" (IRC R311.7.1 min 36")
        - Top tread snaps to north edge of floor rim (finished floor to finished floor)

    Args:
        doc: FreeCAD document
        stairs_config: STAIRS config dict with keys:
            - stair_x_ft: X position (east side of house)
            - stair_y_snap_ft: Y position where top tread south edge meets floor rim
            - tread_rise_in: Riser height (7.25")
            - tread_run_in: Tread depth (10")
            - tread_width_ft: Stair width (3')
            - tread_stock: Lumber stock label
            - descending_direction: "north" (stairs descend northward)
        floor_z_ft: First floor elevation (default 20', top of joists)
        slab_z_ft: Slab elevation (default 0', top of concrete)

    Returns:
        Group containing all stair treads
    """
    App.Console.PrintMessage(
        "[septic_utilities] Creating exterior stairs (descending from floor to slab)...\n"
    )

    x_ft = stairs_config["stair_x_ft"]
    y_snap_ft = stairs_config["stair_y_snap_ft"]  # Top tread south edge position
    rise_in = stairs_config["tread_rise_in"]
    run_in = stairs_config["tread_run_in"]
    width_ft = stairs_config["tread_width_ft"]
    tread_label = stairs_config["tread_stock"]

    # Load catalog for tread stock (need this early to get joist depth for total rise calculation)
    import math

    catalog_candidates = [
        os.path.join(
            SCRIPT_DIR, "..", "lumber", "lumber_catalog.csv"
        ),  # DesignHouse/lumber/lumber_catalog.csv
    ]
    catalog_path = None
    for candidate in catalog_candidates:
        if os.path.exists(candidate):
            catalog_path = candidate
            break

    tread_row = None
    if catalog_path:
        from lumber_common import attach_metadata, find_stock, load_catalog

        rows = load_catalog(catalog_path)
        tread_row = find_stock(rows, tread_label)

    # Get tread dimensions from catalog
    if tread_row:
        tread_thick_in = float(tread_row["actual_thickness_in"])  # 1.5"
        tread_depth_in = float(tread_row["actual_width_in"])  # 11.25"
        tread_length_in = width_ft * 12.0  # Cut to stair width
    else:
        # Fallback dimensions
        tread_thick_in = 1.5
        tread_depth_in = 11.25
        tread_length_in = width_ft * 12.0

    # Calculate total rise and number of steps
    # IMPORTANT: floor_z_ft is the foundation top (joist bottom), NOT the finished floor!
    # Finished floor is at joist top = floor_z_ft + joist depth
    # The joist depth equals tread_depth_in (both are 2x12 = 11.25" actual)
    joist_depth_in = tread_depth_in  # 11.25" for 2x12 joists
    finished_floor_z_in = (floor_z_ft * 12.0) + joist_depth_in
    slab_top_z_in = slab_z_ft * 12.0

    # Deck board thickness (5/4 deck boards on top of joists)
    deck_board_thick_in = 1.0  # 5/4 actual thickness

    # Deck surface (finished floor surface) = joist top + deck board thickness
    deck_surface_z_in = finished_floor_z_in + deck_board_thick_in

    # Total vertical distance from slab top to deck surface (finished floor surface)
    # This is the ACTUAL total rise that the stairs must traverse
    total_rise_in = deck_surface_z_in - slab_top_z_in

    # Calculate number of risers needed (round up to ensure steps aren't too tall)
    num_risers = math.ceil(total_rise_in / rise_in)

    # Adjust actual rise to make all steps equal height
    # (We divide total rise by number of risers to get exact equal spacing)
    actual_rise_in = total_rise_in / num_risers

    # Number of treads:
    # - Tread 0 = top landing (at deck surface, part of the deck)
    # - Treads 1 through num_risers-1 = physical stair treads descending to slab
    # - Total: num_risers treads (0 through num_risers-1)
    # - The final rise (riser num_risers) goes from the last tread to the slab
    num_treads = num_risers

    App.Console.PrintMessage(
        f'[septic_utilities] Stair calculation: {total_rise_in:.2f}" rise (slab {slab_top_z_in:.1f}" → deck surface {deck_surface_z_in:.1f}") ÷ {rise_in:.2f}" target = '
        f'{num_risers} risers @ {actual_rise_in:.4f}" each, {num_treads} treads\n'
    )

    created = []

    # Create treads (descending from deck surface to slab, NORTHWARD)
    # Treads numbered 0 (top landing, at joist top) to num_treads-1 (bottom, nearest slab)
    # Tread 0 = top landing (at joist top level, deck boards installed on top of it)
    # Tread 1 = first actual step down (one rise below deck surface)
    for step in range(num_treads):
        # Calculate Z position for this tread
        # Tread 0 (top): top surface at JOIST TOP (deck boards go on top of tread 0)
        # Tread 1: one rise below DECK SURFACE (not tread 0)
        # ...
        # Tread num_treads-1 (bottom): num_treads-1 rises below deck surface (= one rise above slab)
        if step == 0:
            # Tread 0: top landing at joist top (deck boards sit on top)
            tread_top_z_in = finished_floor_z_in
        else:
            # All other treads: descend from deck surface
            tread_top_z_in = deck_surface_z_in - (step * actual_rise_in)

        tread_z_bottom_in = tread_top_z_in - tread_thick_in

        # Y position: top tread (step 0) starts at y_snap_ft, each subsequent tread moves NORTH (+Y)
        tread_y_south_in = y_snap_ft * 12.0 + (
            step * tread_depth_in
        )  # South edge (moving north = +Y)

        # Create tread box
        tread = doc.addObject("Part::Feature", f"Stair_Tread_{step}")
        tread_box = Part.makeBox(
            bc.inch(tread_length_in),  # Width (X direction, 3')
            bc.inch(tread_depth_in),  # Depth (Y direction, 11.25")
            bc.inch(tread_thick_in),  # Thickness (Z direction, 1.5")
        )
        tread_box.Placement.Base = App.Vector(
            bc.ft(x_ft) - bc.inch(tread_length_in / 2.0),  # Center on X position
            bc.inch(tread_y_south_in),  # Y position south edge (moving north with each step)
            bc.inch(tread_z_bottom_in),  # Z position bottom of tread (descending)
        )
        tread.Shape = tread_box

        # Attach BOM metadata
        if tread_row:
            attach_metadata(tread, tread_row, tread_label, supplier="lowes")
            # Add cut length property
            try:
                if "cut_length_in" not in tread.PropertiesList:
                    tread.addProperty("App::PropertyString", "cut_length_in")
                tread.cut_length_in = f"{tread_length_in:.2f}"
            except Exception:
                pass

        # Color: brown PT lumber
        try:
            if hasattr(tread, "ViewObject") and tread.ViewObject:
                tread.ViewObject.ShapeColor = (0.55, 0.45, 0.35)  # Brown PT lumber
        except Exception:
            pass

        created.append(tread)

    # Group all treads
    stairs_grp = bc.create_group(doc, "Exterior_Stairs")
    bc.add_to_group(stairs_grp, created)

    App.Console.PrintMessage(
        f"[septic_utilities] Created exterior stairs: "
        f'{num_treads} treads + 1 landing (floor), {num_risers} risers @ {actual_rise_in:.4f}" each, '
        f'{total_rise_in:.1f}" total rise\n'
    )

    return stairs_grp


def create_utilities_group(
    doc, utilities_config, stairs_config=None, foundation_config=None, lot_config=None
):
    """
    Create utilities group (water, electrical, plumbing service lines and infrastructure).

    Args:
        doc: FreeCAD document
        utilities_config: UTILITIES config dict
        stairs_config: STAIRS config dict (optional, for foot wash station)
        foundation_config: FOUNDATION config dict (optional, for pile-mounted hose bibs)
        lot_config: LOT config dict (optional, for calculating pile positions)

    Returns:
        Group containing all utility service lines and equipment
    """
    App.Console.PrintMessage("[septic_utilities] Creating utilities...\n")

    # ============================================================
    # WATER INFRASTRUCTURE (grouped separately for debugging)
    # ============================================================
    water_parts = []

    # Water service line from street (returns list of segments)
    water_line_parts = create_water_service_line(doc, utilities_config)
    water_parts.extend(water_line_parts)

    # Water stub-up (now includes shutoff and drain bib - removed create_water_stub_up call)
    # The shutoff and drain bib are now created as part of create_water_service_line()

    # Water infrastructure (meter box at street, customer shutoff near house)
    water_meter = create_water_meter_box(doc, utilities_config)
    water_parts.append(water_meter)

    water_shutoff = create_water_shutoff_box(doc, utilities_config)
    water_parts.append(water_shutoff)

    # Foot wash station on pile 5,6 north face (requires foundation and lot configs)
    if foundation_config and lot_config:
        foot_wash_parts = create_foot_wash_station(
            doc, utilities_config, foundation_config, lot_config
        )
        water_parts.extend(foot_wash_parts)

    # Pile-mounted hose bibs at property corners (requires foundation and lot configs)
    if foundation_config and lot_config:
        pile_hose_bib_parts = create_pile_hose_bibs(
            doc, utilities_config, foundation_config, lot_config
        )
        water_parts.extend(pile_hose_bib_parts)

    # Create Water subgroup
    water_grp = bc.create_group(doc, "Water")
    bc.add_to_group(water_grp, water_parts)

    # ============================================================
    # ELECTRICAL INFRASTRUCTURE (grouped separately)
    # ============================================================
    electrical_parts = []

    # Electrical service line from street (returns list of segments)
    electrical_line_parts = create_electrical_service_line(doc, utilities_config)
    electrical_parts.extend(electrical_line_parts)

    # Electrical stub-up
    electrical_stub = create_electrical_stub_up(doc, utilities_config)
    electrical_parts.append(electrical_stub)

    # Electrical infrastructure (meter → disconnect → panel)
    meter_box = create_electrical_meter_box(doc, utilities_config)
    electrical_parts.append(meter_box)

    disconnect = create_electrical_disconnect(doc, utilities_config)
    electrical_parts.append(disconnect)

    panel = create_electrical_panel(doc, utilities_config)
    electrical_parts.append(panel)

    # Create Electrical subgroup
    electrical_grp = bc.create_group(doc, "Electrical")
    bc.add_to_group(electrical_grp, electrical_parts)

    # ============================================================
    # PLUMBING INFRASTRUCTURE (grouped separately)
    # ============================================================
    plumbing_parts = []

    # Plumbing drain/waste/vent stub-ups
    plumbing_stubs = create_plumbing_stub_ups(doc, utilities_config)
    plumbing_parts.extend(plumbing_stubs)

    # Create Plumbing subgroup (if any plumbing exists)
    if plumbing_parts:
        plumbing_grp = bc.create_group(doc, "Plumbing")
        bc.add_to_group(plumbing_grp, plumbing_parts)

    # ============================================================
    # UTILITIES GROUP (contains Water, Electrical, Plumbing subgroups)
    # ============================================================
    utilities_grp = bc.create_group(doc, "Utilities")
    subgroups = [water_grp, electrical_grp]
    if plumbing_parts:
        subgroups.append(plumbing_grp)
    bc.add_to_group(utilities_grp, subgroups)

    App.Console.PrintMessage(
        f"[septic_utilities] Created utilities: "
        f"1 water line, 1 electrical line, "
        f"{len(plumbing_stubs)} plumbing stubs\n"
    )

    return utilities_grp


if __name__ == "__main__":
    print("[septic_utilities] This module provides septic and utilities creation helpers.")
    print("[septic_utilities] Import into your macro: import septic_utilities as su")
