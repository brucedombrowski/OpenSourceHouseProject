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
    * Underground 90 degrees elbow at slab bottom
    * Underground horizontal run EAST to gap middle at X=37.0' (between pile columns 4 and 5)
    * Underground 90 degrees elbow at gap middle
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


def calculate_pile_positions(foundation_config, lot_config):
    """
    Calculate pile X and Y positions using consistent logic.

    X Direction (East-West):
        - West pile: west face aligns with left setback line
        - East pile: east face aligns with right setback line
        - Interior piles: evenly spaced between

    Y Direction (North-South):
        - Front pile: south face aligns with front setback line
        - Remaining piles: spaced at pile_spacing_y_ft intervals

    Args:
        foundation_config: Foundation configuration dict
        lot_config: Lot configuration dict

    Returns:
        Tuple of (x_positions_ft, y_positions_ft, x_spacing_ft, y_spacing_ft)
    """
    # Extract config values
    pile_grid_x = foundation_config["pile_grid_x"]
    pile_grid_y = foundation_config["pile_grid_y"]
    y_spacing_ft = foundation_config["pile_spacing_y_ft"]
    actual_pile_size_in = foundation_config.get("pile_actual_size_in", 11.25)

    lot_width_ft = lot_config["width_ft"]
    left_setback_ft = lot_config.get("left_setback_ft", 5.0)
    right_setback_ft = lot_config.get("right_setback_ft", 5.0)
    front_setback_ft = lot_config["front_setback_ft"]

    # Pile thickness for face alignment
    pile_thickness_ft = actual_pile_size_in / 12.0
    pile_half_thickness_ft = pile_thickness_ft / 2.0

    # X positions: outside faces align with setback lines
    west_pile_center_x_ft = left_setback_ft + pile_half_thickness_ft
    east_pile_center_x_ft = lot_width_ft - right_setback_ft - pile_half_thickness_ft
    if pile_grid_x > 1:
        x_spacing_ft = (east_pile_center_x_ft - west_pile_center_x_ft) / (pile_grid_x - 1)
    else:
        x_spacing_ft = 0.0
    x_positions_ft = [west_pile_center_x_ft + i * x_spacing_ft for i in range(pile_grid_x)]

    # Y positions: front pile face at front setback
    start_y_ft = front_setback_ft + pile_half_thickness_ft
    y_positions_ft = [start_y_ft + i * y_spacing_ft for i in range(pile_grid_y)]

    return x_positions_ft, y_positions_ft, x_spacing_ft, y_spacing_ft


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
    _mounting_hole_dia_in = 0.5  # 1/2" bolt holes  # noqa: F841

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
        3. Underground horizontal run EAST (with slope) to gap middle: (33.635, 52.46875) -> (37.0, 52.46875)
        4. Underground 90-degree elbow at gap middle
        5. Underground horizontal run NORTH in pile gap: (37.0, 52.46875) -> (37.0, 88.0)
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

    _depth_at_waypoint_in = depth_start_in + (run_1_ft * slope_in_per_ft)  # noqa: F841
    _depth_end_in = depth_start_in + ((run_1_ft + run_2_ft) * slope_in_per_ft)  # noqa: F841

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
        axis2: Outgoing direction (must be 90 degrees from axis1)
        color: Optional RGB tuple (0-1 range)

    Returns:
        Part::Feature object (90 degrees elbow)
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
    _bend_radius_in = diameter_in * 6.0  # noqa: F841

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
    _bend_radius_in = diameter_in * 6.0  # noqa: F841

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
    - Spout extends at 45 degrees downward angle
    - Spout diameter: 0.75" (standard garden hose thread)

    Args:
        doc: FreeCAD document
        name: Object name
        x_ft, y_ft: Horizontal position (feet)
        z_in: Vertical position at connection point (inches)
        diameter_in: Connection diameter (inches)
        angle_deg: Spout angle from horizontal (45 degrees typical)

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

    # Create spout (angled downward at 45 degrees)
    import math

    angle_rad = math.radians(angle_deg)
    _spout_dx_in = spout_length_in * math.cos(angle_rad)  # noqa: F841
    _spout_dz_in = -spout_length_in * math.sin(angle_rad)  # Downward  # noqa: F841

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
    # Use consistent pile positioning logic
    water_x_ft = config.get("water_lateral_x_ft", 37.0)
    water_depth_in = config["water_service_depth_in"]
    branch_diameter_in = 0.75

    actual_pile_size_in = foundation_config.get("pile_actual_size_in", 11.25)

    # Calculate pile positions using shared helper
    x_positions_ft, y_positions_ft, _, _ = calculate_pile_positions(foundation_config, lot_config)

    # Pile 5,6 position (column 4, row 5 in 0-based indexing)
    pile_i = 4
    pile_j = 5
    pile_center_x_ft = x_positions_ft[pile_i]
    pile_center_y_ft = y_positions_ft[pile_j]

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
    actual_pile_size_in = foundation_config.get("pile_actual_size_in", 11.25)  # 11.25" actual

    # Calculate pile positions using shared helper
    x_positions_ft, y_positions_ft, _, y_spacing_ft = calculate_pile_positions(
        foundation_config, lot_config
    )

    # Color: blue for water
    water_color = (0.2, 0.4, 0.8)

    created = []

    # Define hose bib positions at pile corners
    # Pile indices (i, j) where i=column (0 to num_x-1), j=row (0 to num_y-1)
    num_piles_x = len(x_positions_ft)
    num_piles_y = len(y_positions_ft)
    last_col = num_piles_x - 1  # Last column index (e.g., 4 for 5 columns)
    last_row = num_piles_y - 1  # Last row index (e.g., 6 for 7 rows)

    hose_bib_positions = [
        {
            "name": "HoseBib_SW_Front",
            "pile_i": 0,
            "pile_j": 0,
            "face": "west",
        },  # Pile 1,1 west face (SW front corner)
        {
            "name": "HoseBib_SW_Back",
            "pile_i": 0,
            "pile_j": last_row,
            "face": "west",
        },  # Pile 1,N west face (NW corner)
        {
            "name": "HoseBib_SE_Front",
            "pile_i": last_col,
            "pile_j": 0,
            "face": "east",
        },  # Pile N,1 east face (SE front corner)
        {
            "name": "HoseBib_SE_Back",
            "pile_i": last_col,
            "pile_j": last_row,
            "face": "east",
        },  # Pile N,N east face (NE corner)
    ]

    for bib_config in hose_bib_positions:
        name = bib_config["name"]
        pile_i = bib_config["pile_i"]
        pile_j = bib_config["pile_j"]
        face = bib_config["face"]

        # Get pile center position from calculated arrays
        pile_center_x_ft = x_positions_ft[pile_i]
        pile_center_y_ft = y_positions_ft[pile_j]

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


# ============================================================
# STAIR STRUCTURAL COMPONENTS
# ============================================================


def create_cut_stringer(
    doc,
    catalog_rows,
    stringer_label,
    name,
    num_steps,
    rise_per_step_in,
    run_per_step_in,
    stringer_thick_in,
    start_x_in,
    start_y_in,
    top_z_in,
    direction,
    supplier="lowes",
    bottom_cut="horizontal",
    tread_overhang_in=1.0,
    header_depth_in=0.0,
    landing_z_in=None,  # Z level of landing surface for bottom cut (if None, calculated from steps)
):
    """
    Create a cut stringer (sawtooth notched) for stair support.

    Built like a real framer would:
    1. Start with a 2x12 board positioned at the stair angle
    2. Use boolean cuts to remove triangular notches for each tread
    3. Notches have PLUMB (vertical) riser cuts and LEVEL (horizontal) tread cuts

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data
        stringer_label: Catalog label for stringer stock (e.g., "2x12x192_PT")
        name: Object name for the stringer
        num_steps: Number of steps (treads) this stringer supports
        rise_per_step_in: Vertical rise per step (inches)
        run_per_step_in: Horizontal run per step (inches, typically tread depth)
        stringer_thick_in: Stringer thickness (1.5" for 2x lumber) - passed but we use catalog
        start_x_in: X position of stringer west face (for east direction)
        start_y_in: Y position of stringer south face
        top_z_in: Z position where profile Z=0 maps (tread 0 bottom / header top)
        direction: Stair direction ("east", "west", "north", "south")
        supplier: Supplier for catalog metadata
        bottom_cut: "horizontal" (flat seat on landing/slab) or "angled" (follows slope)
        tread_overhang_in: How much tread overhangs past riser (default 1")
        header_depth_in: Depth of header board (11.25" for 2x12). Limits top plumb cut.

    Returns:
        Part::Feature object representing the stringer
    """
    import math

    from lumber_common import attach_metadata, find_stock

    # ==========================================================================
    # STRINGER: 2D profile (XZ plane) extruded in Y
    # ==========================================================================
    #
    # Build a 2D sawtooth profile representing the stringer cross-section,
    # then extrude it by the board thickness (1.5").
    #
    # Profile coordinate system:
    # - X = run direction (horizontal, +X = east/downstairs)
    # - Z = vertical (+Z = up)
    # - Y = thickness direction (extrusion)
    # - Origin at top-west corner where stringer meets header

    # Look up stringer stock
    stringer_row = find_stock(catalog_rows, stringer_label)
    if not stringer_row:
        App.Console.PrintWarning(
            f"[septic_utilities] Stringer stock '{stringer_label}' not found in catalog\n"
        )
        return None

    board_width_in = float(stringer_row["actual_width_in"])  # 11.25" for 2x12
    board_thick_in = float(stringer_row["actual_thickness_in"])  # 1.5"

    # Calculate geometry
    total_rise_in = num_steps * rise_per_step_in
    total_run_in = num_steps * run_per_step_in
    stair_angle_rad = math.atan(rise_per_step_in / run_per_step_in)

    # Notch dimensions
    # run_per_step_in is the tread spacing (tread_depth - overhang)
    # The notch run equals the tread spacing (level cut where tread sits)
    # First notch is shorter by header thickness (tread 0 level cut starts at header east face)
    # header_thick_in is only used if there's actually a header
    header_thick_in = 1.5 if header_depth_in > 0 else 0.0
    standard_notch_run_in = run_per_step_in  # Level cut = tread spacing
    if header_depth_in > 0:
        first_notch_run_in = run_per_step_in - header_thick_in
    else:
        first_notch_run_in = standard_notch_run_in

    # Throat: remaining wood below notches (perpendicular to slope)
    # For 2x12 with standard notch, throat is typically 5-6"
    throat_in = 5.0

    App.Console.PrintMessage(
        f"[septic_utilities] Creating stringer '{name}': {num_steps} steps, "
        f'rise={rise_per_step_in:.2f}", run={run_per_step_in:.2f}", '
        f'throat={throat_in:.1f}", notch0={first_notch_run_in:.2f}", notch_std={standard_notch_run_in:.2f}"\n'
    )

    # ==========================================================================
    # Build stringer: 2x12 board on edge, rotated to stair angle
    # ==========================================================================
    #
    # Create a simple 2x12 board at origin, then use Placement to:
    # 1. Rotate to match stair pitch (around Y axis)
    # 2. Rotate to match stair direction (around Z axis)
    # 3. Translate to final position

    # Calculate the stringer board length along the slope
    stair_hyp_in = math.sqrt(total_rise_in**2 + total_run_in**2)
    board_length_in = stair_hyp_in + 12.0  # Add extra for top/bottom

    # Create 2x12 board at origin, lying along +X axis, on edge
    # - Length along X (will become run direction after rotation)
    # - Thickness along Y (1.5")
    # - Height along Z (11.25" on edge)
    base_board = Part.makeBox(
        bc.inch(board_length_in), bc.inch(board_thick_in), bc.inch(board_width_in)
    )

    # Stair pitch angle in degrees
    pitch_deg = math.degrees(stair_angle_rad)
    sin_angle = math.sin(stair_angle_rad)
    cos_angle = math.cos(stair_angle_rad)

    # Rotate the board shape first (notches must be cut after rotation for level/plumb cuts)
    # Pitch first (around Y), then rotate to direction, then 180° flip for N/S to fix descent direction
    if direction == "east":
        base_board = base_board.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), pitch_deg)
    elif direction == "west":
        base_board = base_board.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), pitch_deg)
        base_board = base_board.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 180)
    elif direction == "north":
        base_board = base_board.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), pitch_deg)
        base_board = base_board.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), -90)
        base_board = base_board.rotate(
            App.Vector(0, 0, 0), App.Vector(0, 0, 1), 180
        )  # Flip to descend toward +Y
    elif direction == "south":
        base_board = base_board.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), pitch_deg)
        base_board = base_board.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 90)
        base_board = base_board.rotate(
            App.Vector(0, 0, 0), App.Vector(0, 0, 1), 180
        )  # Flip to descend toward -Y

    # Calculate reference point and translate board to final position
    # The translation is direction-dependent because the board rotation changes
    # which axis the board extends along
    d = first_notch_run_in * sin_angle
    ref_offset = (board_width_in - d) * sin_angle
    ref_z = (board_width_in - d) * cos_angle

    if direction == "east":
        # Board extends along +X, thickness along Y
        base_board.translate(
            App.Vector(
                bc.inch(start_x_in - ref_offset), bc.inch(start_y_in), bc.inch(top_z_in - ref_z)
            )
        )
    elif direction == "west":
        # Board extends along -X (rotated 180°), thickness along Y
        base_board.translate(
            App.Vector(
                bc.inch(start_x_in + ref_offset), bc.inch(start_y_in), bc.inch(top_z_in - ref_z)
            )
        )
    elif direction == "north":
        # Board extends along +Y (rotated -90° then 180°), thickness along X
        base_board.translate(
            App.Vector(
                bc.inch(start_x_in), bc.inch(start_y_in - ref_offset), bc.inch(top_z_in - ref_z)
            )
        )
    elif direction == "south":
        # Board extends along -Y (rotated 90° then 180°), thickness along X
        base_board.translate(
            App.Vector(
                bc.inch(start_x_in), bc.inch(start_y_in + ref_offset), bc.inch(top_z_in - ref_z)
            )
        )

    # Debug: print board bounding box
    bb = base_board.BoundBox
    App.Console.PrintMessage(
        f'[septic_utilities] Board BoundBox: X={bb.XMin/25.4:.2f}" to {bb.XMax/25.4:.2f}", '
        f'Z={bb.ZMin/25.4:.2f}" to {bb.ZMax/25.4:.2f}"\n'
    )

    # Now cut notches with axis-aligned boxes (level and plumb cuts)
    # Notches are positioned relative to tread locations in world coordinates
    #
    # For "east" direction stairs (descending toward +X):
    # - Plumb cut (riser face) is at the WEST edge of each notch
    # - Level cut (tread surface) extends EAST from plumb cut
    # - First notch: plumb at header east face (start_x), level extends east
    #
    # For "north" direction stairs (descending toward +Y):
    # - Plumb cut is at the SOUTH edge of each notch
    # - Level cut extends NORTH from plumb cut
    #
    # Header position (tread 0 edge aligns here)
    header_west_in = start_x_in - header_thick_in  # For E/W
    header_south_in = start_y_in - header_thick_in  # For N/S

    App.Console.PrintMessage(
        f'[septic_utilities] Stringer notch cutting ({direction}): start=({start_x_in:.2f}", {start_y_in:.2f}"), top_z={top_z_in:.2f}"\n'
    )

    # Direction-specific notch cutting
    if direction == "east":
        # EAST: notches along +X axis, board thickness along Y
        # First plumb cut: at header east face, extends WEST to cut board top
        first_plumb_x = start_x_in  # Header east face
        first_cut_box = Part.makeBox(
            bc.inch(standard_notch_run_in),
            bc.inch(board_thick_in + 6),
            bc.inch(total_rise_in + board_width_in * 2),
        )
        first_cut_box.translate(
            App.Vector(
                bc.inch(first_plumb_x - standard_notch_run_in),
                bc.inch(start_y_in - 3),
                bc.inch(top_z_in - total_rise_in),
            )
        )
        App.Console.PrintMessage(f'[septic_utilities]   First plumb: x={first_plumb_x:.2f}"\n')
        base_board = base_board.cut(first_cut_box)

        # All tread notches
        for step in range(num_steps):
            level_z = top_z_in - step * rise_per_step_in
            tread_west = header_west_in + step * run_per_step_in
            plumb_x = tread_west

            notch_box = Part.makeBox(
                bc.inch(standard_notch_run_in),
                bc.inch(board_thick_in + 6),
                bc.inch(rise_per_step_in + board_width_in),
            )
            notch_box.translate(
                App.Vector(bc.inch(plumb_x), bc.inch(start_y_in - 3), bc.inch(level_z))
            )
            App.Console.PrintMessage(
                f'[septic_utilities]   Step {step}: plumb_x={plumb_x:.2f}", level_z={level_z:.2f}"\n'
            )
            base_board = base_board.cut(notch_box)

        # Final plumb cut
        last_tread_west = header_west_in + (num_steps - 1) * run_per_step_in
        final_plumb_x = last_tread_west + run_per_step_in
        final_cut_box = Part.makeBox(
            bc.inch(board_length_in),
            bc.inch(board_thick_in + 6),
            bc.inch(total_rise_in + board_width_in * 2),
        )
        final_cut_box.translate(
            App.Vector(
                bc.inch(final_plumb_x), bc.inch(start_y_in - 3), bc.inch(top_z_in - total_rise_in)
            )
        )
        App.Console.PrintMessage(f'[septic_utilities]   Final plumb: x={final_plumb_x:.2f}"\n')
        base_board = base_board.cut(final_cut_box)

        # Bottom horizontal cut
        if landing_z_in is not None:
            bottom_cut_z = landing_z_in
        else:
            bottom_cut_z = top_z_in - num_steps * rise_per_step_in
        bottom_cut_box = Part.makeBox(
            bc.inch(board_length_in * 2),
            bc.inch(board_thick_in + 6),
            bc.inch(total_rise_in + board_width_in * 2),
        )
        bottom_cut_box.translate(
            App.Vector(
                bc.inch(header_west_in - board_length_in),
                bc.inch(start_y_in - 3),
                bc.inch(bottom_cut_z - total_rise_in - board_width_in * 2),
            )
        )
        App.Console.PrintMessage(f'[septic_utilities]   Bottom cut: z={bottom_cut_z:.2f}"\n')
        base_board = base_board.cut(bottom_cut_box)

    elif direction == "west":
        # WEST: notches along -X axis, board thickness along Y
        # Treads descend toward -X, so notch positions decrease with each step
        # start_x_in is the first tread EAST face (where stringer starts)
        header_east_in = start_x_in + header_thick_in  # For west, header is on east side

        # First plumb cut: at start position, extends EAST to cut board top
        first_plumb_x = start_x_in
        first_cut_box = Part.makeBox(
            bc.inch(standard_notch_run_in),
            bc.inch(board_thick_in + 6),
            bc.inch(total_rise_in + board_width_in * 2),
        )
        first_cut_box.translate(
            App.Vector(
                bc.inch(first_plumb_x), bc.inch(start_y_in - 3), bc.inch(top_z_in - total_rise_in)
            )
        )
        App.Console.PrintMessage(f'[septic_utilities]   First plumb: x={first_plumb_x:.2f}"\n')
        base_board = base_board.cut(first_cut_box)

        # All tread notches - positions decrease toward -X
        for step in range(num_steps):
            level_z = top_z_in - step * rise_per_step_in
            # Tread east face = start - step * spacing
            tread_east = header_east_in - step * run_per_step_in
            plumb_x = tread_east  # Plumb cut at tread east face

            notch_box = Part.makeBox(
                bc.inch(standard_notch_run_in),
                bc.inch(board_thick_in + 6),
                bc.inch(rise_per_step_in + board_width_in),
            )
            notch_box.translate(
                App.Vector(
                    bc.inch(plumb_x - standard_notch_run_in),  # Extends west from plumb
                    bc.inch(start_y_in - 3),
                    bc.inch(level_z),
                )
            )
            App.Console.PrintMessage(
                f'[septic_utilities]   Step {step}: plumb_x={plumb_x:.2f}", level_z={level_z:.2f}"\n'
            )
            base_board = base_board.cut(notch_box)

        # Final plumb cut - at last tread west edge
        last_tread_east = header_east_in - (num_steps - 1) * run_per_step_in
        final_plumb_x = last_tread_east - run_per_step_in
        final_cut_box = Part.makeBox(
            bc.inch(board_length_in),
            bc.inch(board_thick_in + 6),
            bc.inch(total_rise_in + board_width_in * 2),
        )
        final_cut_box.translate(
            App.Vector(
                bc.inch(final_plumb_x - board_length_in),  # Extends west past board end
                bc.inch(start_y_in - 3),
                bc.inch(top_z_in - total_rise_in),
            )
        )
        App.Console.PrintMessage(f'[septic_utilities]   Final plumb: x={final_plumb_x:.2f}"\n')
        base_board = base_board.cut(final_cut_box)

        # Bottom horizontal cut
        if landing_z_in is not None:
            bottom_cut_z = landing_z_in
        else:
            bottom_cut_z = top_z_in - num_steps * rise_per_step_in
        bottom_cut_box = Part.makeBox(
            bc.inch(board_length_in * 2),
            bc.inch(board_thick_in + 6),
            bc.inch(total_rise_in + board_width_in * 2),
        )
        bottom_cut_box.translate(
            App.Vector(
                bc.inch(final_plumb_x - board_length_in),
                bc.inch(start_y_in - 3),
                bc.inch(bottom_cut_z - total_rise_in - board_width_in * 2),
            )
        )
        App.Console.PrintMessage(f'[septic_utilities]   Bottom cut: z={bottom_cut_z:.2f}"\n')
        base_board = base_board.cut(bottom_cut_box)

    elif direction == "north":
        # NORTH: notches along +Y axis, board thickness along X
        # Treads descend toward +Y
        header_north_in = start_y_in + header_thick_in

        # First plumb cut: at start position, extends SOUTH
        first_plumb_y = start_y_in
        first_cut_box = Part.makeBox(
            bc.inch(board_thick_in + 6),
            bc.inch(standard_notch_run_in),
            bc.inch(total_rise_in + board_width_in * 2),
        )
        first_cut_box.translate(
            App.Vector(
                bc.inch(start_x_in - 3),
                bc.inch(first_plumb_y - standard_notch_run_in),
                bc.inch(top_z_in - total_rise_in),
            )
        )
        App.Console.PrintMessage(f'[septic_utilities]   First plumb: y={first_plumb_y:.2f}"\n')
        base_board = base_board.cut(first_cut_box)

        # All tread notches - positions increase toward +Y
        for step in range(num_steps):
            level_z = top_z_in - step * rise_per_step_in
            tread_south = header_south_in + step * run_per_step_in
            plumb_y = tread_south

            notch_box = Part.makeBox(
                bc.inch(board_thick_in + 6),
                bc.inch(standard_notch_run_in),
                bc.inch(rise_per_step_in + board_width_in),
            )
            notch_box.translate(
                App.Vector(bc.inch(start_x_in - 3), bc.inch(plumb_y), bc.inch(level_z))
            )
            App.Console.PrintMessage(
                f'[septic_utilities]   Step {step}: plumb_y={plumb_y:.2f}", level_z={level_z:.2f}"\n'
            )
            base_board = base_board.cut(notch_box)

        # Final plumb cut
        last_tread_south = header_south_in + (num_steps - 1) * run_per_step_in
        final_plumb_y = last_tread_south + run_per_step_in
        final_cut_box = Part.makeBox(
            bc.inch(board_thick_in + 6),
            bc.inch(board_length_in),
            bc.inch(total_rise_in + board_width_in * 2),
        )
        final_cut_box.translate(
            App.Vector(
                bc.inch(start_x_in - 3), bc.inch(final_plumb_y), bc.inch(top_z_in - total_rise_in)
            )
        )
        App.Console.PrintMessage(f'[septic_utilities]   Final plumb: y={final_plumb_y:.2f}"\n')
        base_board = base_board.cut(final_cut_box)

        # Bottom horizontal cut
        if landing_z_in is not None:
            bottom_cut_z = landing_z_in
        else:
            bottom_cut_z = top_z_in - num_steps * rise_per_step_in
        bottom_cut_box = Part.makeBox(
            bc.inch(board_thick_in + 6),
            bc.inch(board_length_in * 2),
            bc.inch(total_rise_in + board_width_in * 2),
        )
        bottom_cut_box.translate(
            App.Vector(
                bc.inch(start_x_in - 3),
                bc.inch(header_south_in - board_length_in),
                bc.inch(bottom_cut_z - total_rise_in - board_width_in * 2),
            )
        )
        App.Console.PrintMessage(f'[septic_utilities]   Bottom cut: z={bottom_cut_z:.2f}"\n')
        base_board = base_board.cut(bottom_cut_box)

    elif direction == "south":
        # SOUTH: notches along -Y axis, board thickness along X
        # Treads descend toward -Y
        header_north_in = start_y_in + header_thick_in

        # First plumb cut: at start position, extends NORTH
        first_plumb_y = start_y_in
        first_cut_box = Part.makeBox(
            bc.inch(board_thick_in + 6),
            bc.inch(standard_notch_run_in),
            bc.inch(total_rise_in + board_width_in * 2),
        )
        first_cut_box.translate(
            App.Vector(
                bc.inch(start_x_in - 3), bc.inch(first_plumb_y), bc.inch(top_z_in - total_rise_in)
            )
        )
        App.Console.PrintMessage(f'[septic_utilities]   First plumb: y={first_plumb_y:.2f}"\n')
        base_board = base_board.cut(first_cut_box)

        # All tread notches - positions decrease toward -Y
        for step in range(num_steps):
            level_z = top_z_in - step * rise_per_step_in
            tread_north = header_north_in - step * run_per_step_in
            plumb_y = tread_north

            notch_box = Part.makeBox(
                bc.inch(board_thick_in + 6),
                bc.inch(standard_notch_run_in),
                bc.inch(rise_per_step_in + board_width_in),
            )
            notch_box.translate(
                App.Vector(
                    bc.inch(start_x_in - 3),
                    bc.inch(plumb_y - standard_notch_run_in),  # Extends south from plumb
                    bc.inch(level_z),
                )
            )
            App.Console.PrintMessage(
                f'[septic_utilities]   Step {step}: plumb_y={plumb_y:.2f}", level_z={level_z:.2f}"\n'
            )
            base_board = base_board.cut(notch_box)

        # Final plumb cut - at last tread south edge
        last_tread_north = header_north_in - (num_steps - 1) * run_per_step_in
        final_plumb_y = last_tread_north - run_per_step_in
        final_cut_box = Part.makeBox(
            bc.inch(board_thick_in + 6),
            bc.inch(board_length_in),
            bc.inch(total_rise_in + board_width_in * 2),
        )
        final_cut_box.translate(
            App.Vector(
                bc.inch(start_x_in - 3),
                bc.inch(final_plumb_y - board_length_in),
                bc.inch(top_z_in - total_rise_in),
            )
        )
        App.Console.PrintMessage(f'[septic_utilities]   Final plumb: y={final_plumb_y:.2f}"\n')
        base_board = base_board.cut(final_cut_box)

        # Bottom horizontal cut
        if landing_z_in is not None:
            bottom_cut_z = landing_z_in
        else:
            bottom_cut_z = top_z_in - num_steps * rise_per_step_in
        bottom_cut_box = Part.makeBox(
            bc.inch(board_thick_in + 6),
            bc.inch(board_length_in * 2),
            bc.inch(total_rise_in + board_width_in * 2),
        )
        bottom_cut_box.translate(
            App.Vector(
                bc.inch(start_x_in - 3),
                bc.inch(final_plumb_y - board_length_in),
                bc.inch(bottom_cut_z - total_rise_in - board_width_in * 2),
            )
        )
        App.Console.PrintMessage(f'[septic_utilities]   Bottom cut: z={bottom_cut_z:.2f}"\n')
        base_board = base_board.cut(bottom_cut_box)

    # Create Part::Feature with the cut shape
    stringer = doc.addObject("Part::Feature", name)
    stringer.Shape = base_board

    # Attach catalog metadata
    attach_metadata(stringer, stringer_row, stringer_label, supplier=supplier)

    # Set color (brown for PT lumber)
    try:
        if hasattr(stringer, "ViewObject") and stringer.ViewObject:
            stringer.ViewObject.ShapeColor = (0.55, 0.45, 0.35)
    except Exception:
        pass

    return stringer


def create_stair_run(
    doc,
    catalog_rows,
    run_idx,
    direction,
    tread_count,
    start_x_in,
    start_y_in,
    top_z_in,
    landing_z_in,
    tread_depth_in,
    tread_length_in,
    tread_thick_in,
    rise_per_step_in,
    tread_label="2x12x96_PT",
    stringer_label="2x12x96_PT",
    header_label=None,  # If provided, creates header at start of run
    supplier="lowes",
    tread_overhang_in=1.0,
):
    """
    Create a complete stair run with treads and stringers.

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data
        run_idx: Run number for naming (1, 2, 3, etc.)
        direction: Descent direction ("east", "west", "north", "south")
        tread_count: Number of treads in this run
        start_x_in: X position of first tread (west edge for E/W, or tread position for N/S)
        start_y_in: Y position of first tread (south edge for N/S, or tread position for E/W)
        top_z_in: Z of first tread top surface
        landing_z_in: Z of landing at bottom (for stringer bottom cut)
        tread_depth_in: Tread depth (11.25" for 2x12)
        tread_length_in: Tread length/width (36" for 3' stairs)
        tread_thick_in: Tread thickness (1.5" for 2x lumber)
        rise_per_step_in: Vertical rise per step
        tread_label: Catalog label for tread stock
        stringer_label: Catalog label for stringer stock
        header_label: If provided, creates a header at the start (only Run 1 typically)
        supplier: Supplier for catalog metadata
        tread_overhang_in: Nosing overhang (1" default)

    Returns:
        dict with 'treads', 'stringers', 'header' (if any), and position info for next landing
    """
    from lumber_common import attach_metadata, find_stock

    created = {"treads": [], "stringers": [], "header": None}

    # Look up tread stock
    tread_row = find_stock(catalog_rows, tread_label)

    # Tread spacing accounts for overhang (treads overlap)
    tread_spacing_in = tread_depth_in - tread_overhang_in

    # Direction determines box dimensions and position increments
    # East/West: treads span N-S (length in Y), depth in X
    # North/South: treads span E-W (length in X), depth in Y
    if direction in ("east", "west"):
        box_x = tread_depth_in
        box_y = tread_length_in
    else:  # north, south
        box_x = tread_length_in
        box_y = tread_depth_in

    # Create treads
    for step in range(tread_count):
        tread_top_z = top_z_in - (step * rise_per_step_in)
        tread_z_bottom = tread_top_z - tread_thick_in

        # Calculate position based on direction
        if direction == "east":
            tread_x = start_x_in + (step * tread_spacing_in)
            tread_y = start_y_in
        elif direction == "west":
            tread_x = start_x_in - (step * tread_spacing_in) - tread_depth_in
            tread_y = start_y_in
        elif direction == "north":
            tread_x = start_x_in
            tread_y = start_y_in + (step * tread_spacing_in)
        elif direction == "south":
            tread_x = start_x_in
            tread_y = start_y_in - (step * tread_spacing_in) - tread_depth_in

        tread = doc.addObject("Part::Feature", f"Stair_Run{run_idx}_Tread_{step}")
        tread_box = Part.makeBox(
            bc.inch(box_x),
            bc.inch(box_y),
            bc.inch(tread_thick_in),
        )
        tread_box.Placement.Base = App.Vector(
            bc.inch(tread_x),
            bc.inch(tread_y),
            bc.inch(tread_z_bottom),
        )
        tread.Shape = tread_box

        if tread_row:
            attach_metadata(tread, tread_row, tread_label, supplier=supplier)
        try:
            if hasattr(tread, "ViewObject") and tread.ViewObject:
                tread.ViewObject.ShapeColor = (0.55, 0.45, 0.35)
        except Exception:
            pass

        created["treads"].append(tread)

    # Create header if specified (only for Run 1 typically)
    header_thick_in = 1.5  # Default
    header_depth_in = 11.25  # Default
    if header_label:
        header_row = find_stock(catalog_rows, header_label)
        if header_row:
            header_thick_in = float(header_row["actual_thickness_in"])
            header_depth_in = float(header_row["actual_width_in"])

        # Header position depends on direction
        header_top_z = top_z_in - tread_thick_in
        header_bottom_z = header_top_z - header_depth_in

        if direction == "east":
            # Header at west edge of tread 0, runs N-S
            header_box = Part.makeBox(
                bc.inch(header_thick_in),
                bc.inch(tread_length_in),
                bc.inch(header_depth_in),
            )
            header_box.Placement.Base = App.Vector(
                bc.inch(start_x_in),
                bc.inch(start_y_in),
                bc.inch(header_bottom_z),
            )
        elif direction == "west":
            # Header at east edge of tread 0, runs N-S
            header_box = Part.makeBox(
                bc.inch(header_thick_in),
                bc.inch(tread_length_in),
                bc.inch(header_depth_in),
            )
            header_box.Placement.Base = App.Vector(
                bc.inch(start_x_in - header_thick_in),
                bc.inch(start_y_in),
                bc.inch(header_bottom_z),
            )
        elif direction == "north":
            # Header at south edge of tread 0, runs E-W
            header_box = Part.makeBox(
                bc.inch(tread_length_in),
                bc.inch(header_thick_in),
                bc.inch(header_depth_in),
            )
            header_box.Placement.Base = App.Vector(
                bc.inch(start_x_in),
                bc.inch(start_y_in),
                bc.inch(header_bottom_z),
            )
        elif direction == "south":
            # Header at north edge of tread 0, runs E-W
            header_box = Part.makeBox(
                bc.inch(tread_length_in),
                bc.inch(header_thick_in),
                bc.inch(header_depth_in),
            )
            header_box.Placement.Base = App.Vector(
                bc.inch(start_x_in),
                bc.inch(start_y_in - header_thick_in),
                bc.inch(header_bottom_z),
            )

        header = doc.addObject("Part::Feature", f"Stair_Run{run_idx}_Header")
        header.Shape = header_box
        if header_row:
            attach_metadata(header, header_row, header_label, supplier=supplier)
        try:
            if hasattr(header, "ViewObject") and header.ViewObject:
                header.ViewObject.ShapeColor = (0.55, 0.45, 0.35)
        except Exception:
            pass
        created["header"] = header

    # Create stringers - 4 stringers at 12" OC
    stringer_top_z = top_z_in - tread_thick_in  # Stringer top at first tread bottom

    # Stringer positions depend on direction
    # Stringers run parallel to descent, spaced across tread width
    # If there's a header, stringers start at header's far face (east face for east direction)
    # Determine header_depth for stringer notch calculations
    stringer_header_depth = header_depth_in if header_label else 0.0

    if direction == "east":
        # If header exists, stringers start at header east face (start_x + header_thick)
        stringer_start_x = start_x_in + header_thick_in if header_label else start_x_in
        stringer_offsets = [0.0, 12.0, 24.0, tread_length_in - tread_thick_in]
        for idx, offset in enumerate(stringer_offsets):
            stringer = create_cut_stringer(
                doc=doc,
                catalog_rows=catalog_rows,
                stringer_label=stringer_label,
                name=f"Stair_Run{run_idx}_Stringer_{idx}",
                num_steps=tread_count,
                rise_per_step_in=rise_per_step_in,
                run_per_step_in=tread_spacing_in,
                stringer_thick_in=tread_thick_in,
                start_x_in=stringer_start_x,
                start_y_in=start_y_in + offset,
                top_z_in=stringer_top_z,
                direction=direction,
                supplier=supplier,
                bottom_cut="horizontal",
                landing_z_in=landing_z_in,
                tread_overhang_in=tread_overhang_in,
                header_depth_in=stringer_header_depth,
            )
            if stringer:
                created["stringers"].append(stringer)

    elif direction == "west":
        # If header exists, stringers start at header west face (start_x - header_thick)
        stringer_start_x = start_x_in - header_thick_in if header_label else start_x_in
        stringer_offsets = [0.0, 12.0, 24.0, tread_length_in - tread_thick_in]
        for idx, offset in enumerate(stringer_offsets):
            stringer = create_cut_stringer(
                doc=doc,
                catalog_rows=catalog_rows,
                stringer_label=stringer_label,
                name=f"Stair_Run{run_idx}_Stringer_{idx}",
                num_steps=tread_count,
                rise_per_step_in=rise_per_step_in,
                run_per_step_in=tread_spacing_in,
                stringer_thick_in=tread_thick_in,
                start_x_in=stringer_start_x,
                start_y_in=start_y_in + offset,
                top_z_in=stringer_top_z,
                direction=direction,
                supplier=supplier,
                bottom_cut="horizontal",
                landing_z_in=landing_z_in,
                tread_overhang_in=tread_overhang_in,
                header_depth_in=stringer_header_depth,
            )
            if stringer:
                created["stringers"].append(stringer)

    elif direction == "north":
        # If header exists, stringers start at header north face (start_y + header_thick)
        stringer_start_y = start_y_in + header_thick_in if header_label else start_y_in
        stringer_offsets = [tread_thick_in, 12.0, 24.0, 36.0]
        for idx, offset in enumerate(stringer_offsets):
            stringer = create_cut_stringer(
                doc=doc,
                catalog_rows=catalog_rows,
                stringer_label=stringer_label,
                name=f"Stair_Run{run_idx}_Stringer_{idx}",
                num_steps=tread_count,
                rise_per_step_in=rise_per_step_in,
                run_per_step_in=tread_spacing_in,
                stringer_thick_in=tread_thick_in,
                start_x_in=start_x_in + offset,
                start_y_in=stringer_start_y,
                top_z_in=stringer_top_z,
                direction=direction,
                supplier=supplier,
                bottom_cut="horizontal",
                landing_z_in=landing_z_in,
                tread_overhang_in=tread_overhang_in,
                header_depth_in=stringer_header_depth,
            )
            if stringer:
                created["stringers"].append(stringer)

    elif direction == "south":
        # If header exists, stringers start at header south face (start_y - header_thick)
        stringer_start_y = start_y_in - header_thick_in if header_label else start_y_in
        stringer_offsets = [0.0, 12.0, 24.0, tread_length_in - tread_thick_in]
        for idx, offset in enumerate(stringer_offsets):
            stringer = create_cut_stringer(
                doc=doc,
                catalog_rows=catalog_rows,
                stringer_label=stringer_label,
                name=f"Stair_Run{run_idx}_Stringer_{idx}",
                num_steps=tread_count,
                rise_per_step_in=rise_per_step_in,
                run_per_step_in=tread_spacing_in,
                stringer_thick_in=tread_thick_in,
                start_x_in=start_x_in + offset,
                start_y_in=stringer_start_y,
                top_z_in=stringer_top_z,
                direction=direction,
                supplier=supplier,
                bottom_cut="horizontal",
                landing_z_in=landing_z_in,
                tread_overhang_in=tread_overhang_in,
                header_depth_in=stringer_header_depth,
            )
            if stringer:
                created["stringers"].append(stringer)

    # Calculate end position for next landing
    if direction == "east":
        end_x = start_x_in + ((tread_count - 1) * tread_spacing_in)
        end_y = start_y_in
    elif direction == "west":
        end_x = start_x_in - ((tread_count - 1) * tread_spacing_in)
        end_y = start_y_in
    elif direction == "north":
        end_x = start_x_in
        end_y = start_y_in + ((tread_count - 1) * tread_spacing_in)
    elif direction == "south":
        end_x = start_x_in
        end_y = start_y_in - ((tread_count - 1) * tread_spacing_in)

    created["end_x_in"] = end_x
    created["end_y_in"] = end_y
    created["end_z_in"] = landing_z_in

    return created


def create_landing_support_posts(
    doc,
    catalog_rows,
    landing_x_west_in,
    landing_y_south_in,
    landing_size_in,
    landing_z_top_in,
    slab_z_in,
    post_label="post_4x4x96_PT",
    landing_idx=1,
    supplier="lowes",
    rim_joist_depth_in=11.25,
    rim_joist_thick_in=1.5,
    deck_board_thick_in=1.0,
    incoming_stringer_dir=None,
    outgoing_stringer_dir=None,
):
    """
    Create 4 corner posts to support a stair landing.

    Posts extend from slab up to landing surface level. Stringers bolt to
    the inside face of posts (no notching required). This is simpler and
    stronger than notching, especially at corners where two stringer runs meet.

    Post layout (plan view):
        Post at each corner of landing, inset by half post width so post
        centerline aligns with landing edge. Stringers bolt to inside face.

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data
        landing_x_west_in: X position of landing west edge (inches)
        landing_y_south_in: Y position of landing south edge (inches)
        landing_size_in: Landing size (inches, assumed square)
        landing_z_top_in: Z position of landing top surface (inches) - the walking surface
        slab_z_in: Z position of slab top (inches, typically 0)
        post_label: Catalog label for post stock
        landing_idx: Landing number for naming
        supplier: Supplier for catalog metadata
        rim_joist_depth_in: (unused, kept for API compatibility)
        rim_joist_thick_in: (unused, kept for API compatibility)
        deck_board_thick_in: (unused, kept for API compatibility)
        incoming_stringer_dir: (unused, kept for API compatibility)
        outgoing_stringer_dir: (unused, kept for API compatibility)

    Returns:
        List of Part::Feature objects (4 corner posts)
    """
    from lumber_common import attach_metadata, find_stock

    post_row = find_stock(catalog_rows, post_label)
    if not post_row:
        App.Console.PrintWarning(
            f"[septic_utilities] Post stock '{post_label}' not found in catalog\n"
        )
        return []

    post_size_in = float(post_row["actual_thickness_in"])  # 3.5" for 4x4

    # Post extends from slab to landing top (stringers bolt to inside face of post)
    post_height_in = landing_z_top_in - slab_z_in

    if post_height_in <= 0:
        App.Console.PrintWarning(
            f'[septic_utilities] Invalid post height {post_height_in:.2f}" for landing {landing_idx}\n'
        )
        return []

    # Inset posts from landing corners by half post width
    # This puts post centerline at landing edge, with half the post inside and half outside
    inset = post_size_in / 2.0

    # Corner positions (post center coordinates)
    corner_positions = {
        "SW": (landing_x_west_in + inset, landing_y_south_in + inset),
        "SE": (landing_x_west_in + landing_size_in - inset, landing_y_south_in + inset),
        "NW": (landing_x_west_in + inset, landing_y_south_in + landing_size_in - inset),
        "NE": (
            landing_x_west_in + landing_size_in - inset,
            landing_y_south_in + landing_size_in - inset,
        ),
    }

    posts = []
    for corner_name, (cx, cy) in corner_positions.items():
        # Simple post box - no notches, stringers bolt to inside face
        post_west_in = cx - post_size_in / 2.0
        post_south_in = cy - post_size_in / 2.0

        # Create shape and wrap in Part::Feature (Part::Box doesn't support addProperty)
        post_shape = Part.makeBox(
            bc.inch(post_size_in),
            bc.inch(post_size_in),
            bc.inch(post_height_in),
        )
        post_shape.Placement.Base = App.Vector(
            bc.inch(post_west_in),
            bc.inch(post_south_in),
            bc.inch(slab_z_in),
        )
        post = doc.addObject("Part::Feature", f"Landing_{landing_idx}_Post_{corner_name}")
        post.Shape = post_shape

        attach_metadata(post, post_row, post_label, supplier=supplier)

        # Set color (brown for PT lumber)
        try:
            if hasattr(post, "ViewObject") and post.ViewObject:
                post.ViewObject.ShapeColor = (0.55, 0.45, 0.35)
        except Exception:
            pass

        posts.append(post)

    App.Console.PrintMessage(
        f"[septic_utilities] Landing {landing_idx}: Created 4 corner posts "
        f'({post_size_in:.1f}" x {post_size_in:.1f}" x {post_height_in:.1f}"h, stringers bolt to face)\n'
    )

    return posts


def create_landing_frame(
    doc,
    catalog_rows,
    landing_x_center_in,
    landing_y_center_in,
    landing_size_in,
    landing_z_top_in,
    slab_z_in,
    landing_idx=1,
    post_label="post_4x4x96_PT",
    rim_label="2x12x96_PT",
    deck_board_label="deckboard_5_4x6x96_PT",
    supplier="lowes",
    post_bottom_z_in=None,  # Override post bottom (e.g., for stacked landings)
):
    """
    Create a complete landing frame assembly.

    Structure (from bottom to top):
        1. 4 corner posts (4x4, from slab to rim bottom)
        2. 4 rim joists (2x12 on edge, forming box on posts)
        3. Deck boards (5/4 decking on rim frame)

    The landing_z_top is the top of the deck boards - this is where
    the stringers from above will rest (their horizontal bottom cut
    sits on this surface).

    Args:
        doc: FreeCAD document
        catalog_rows: Loaded catalog data
        landing_x_center_in: X center position (inches)
        landing_y_center_in: Y center position (inches)
        landing_size_in: Outer dimension of landing (inches, square)
        landing_z_top_in: Z of deck board top surface (inches) - where stringers rest
        slab_z_in: Z of slab top (inches, typically 0)
        landing_idx: Landing number for naming
        post_label: Catalog label for 4x4 posts
        rim_label: Catalog label for 2x12 rim joists
        deck_board_label: Catalog label for 5/4 deck boards
        supplier: Supplier for catalog metadata
        post_bottom_z_in: Override for post bottom Z (if None, uses slab_z_in).
                          Use this when a landing sits above another landing.

    Returns:
        Dict with keys: 'posts', 'rims', 'deck_boards', 'group'
    """
    from lumber_common import attach_metadata, find_stock

    # Look up lumber dimensions from catalog
    post_row = find_stock(catalog_rows, post_label)
    rim_row = find_stock(catalog_rows, rim_label)
    deck_row = find_stock(catalog_rows, deck_board_label)

    if not post_row:
        App.Console.PrintWarning(f"[septic_utilities] Post stock '{post_label}' not found\n")
        return None
    if not rim_row:
        App.Console.PrintWarning(f"[septic_utilities] Rim stock '{rim_label}' not found\n")
        return None
    if not deck_row:
        App.Console.PrintWarning(
            f"[septic_utilities] Deck board stock '{deck_board_label}' not found\n"
        )
        return None

    # Actual dimensions from catalog
    post_size_in = float(post_row["actual_thickness_in"])  # 3.5" for 4x4
    rim_depth_in = float(rim_row["actual_width_in"])  # 11.25" for 2x12
    rim_thick_in = float(rim_row["actual_thickness_in"])  # 1.5" for 2x
    deck_thick_in = float(deck_row["actual_thickness_in"])  # 1.0" for 5/4
    deck_width_in = float(deck_row["actual_width_in"])  # 5.5" for 5/4x6

    # Z levels (working down from top)
    deck_board_top_z = landing_z_top_in
    deck_board_bottom_z = deck_board_top_z - deck_thick_in
    rim_top_z = deck_board_bottom_z  # Rim sits under deck boards
    rim_bottom_z = rim_top_z - rim_depth_in
    post_top_z = rim_bottom_z  # Posts support rim from below
    post_bottom_z = post_bottom_z_in if post_bottom_z_in is not None else slab_z_in

    post_height_in = post_top_z - post_bottom_z
    if post_height_in <= 0:
        App.Console.PrintWarning(
            f'[septic_utilities] Invalid post height {post_height_in:.2f}" for landing {landing_idx}\n'
        )
        return None

    # Landing boundaries (from center)
    west_edge = landing_x_center_in - landing_size_in / 2.0
    east_edge = landing_x_center_in + landing_size_in / 2.0
    south_edge = landing_y_center_in - landing_size_in / 2.0
    north_edge = landing_y_center_in + landing_size_in / 2.0

    created_parts = {"posts": [], "rims": [], "deck_boards": [], "group": None}

    # Color for PT lumber
    pt_color = (0.55, 0.45, 0.35)

    # ============================================================
    # 1. CORNER POSTS (4x4, at corners, support rim joists)
    # ============================================================
    # Posts are at corners, inset so outer face aligns with landing edge
    corner_positions = {
        "SW": (west_edge + post_size_in / 2.0, south_edge + post_size_in / 2.0),
        "SE": (east_edge - post_size_in / 2.0, south_edge + post_size_in / 2.0),
        "NW": (west_edge + post_size_in / 2.0, north_edge - post_size_in / 2.0),
        "NE": (east_edge - post_size_in / 2.0, north_edge - post_size_in / 2.0),
    }

    for corner_name, (cx, cy) in corner_positions.items():
        # Create shape and wrap in Part::Feature (Part::Box doesn't support addProperty)
        post_shape = Part.makeBox(
            bc.inch(post_size_in),
            bc.inch(post_size_in),
            bc.inch(post_height_in),
        )
        post_shape.Placement.Base = App.Vector(
            bc.inch(cx - post_size_in / 2.0),
            bc.inch(cy - post_size_in / 2.0),
            bc.inch(post_bottom_z),
        )
        post = doc.addObject("Part::Feature", f"Landing_{landing_idx}_Post_{corner_name}")
        post.Shape = post_shape
        attach_metadata(post, post_row, post_label, supplier=supplier)
        try:
            if hasattr(post, "ViewObject") and post.ViewObject:
                post.ViewObject.ShapeColor = pt_color
        except Exception:
            pass
        created_parts["posts"].append(post)

    # ============================================================
    # 2. RIM JOIST BOX (4x 2x12 forming square frame on posts)
    # ============================================================
    # Rim joists sit ON TOP of posts, forming a box frame
    # The box outer dimension = landing_size
    # Each rim runs along one edge

    # South rim (runs E-W along south edge)
    south_rim_shape = Part.makeBox(
        bc.inch(landing_size_in),  # Full width E-W
        bc.inch(rim_thick_in),
        bc.inch(rim_depth_in),
    )
    south_rim_shape.Placement.Base = App.Vector(
        bc.inch(west_edge),
        bc.inch(south_edge),
        bc.inch(rim_bottom_z),
    )
    south_rim = doc.addObject("Part::Feature", f"Landing_{landing_idx}_Rim_South")
    south_rim.Shape = south_rim_shape
    attach_metadata(south_rim, rim_row, rim_label, supplier=supplier)
    try:
        if hasattr(south_rim, "ViewObject") and south_rim.ViewObject:
            south_rim.ViewObject.ShapeColor = pt_color
    except Exception:
        pass
    created_parts["rims"].append(south_rim)

    # North rim (runs E-W along north edge)
    north_rim_shape = Part.makeBox(
        bc.inch(landing_size_in),
        bc.inch(rim_thick_in),
        bc.inch(rim_depth_in),
    )
    north_rim_shape.Placement.Base = App.Vector(
        bc.inch(west_edge),
        bc.inch(north_edge - rim_thick_in),
        bc.inch(rim_bottom_z),
    )
    north_rim = doc.addObject("Part::Feature", f"Landing_{landing_idx}_Rim_North")
    north_rim.Shape = north_rim_shape
    attach_metadata(north_rim, rim_row, rim_label, supplier=supplier)
    try:
        if hasattr(north_rim, "ViewObject") and north_rim.ViewObject:
            north_rim.ViewObject.ShapeColor = pt_color
    except Exception:
        pass
    created_parts["rims"].append(north_rim)

    # West rim (runs N-S along west edge, between south and north rims)
    west_rim_length = landing_size_in - 2 * rim_thick_in
    west_rim_shape = Part.makeBox(
        bc.inch(rim_thick_in),
        bc.inch(west_rim_length),
        bc.inch(rim_depth_in),
    )
    west_rim_shape.Placement.Base = App.Vector(
        bc.inch(west_edge),
        bc.inch(south_edge + rim_thick_in),
        bc.inch(rim_bottom_z),
    )
    west_rim = doc.addObject("Part::Feature", f"Landing_{landing_idx}_Rim_West")
    west_rim.Shape = west_rim_shape
    attach_metadata(west_rim, rim_row, rim_label, supplier=supplier)
    try:
        if hasattr(west_rim, "ViewObject") and west_rim.ViewObject:
            west_rim.ViewObject.ShapeColor = pt_color
    except Exception:
        pass
    created_parts["rims"].append(west_rim)

    # East rim (runs N-S along east edge, between south and north rims)
    east_rim_shape = Part.makeBox(
        bc.inch(rim_thick_in),
        bc.inch(west_rim_length),  # Same as west rim
        bc.inch(rim_depth_in),
    )
    east_rim_shape.Placement.Base = App.Vector(
        bc.inch(east_edge - rim_thick_in),
        bc.inch(south_edge + rim_thick_in),
        bc.inch(rim_bottom_z),
    )
    east_rim = doc.addObject("Part::Feature", f"Landing_{landing_idx}_Rim_East")
    east_rim.Shape = east_rim_shape
    attach_metadata(east_rim, rim_row, rim_label, supplier=supplier)
    try:
        if hasattr(east_rim, "ViewObject") and east_rim.ViewObject:
            east_rim.ViewObject.ShapeColor = pt_color
    except Exception:
        pass
    created_parts["rims"].append(east_rim)

    # ============================================================
    # 3. DECK BOARDS (5/4 decking on rim frame) - 45 degree angle
    # ============================================================
    # Deck boards run at 45 degrees since landings have 90 degree turns
    # Deck boards extend to OUTSIDE edges of rim joists (full landing size)
    board_spacing_in = 0.125  # 1/8" gap between boards

    # For 45 degree boards, the diagonal of the landing is sqrt(2) * landing_size
    # Boards need to be longer than the diagonal to cover corner to corner
    import math

    diagonal_span = math.sqrt(2) * landing_size_in
    board_length_in = diagonal_span + deck_width_in * 2  # Extra length for clipping

    # Calculate number of boards needed to cover the diagonal
    # The width perpendicular to the boards that needs covering is sqrt(2) * landing_size
    num_boards = int((diagonal_span + board_spacing_in) / (deck_width_in + board_spacing_in)) + 2

    # Center point of the landing (full landing size, not inner)
    center_x = west_edge + landing_size_in / 2.0
    center_y = south_edge + landing_size_in / 2.0

    # Create a clipping box matching the FULL landing area (outside edges of rim joists)
    clip_box = Part.makeBox(
        bc.inch(landing_size_in),
        bc.inch(landing_size_in),
        bc.inch(deck_thick_in + 1),  # Slightly taller to ensure full intersection
    )
    clip_box.translate(
        App.Vector(
            bc.inch(west_edge),
            bc.inch(south_edge),
            bc.inch(deck_board_bottom_z - 0.5),
        )
    )

    board_count = 0
    # Boards are centered on the landing center, offset perpendicular to 45 degree line
    # First board starts at SW corner, last at NE corner
    for i in range(-num_boards // 2, num_boards // 2 + 1):
        # Offset perpendicular to the 45-degree board direction
        offset = i * (deck_width_in + board_spacing_in)

        # Create board at origin, then rotate and translate
        board_shape = Part.makeBox(
            bc.inch(board_length_in),
            bc.inch(deck_width_in),
            bc.inch(deck_thick_in),
        )

        # Position board centered at origin for rotation
        board_shape.translate(
            App.Vector(
                bc.inch(-board_length_in / 2.0),
                bc.inch(-deck_width_in / 2.0),
                0,
            )
        )

        # Rotate 45 degrees around Z axis
        board_shape.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 45)

        # Translate to landing center, then offset perpendicular to board direction
        # Perpendicular direction at 45 degrees is (-sin45, cos45) = (-0.707, 0.707)
        perp_x = -offset * math.sin(math.radians(45))
        perp_y = offset * math.cos(math.radians(45))

        board_shape.translate(
            App.Vector(
                bc.inch(center_x + perp_x),
                bc.inch(center_y + perp_y),
                bc.inch(deck_board_bottom_z),
            )
        )

        # Clip to landing area using boolean intersection
        try:
            clipped_shape = board_shape.common(clip_box)
            if clipped_shape.Volume > 0:
                board_count += 1
                deck_board = doc.addObject(
                    "Part::Feature", f"Landing_{landing_idx}_DeckBoard_{board_count}"
                )
                deck_board.Shape = clipped_shape
                attach_metadata(deck_board, deck_row, deck_board_label, supplier=supplier)
                try:
                    if hasattr(deck_board, "ViewObject") and deck_board.ViewObject:
                        deck_board.ViewObject.ShapeColor = pt_color
                except Exception:
                    pass
                created_parts["deck_boards"].append(deck_board)
        except Exception:
            # Skip boards that don't intersect the landing
            pass

    num_boards = board_count  # Update for logging

    # Create group for landing
    landing_grp = bc.create_group(doc, f"Landing_{landing_idx}_Frame")
    all_parts = created_parts["posts"] + created_parts["rims"] + created_parts["deck_boards"]
    bc.add_to_group(landing_grp, all_parts)
    created_parts["group"] = landing_grp

    App.Console.PrintMessage(
        f"[septic_utilities] Landing {landing_idx} frame: "
        f'4 posts ({post_size_in:.1f}"x{post_height_in:.1f}"h), '
        f'4 rim joists ({rim_thick_in:.1f}"x{rim_depth_in:.1f}"), '
        f"{num_boards} deck boards, "
        f'top Z={landing_z_top_in:.1f}"\n'
    )

    return created_parts


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

    Supports two stair types:
        - "straight": Single run descending in one direction (default)
        - "L": L-shaped stair with landing and 90 degrees turn

    L-Stair Configuration (when stair_type == "L"):
        - run1_direction: Direction for Run 1 (e.g., "north")
        - run1_tread_count: Number of treads in Run 1
        - landing_size_ft: Landing platform size (3' x 3' typical)
        - landing_turn: Turn direction at landing ("left" or "right")
        - run2_direction: Direction for Run 2 (e.g., "west")

    Args:
        doc: FreeCAD document
        stairs_config: STAIRS config dict with keys:
            - stair_x_ft: X position (east side of house)
            - stair_y_snap_ft: Y position where top tread south edge meets floor rim
            - tread_rise_in: Riser height (7.25")
            - tread_run_in: Tread depth (10")
            - tread_width_ft: Stair width (3')
            - tread_stock: Lumber stock label
            - stair_type: "straight" or "L" (default: "straight")
        floor_z_ft: First floor elevation (default 20', top of joists)
        slab_z_ft: Slab elevation (default 0', top of concrete)

    Returns:
        Group containing all stair treads
    """
    stair_type = stairs_config.get("stair_type", "straight")
    App.Console.PrintMessage(
        f"[septic_utilities] Creating exterior stairs ({stair_type} type, descending from floor to slab)...\n"
    )

    x_ft = stairs_config["stair_x_ft"]
    y_snap_ft = stairs_config["stair_y_snap_ft"]  # Top tread south edge position
    rise_in = stairs_config["tread_rise_in"]
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
        f'[septic_utilities] Stair calculation: {total_rise_in:.2f}" rise (slab {slab_top_z_in:.1f}" -> deck surface {deck_surface_z_in:.1f}") ÷ {rise_in:.2f}" target = '
        f'{num_risers} risers @ {actual_rise_in:.4f}" each, {num_treads} treads\n'
    )

    created = []

    # Check stair type
    if stair_type == "L":
        # L-STAIR: Two runs with a landing between
        run1_tread_count = stairs_config.get("run1_tread_count", 6)
        landing_size_ft = stairs_config.get("landing_size_ft", 3.0)
        landing_turn = stairs_config.get("landing_turn", "left")
        run2_direction = stairs_config.get("run2_direction", "west")

        # Run 2 tread count: total treads minus Run 1 treads
        run2_tread_count = num_treads - run1_tread_count

        # TREAD 0 OFFSET: Start one rise below deck surface for head clearance
        # This gives us an extra rise worth of clearance under the floor joists
        tread0_z_offset_in = actual_rise_in  # Drop tread 0 by one rise

        # Y OFFSET: y_snap_ft already includes landing_depth (3' north of front rim)
        # No additional shift needed - the config calculation handles the deck landing space
        tread0_y_offset_in = 0.0  # No additional Y offset

        App.Console.PrintMessage(
            f"[septic_utilities] L-stair: Run 1 = {run1_tread_count} treads (north), "
            f"Landing = {landing_size_ft}' x {landing_size_ft}', "
            f"Run 2 = {run2_tread_count} treads ({run2_direction})\n"
        )
        App.Console.PrintMessage(
            f'[septic_utilities] L-stair offsets: tread 0 dropped {tread0_z_offset_in:.2f}" below deck, '
            f"shifted {tread0_y_offset_in:.2f}\" south for {landing_size_ft}' deck landing\n"
        )

        # Landing size in inches (needed for clearance calculation)
        landing_size_in = landing_size_ft * 12.0

        # HEAD CLEARANCE CALCULATION
        # Floor joists start at Y=30' (first floor module at front_setback + pile_spacing_y)
        # Treads south of Y=30' are in the front deck area (open above)
        # Treads at or north of Y=30' are under the first floor
        # Joist bottom = above_grade_ft * 12 = 240" (at Y positions where joists exist)
        joist_bottom_z_in = floor_z_ft * 12.0  # 240" for 20' above grade
        floor_start_y_in = (
            30.0 * 12.0
        )  # First floor starts at Y=30' (front_setback + pile_spacing_y)

        # Calculate clearance at each Run 1 tread
        App.Console.PrintMessage(
            '[septic_utilities] HEAD CLEARANCE CHECK (IRC R311.7.2 requires 80" min):\n'
        )
        App.Console.PrintMessage(
            f"[septic_utilities]   Floor joists start at Y={floor_start_y_in/12:.1f}' (treads south of this are in open deck area)\n"
        )
        for step in range(run1_tread_count):
            # Tread top Z (with offset)
            tread_top_z_in = deck_surface_z_in - tread0_z_offset_in - (step * actual_rise_in)
            # Tread Y position (south edge, with offset)
            tread_y_south_in = (y_snap_ft * 12.0) - tread0_y_offset_in + (step * tread_depth_in)
            # Tread north edge
            tread_y_north_in = tread_y_south_in + tread_depth_in

            # Check if tread is under floor joists (north edge >= floor start)
            if tread_y_north_in >= floor_start_y_in:
                clearance_in = joist_bottom_z_in - tread_top_z_in
                status = "(correct) OK" if clearance_in >= 80.0 else "⚠ LOW"
                App.Console.PrintMessage(
                    f"[septic_utilities]   Tread {step}: Y={tread_y_south_in/12:.2f}'-{tread_y_north_in/12:.2f}', Z top={tread_top_z_in:.1f}\", clearance={clearance_in:.1f}\" {status} (UNDER FLOOR)\n"
                )
            else:
                App.Console.PrintMessage(
                    f"[septic_utilities]   Tread {step}: Y={tread_y_south_in/12:.2f}'-{tread_y_north_in/12:.2f}', Z top={tread_top_z_in:.1f}\" (in deck area, open above)\n"
                )

        # Landing clearance
        landing_z_top_in = (
            deck_surface_z_in - tread0_z_offset_in - (run1_tread_count * actual_rise_in)
        )
        landing_y_south_in = (
            (y_snap_ft * 12.0) - tread0_y_offset_in + (run1_tread_count * tread_depth_in)
        )
        landing_y_north_in = landing_y_south_in + landing_size_in
        if landing_y_north_in >= floor_start_y_in:
            landing_clearance_in = joist_bottom_z_in - landing_z_top_in
            landing_status = "(correct) OK" if landing_clearance_in >= 80.0 else "⚠ LOW"
            App.Console.PrintMessage(
                f"[septic_utilities]   Landing: Y={landing_y_south_in/12:.2f}'-{landing_y_north_in/12:.2f}', Z top={landing_z_top_in:.1f}\", clearance={landing_clearance_in:.1f}\" {landing_status} (UNDER FLOOR)\n"
            )
        else:
            App.Console.PrintMessage(
                f"[septic_utilities]   Landing: Y={landing_y_south_in/12:.2f}'-{landing_y_north_in/12:.2f}', Z top={landing_z_top_in:.1f}\" (in deck area, open above)\n"
            )

        # ===== RUN 1: Treads 0 through run1_tread_count-1 (descending NORTH) =====
        for step in range(run1_tread_count):
            # Z position: all treads descend from deck surface - offset
            tread_top_z_in = deck_surface_z_in - tread0_z_offset_in - (step * actual_rise_in)
            tread_z_bottom_in = tread_top_z_in - tread_thick_in

            # Y position: descending north (+Y), with south offset for deck landing
            tread_y_south_in = (y_snap_ft * 12.0) - tread0_y_offset_in + (step * tread_depth_in)

            # Create tread
            tread = doc.addObject("Part::Feature", f"Stair_Run1_Tread_{step}")
            tread_box = Part.makeBox(
                bc.inch(tread_length_in),
                bc.inch(tread_depth_in),
                bc.inch(tread_thick_in),
            )
            tread_box.Placement.Base = App.Vector(
                bc.ft(x_ft),
                bc.inch(tread_y_south_in),
                bc.inch(tread_z_bottom_in),
            )
            tread.Shape = tread_box

            if tread_row:
                attach_metadata(tread, tread_row, tread_label, supplier="lowes")
            try:
                if hasattr(tread, "ViewObject") and tread.ViewObject:
                    tread.ViewObject.ShapeColor = (0.55, 0.45, 0.35)
            except Exception:
                pass

            created.append(tread)

        # ===== LANDING: Platform at Run 1 bottom / Run 2 top =====
        # Landing Z: one rise below the last Run 1 tread (with tread0 offset applied)
        landing_z_top_in = (
            deck_surface_z_in - tread0_z_offset_in - (run1_tread_count * actual_rise_in)
        )
        landing_z_bottom_in = landing_z_top_in - tread_thick_in

        # Landing position: at the north end of Run 1 (with Y offset applied)
        # South edge of landing = north edge of last Run 1 tread
        landing_y_south_in = (
            (y_snap_ft * 12.0) - tread0_y_offset_in + (run1_tread_count * tread_depth_in)
        )

        # Landing X: depends on turn direction
        # For "left" turn (west), landing extends west from Run 1 east edge
        if landing_turn == "left":
            # Run 1 east edge = x_ft + tread_width_ft
            # Landing west edge = run1 west edge (x_ft)
            landing_x_in = x_ft * 12.0
        else:
            # For "right" turn (east), landing extends east from Run 1
            landing_x_in = x_ft * 12.0

        landing = doc.addObject("Part::Feature", "Stair_Landing")
        landing_box = Part.makeBox(
            bc.inch(landing_size_in),  # X dimension
            bc.inch(landing_size_in),  # Y dimension
            bc.inch(tread_thick_in),  # Z dimension (same as treads)
        )
        landing_box.Placement.Base = App.Vector(
            bc.inch(landing_x_in),
            bc.inch(landing_y_south_in),
            bc.inch(landing_z_bottom_in),
        )
        landing.Shape = landing_box

        if tread_row:
            attach_metadata(landing, tread_row, tread_label, supplier="lowes")
        try:
            if hasattr(landing, "ViewObject") and landing.ViewObject:
                landing.ViewObject.ShapeColor = (0.55, 0.45, 0.35)
        except Exception:
            pass

        created.append(landing)

        # ===== RUN 2: Remaining treads descending WEST =====
        # Run 2 starts from the landing, descending west (-X)
        # First Run 2 tread is one rise below landing
        for step in range(run2_tread_count):
            tread_top_z_in = landing_z_top_in - ((step + 1) * actual_rise_in)
            tread_z_bottom_in = tread_top_z_in - tread_thick_in

            if run2_direction == "west":
                # Descending west: X decreases, Y stays at landing center
                # Tread runs north-south (Y direction), descending west (-X)
                tread_x_east_in = landing_x_in - (step * tread_depth_in)
                tread_y_south_in = landing_y_south_in  # Same Y as landing south edge

                tread = doc.addObject("Part::Feature", f"Stair_Run2_Tread_{step}")
                tread_box = Part.makeBox(
                    bc.inch(tread_depth_in),  # X dimension (run)
                    bc.inch(tread_length_in),  # Y dimension (width = 3')
                    bc.inch(tread_thick_in),  # Z dimension
                )
                tread_box.Placement.Base = App.Vector(
                    bc.inch(tread_x_east_in - tread_depth_in),  # West edge
                    bc.inch(tread_y_south_in),
                    bc.inch(tread_z_bottom_in),
                )
                tread.Shape = tread_box
            else:
                # Other directions (east, south) - implement as needed
                # For now, default to west behavior
                tread_x_east_in = landing_x_in - (step * tread_depth_in)
                tread_y_south_in = landing_y_south_in

                tread = doc.addObject("Part::Feature", f"Stair_Run2_Tread_{step}")
                tread_box = Part.makeBox(
                    bc.inch(tread_depth_in),
                    bc.inch(tread_length_in),
                    bc.inch(tread_thick_in),
                )
                tread_box.Placement.Base = App.Vector(
                    bc.inch(tread_x_east_in - tread_depth_in),
                    bc.inch(tread_y_south_in),
                    bc.inch(tread_z_bottom_in),
                )
                tread.Shape = tread_box

            if tread_row:
                attach_metadata(tread, tread_row, tread_label, supplier="lowes")
            try:
                if hasattr(tread, "ViewObject") and tread.ViewObject:
                    tread.ViewObject.ShapeColor = (0.55, 0.45, 0.35)
            except Exception:
                pass

            created.append(tread)

    elif stair_type == "double_L":
        # DOUBLE-L STAIR: Three runs with two 90 degrees landings (east -> north -> west)
        # Configuration from stairs_config
        run1_direction = stairs_config.get("run1_direction", "east")
        run1_tread_count = stairs_config.get("run1_tread_count", 6)

        run2_direction = stairs_config.get("run2_direction", "north")
        run2_tread_count = stairs_config.get("run2_tread_count", 6)

        run3_direction = stairs_config.get("run3_direction", "west")
        # Run 3 tread count: can be specified or calculated
        run3_tread_count_config = stairs_config.get("run3_tread_count", None)

        # Landing 3 and Run 4
        landing3_turn = stairs_config.get("landing3_turn", None)
        run4_direction = stairs_config.get("run4_direction", None)
        run4_tread_count_config = stairs_config.get("run4_tread_count", None)

        # Landing 4 and Run 5 (optional - for 5-run stair)
        landing4_turn = stairs_config.get("landing4_turn", None)
        run5_direction = stairs_config.get("run5_direction", None)
        run5_tread_count_config = stairs_config.get("run5_tread_count", None)

        # Landing 5 and Run 6 (optional - for 6-run stair)
        landing5_turn = stairs_config.get("landing5_turn", None)
        run6_direction = stairs_config.get("run6_direction", None)

        # ===== DERIVE LANDING SIZE FROM TREAD WIDTH =====
        # Landing size is derived, not configured. Reasoning:
        # - Walkable deck area must be 36"x36" (code requirement for stair width)
        # - Posts at corners with outer face at landing edge
        # - Railings mount to posts, reducing walkable area
        # - Interior clear space = landing_size - 2*(post_size + railing_thick)
        # Formula: landing_size = tread_length + 2*(post_size + railing_thick)

        # Get post dimensions from catalog for landing sizing calculations
        post_label = "post_4x4x96_PT"
        post_row = find_stock(rows, post_label)
        if post_row:
            post_size_in = float(post_row["actual_thickness_in"])  # 3.5" for 4x4
        else:
            post_size_in = 3.5  # Fallback

        # Get railing width from catalog (2x4 top/bottom rails - 3.5" wide)
        railing_label = "2x4x96_PT"
        railing_row = find_stock(rows, railing_label)
        if railing_row:
            railing_width_in = float(railing_row["actual_width_in"])  # 3.5" for 2x4
        else:
            railing_width_in = 3.5  # Fallback

        # Landing size = tread_length + 2*(post + railing) = 36 + 2*(3.5 + 3.5) = 50"
        landing_size_in_derived = tread_length_in + (2.0 * (post_size_in + railing_width_in))

        # Offset to center treads on landing (half the perimeter allowance)
        landing_tread_offset_in = post_size_in + railing_width_in  # 7" each side

        # Convert to feet for legacy compatibility in log messages
        landing1_size_ft = landing_size_in_derived / 12.0
        landing2_size_ft = landing_size_in_derived / 12.0
        landing3_size_ft = landing_size_in_derived / 12.0

        # Determine stair complexity (based on turn config, not landing size)
        has_landing3 = landing3_turn is not None
        has_landing4 = landing4_turn is not None
        has_landing5 = landing5_turn is not None

        # Calculate tread counts based on stair configuration
        if has_landing5:
            # 6-run stair: Run 3, Run 4, Run 5 counts specified, Run 6 calculated
            run3_tread_count = run3_tread_count_config if run3_tread_count_config else 4
            run4_tread_count = run4_tread_count_config if run4_tread_count_config else 3
            run5_tread_count = run5_tread_count_config if run5_tread_count_config else 4
            # Run 6 = remaining after Run1 + L1 + Run2 + L2 + Run3 + L3 + Run4 + L4 + Run5 + L5
            # 5 landings total, each counts as 1 rise
            # Subtract 6 total: 5 landings + 1 for tread0 offset (first tread is 1 rise below deck)
            run6_tread_count = (
                num_treads
                - run1_tread_count
                - run2_tread_count
                - run3_tread_count
                - run4_tread_count
                - run5_tread_count
                - 6
            )
        elif has_landing4:
            # 5-run stair: Run 3, Run 4 counts specified, Run 5 calculated
            run3_tread_count = run3_tread_count_config if run3_tread_count_config else 4
            run4_tread_count = run4_tread_count_config if run4_tread_count_config else 3
            # Run 5 = remaining after Run1 + L1 + Run2 + L2 + Run3 + L3 + Run4 + L4
            # 4 landings total, each counts as 1 rise
            # Subtract 5 total: 4 landings + 1 for tread0 offset (first tread is 1 rise below deck)
            run5_tread_count = (
                num_treads
                - run1_tread_count
                - run2_tread_count
                - run3_tread_count
                - run4_tread_count
                - 5
            )
            run6_tread_count = 0
        elif has_landing3:
            # 4-run stair (switchback): Run 3 count specified, Run 4 calculated
            run3_tread_count = run3_tread_count_config if run3_tread_count_config else 12
            # Subtract 4 total: 3 landings + 1 for tread0 offset
            run4_tread_count = (
                num_treads - run1_tread_count - run2_tread_count - run3_tread_count - 4
            )
            run5_tread_count = 0
            run6_tread_count = 0
        else:
            # 3-run stair: Run 3 gets all remaining treads
            # Subtract 3 total: 2 landings + 1 for tread0 offset
            run3_tread_count = num_treads - run1_tread_count - run2_tread_count - 3
            run4_tread_count = 0
            run5_tread_count = 0
            run6_tread_count = 0

        # All landings use the derived size
        landing1_size_in = landing_size_in_derived
        landing2_size_in = landing_size_in_derived
        landing3_size_in = landing_size_in_derived if has_landing3 else 0.0
        landing4_size_in = landing_size_in_derived if has_landing4 else 0.0
        landing5_size_in = landing_size_in_derived if has_landing5 else 0.0

        # TREAD 0 OFFSET: Start one rise below deck surface for head clearance
        tread0_z_offset_in = actual_rise_in  # Drop tread 0 by one rise

        if has_landing5:
            App.Console.PrintMessage(
                f"[septic_utilities] 6-Run spiral stair: "
                f"Run 1 = {run1_tread_count} ({run1_direction}), "
                f"L1, Run 2 = {run2_tread_count} ({run2_direction}), "
                f"L2, Run 3 = {run3_tread_count} ({run3_direction}), "
                f"L3, Run 4 = {run4_tread_count} ({run4_direction}), "
                f"L4, Run 5 = {run5_tread_count} ({run5_direction}), "
                f"L5, Run 6 = {run6_tread_count} ({run6_direction})\n"
            )
        elif has_landing4:
            App.Console.PrintMessage(
                f"[septic_utilities] 5-Run spiral stair: "
                f"Run 1 = {run1_tread_count} ({run1_direction}), "
                f"L1, Run 2 = {run2_tread_count} ({run2_direction}), "
                f"L2, Run 3 = {run3_tread_count} ({run3_direction}), "
                f"L3, Run 4 = {run4_tread_count} ({run4_direction}), "
                f"L4, Run 5 = {run5_tread_count} ({run5_direction})\n"
            )
        elif has_landing3:
            App.Console.PrintMessage(
                f"[septic_utilities] Double-L + Switchback stair: "
                f"Run 1 = {run1_tread_count} treads ({run1_direction}), "
                f"Landing 1 = {landing1_size_ft}' x {landing1_size_ft}', "
                f"Run 2 = {run2_tread_count} treads ({run2_direction}), "
                f"Landing 2 = {landing2_size_ft}' x {landing2_size_ft}', "
                f"Run 3 = {run3_tread_count} treads ({run3_direction}), "
                f"Landing 3 = {landing3_size_ft}' x {landing3_size_ft}' ({landing3_turn}), "
                f"Run 4 = {run4_tread_count} treads ({run4_direction})\n"
            )
        else:
            App.Console.PrintMessage(
                f"[septic_utilities] Double-L stair: "
                f"Run 1 = {run1_tread_count} treads ({run1_direction}), "
                f"Landing 1 = {landing1_size_ft}' x {landing1_size_ft}', "
                f"Run 2 = {run2_tread_count} treads ({run2_direction}), "
                f"Landing 2 = {landing2_size_ft}' x {landing2_size_ft}', "
                f"Run 3 = {run3_tread_count} treads ({run3_direction})\n"
            )

        # ===== RUN 1: Descending EAST =====
        # Use create_stair_run helper function
        tread_overhang_in = stairs_config.get("tread_overhang_in", 1.0)
        tread_spacing_in = tread_depth_in - tread_overhang_in  # 11.25 - 1 = 10.25"

        # Landing 1 Z: one rise below last Run 1 tread top
        landing1_z_top_in = (
            deck_surface_z_in - tread0_z_offset_in - (run1_tread_count * actual_rise_in)
        )

        run1_result = create_stair_run(
            doc=doc,
            catalog_rows=rows,
            run_idx=1,
            direction="east",
            tread_count=run1_tread_count,
            start_x_in=x_ft * 12.0,
            start_y_in=y_snap_ft * 12.0,
            top_z_in=deck_surface_z_in - tread0_z_offset_in,
            landing_z_in=landing1_z_top_in,
            tread_depth_in=tread_depth_in,
            tread_length_in=tread_length_in,
            tread_thick_in=tread_thick_in,
            rise_per_step_in=actual_rise_in,
            tread_label=tread_label,
            stringer_label="2x12x96_PT",
            header_label="2x12x48_PT",  # Only Run 1 has a header
            supplier="lowes",
            tread_overhang_in=tread_overhang_in,
        )
        created.extend(run1_result["treads"])
        if run1_result["header"]:
            created.append(run1_result["header"])
        created.extend(run1_result["stringers"])

        # Landing 1 position: at the east end of Run 1
        # Landing west edge = last tread west edge
        # Last tread (index run1_tread_count - 1) west edge = x_ft + ((run1_tread_count - 1) * tread_spacing)
        last_tread_west_in = (x_ft * 12.0) + ((run1_tread_count - 1) * tread_spacing_in)
        landing1_x_west_in = last_tread_west_in
        # Landing 1 south edge: offset south by landing_tread_offset so Run 1 treads are centered on landing
        # Run 1 treads have south edge at y_snap_ft, so landing south edge = y_snap - offset
        landing1_y_south_in = (y_snap_ft * 12.0) - landing_tread_offset_in

        # Convert to center coordinates for create_landing_frame()
        landing1_x_center_in = landing1_x_west_in + landing1_size_in / 2.0
        landing1_y_center_in = landing1_y_south_in + landing1_size_in / 2.0

        # Create landing frame (posts + rim joists + deck boards)
        landing1_frame = create_landing_frame(
            doc=doc,
            catalog_rows=rows,
            landing_x_center_in=landing1_x_center_in,
            landing_y_center_in=landing1_y_center_in,
            landing_size_in=landing1_size_in,
            landing_z_top_in=landing1_z_top_in,
            slab_z_in=slab_top_z_in,
            landing_idx=1,
            post_label="post_4x4x96_PT",
            rim_label="2x12x96_PT",
            deck_board_label="deckboard_5_4x6x96_PT",
            supplier="lowes",
        )
        if landing1_frame:
            created.append(landing1_frame["group"])

        # ===== RUN 2: Descending NORTH =====
        # Use create_stair_run helper function
        # Landing 2 Z: one rise below last Run 2 tread
        landing2_z_top_in = landing1_z_top_in - ((run2_tread_count + 1) * actual_rise_in)

        # Run 2 starts at landing 1 north edge, offset to center on landing
        run2_start_x_in = landing1_x_west_in + landing_tread_offset_in
        run2_start_y_in = landing1_y_south_in + landing1_size_in

        run2_result = create_stair_run(
            doc=doc,
            catalog_rows=rows,
            run_idx=2,
            direction="north",
            tread_count=run2_tread_count,
            start_x_in=run2_start_x_in,
            start_y_in=run2_start_y_in,
            top_z_in=landing1_z_top_in
            - actual_rise_in,  # First Run 2 tread is one rise below landing 1
            landing_z_in=landing2_z_top_in,
            tread_depth_in=tread_depth_in,
            tread_length_in=tread_length_in,
            tread_thick_in=tread_thick_in,
            rise_per_step_in=actual_rise_in,
            tread_label=tread_label,
            stringer_label="2x12x96_PT",
            header_label="2x12x96_PT",  # Header for Run 2
            supplier="lowes",
            tread_overhang_in=tread_overhang_in,
        )
        created.extend(run2_result["treads"])
        if run2_result["header"]:
            created.append(run2_result["header"])
        created.extend(run2_result["stringers"])

        # Landing 2 position: at the north end of Run 2
        # Landing 2 south edge = last tread south edge (same pattern as Landing 1)
        # Last Run 2 tread south edge = run2_start_y_in + ((run2_tread_count - 1) * tread_spacing_in)
        last_run2_tread_south_in = run2_start_y_in + ((run2_tread_count - 1) * tread_spacing_in)
        landing2_y_south_in = last_run2_tread_south_in

        # Landing 2 west edge aligns with Landing 1 west edge
        landing2_x_west_in = landing1_x_west_in

        # Convert to center coordinates for create_landing_frame()
        landing2_x_center_in = landing2_x_west_in + landing2_size_in / 2.0
        landing2_y_center_in = landing2_y_south_in + landing2_size_in / 2.0

        # Create landing frame (posts + rim joists + deck boards)
        landing2_frame = create_landing_frame(
            doc=doc,
            catalog_rows=rows,
            landing_x_center_in=landing2_x_center_in,
            landing_y_center_in=landing2_y_center_in,
            landing_size_in=landing2_size_in,
            landing_z_top_in=landing2_z_top_in,
            slab_z_in=slab_top_z_in,
            landing_idx=2,
            post_label="post_4x4x96_PT",
            rim_label="2x12x96_PT",
            deck_board_label="deckboard_5_4x6x96_PT",
            supplier="lowes",
        )
        if landing2_frame:
            created.append(landing2_frame["group"])

        # ===== RUN 3: Descending WEST =====
        # Use create_stair_run helper function
        # Landing 3 Z: one rise below last Run 3 tread
        landing3_z_top_in = landing2_z_top_in - ((run3_tread_count + 1) * actual_rise_in)

        # Run 3 starts at landing 2 west edge, offset to center on landing
        run3_start_x_in = landing2_x_west_in
        run3_start_y_in = landing2_y_south_in + landing_tread_offset_in

        run3_result = create_stair_run(
            doc=doc,
            catalog_rows=rows,
            run_idx=3,
            direction="west",
            tread_count=run3_tread_count,
            start_x_in=run3_start_x_in,
            start_y_in=run3_start_y_in,
            top_z_in=landing2_z_top_in
            - actual_rise_in,  # First Run 3 tread is one rise below landing 2
            landing_z_in=landing3_z_top_in,
            tread_depth_in=tread_depth_in,
            tread_length_in=tread_length_in,
            tread_thick_in=tread_thick_in,
            rise_per_step_in=actual_rise_in,
            tread_label=tread_label,
            stringer_label="2x12x96_PT",
            header_label="2x12x96_PT",  # Header for Run 3
            supplier="lowes",
            tread_overhang_in=tread_overhang_in,
        )
        created.extend(run3_result["treads"])
        if run3_result["header"]:
            created.append(run3_result["header"])
        created.extend(run3_result["stringers"])

        # ===== LANDING 3 and RUN 4 =====
        if has_landing3:

            # Landing 3 position: at the west end of Run 3
            # Same pattern as Landing 1: landing edge = last tread edge
            # For west direction, landing east edge = last tread east edge
            # Last Run 3 tread east edge = run3_start_x_in - ((run3_tread_count - 1) * tread_spacing_in)
            last_run3_tread_east_in = run3_start_x_in - ((run3_tread_count - 1) * tread_spacing_in)
            landing3_x_east_in = last_run3_tread_east_in
            landing3_x_west_in = landing3_x_east_in - landing3_size_in

            if landing3_turn == "left":
                # 90 degrees left turn: west -> south
                # Landing Y aligns with Run 3 treads south edge
                landing3_y_south_in = run3_start_y_in - landing_tread_offset_in
            else:
                # 180 degrees switchback: west -> east
                # Landing extends south to make room for Run 4
                landing3_y_south_in = run3_start_y_in - landing_tread_offset_in - tread_length_in

            # Convert to center coordinates for create_landing_frame()
            landing3_x_center_in = landing3_x_west_in + landing3_size_in / 2.0
            landing3_y_center_in = landing3_y_south_in + landing3_size_in / 2.0

            # Create landing frame (posts + rim joists + deck boards)
            landing3_frame = create_landing_frame(
                doc=doc,
                catalog_rows=rows,
                landing_x_center_in=landing3_x_center_in,
                landing_y_center_in=landing3_y_center_in,
                landing_size_in=landing3_size_in,
                landing_z_top_in=landing3_z_top_in,
                slab_z_in=slab_top_z_in,
                landing_idx=3,
                post_label="post_4x4x96_PT",
                rim_label="2x12x96_PT",
                deck_board_label="deckboard_5_4x6x96_PT",
                supplier="lowes",
            )
            if landing3_frame:
                created.append(landing3_frame["group"])

            # ===== RUN 4 =====
            # Calculate landing4 Z for stringer bottom cut
            landing4_z_top_in = landing3_z_top_in - ((run4_tread_count + 1) * actual_rise_in)

            if run4_direction == "south":
                # Run 4: Descending SOUTH (after 90 degrees left from west)
                # Use create_stair_run helper function
                run4_start_x_in = landing3_x_west_in + landing_tread_offset_in
                run4_start_y_in = landing3_y_south_in

                run4_result = create_stair_run(
                    doc=doc,
                    catalog_rows=rows,
                    run_idx=4,
                    direction="south",
                    tread_count=run4_tread_count,
                    start_x_in=run4_start_x_in,
                    start_y_in=run4_start_y_in,
                    top_z_in=landing3_z_top_in
                    - actual_rise_in,  # First Run 4 tread is one rise below landing 3
                    landing_z_in=landing4_z_top_in,
                    tread_depth_in=tread_depth_in,
                    tread_length_in=tread_length_in,
                    tread_thick_in=tread_thick_in,
                    rise_per_step_in=actual_rise_in,
                    tread_label=tread_label,
                    stringer_label="2x12x96_PT",
                    header_label="2x12x96_PT",  # Header for Run 4
                    supplier="lowes",
                    tread_overhang_in=tread_overhang_in,
                )
                created.extend(run4_result["treads"])
                if run4_result["header"]:
                    created.append(run4_result["header"])
                created.extend(run4_result["stringers"])

                # Track last Run 4 position for Landing 4 (same pattern as Landing 1)
                # Last Run 4 tread north edge = run4_start_y_in - ((run4_tread_count - 1) * tread_spacing_in)
                last_run4_tread_north_in = run4_start_y_in - (
                    (run4_tread_count - 1) * tread_spacing_in
                )

            elif run4_direction == "east":
                # Run 4: Descending EAST (after 180 degrees switchback)
                # Use create_stair_run helper function
                run4_start_x_in = landing3_x_east_in
                run4_start_y_in = landing3_y_south_in + landing_tread_offset_in

                run4_result = create_stair_run(
                    doc=doc,
                    catalog_rows=rows,
                    run_idx=4,
                    direction="east",
                    tread_count=run4_tread_count,
                    start_x_in=run4_start_x_in,
                    start_y_in=run4_start_y_in,
                    top_z_in=landing3_z_top_in
                    - actual_rise_in,  # First Run 4 tread is one rise below landing 3
                    landing_z_in=landing4_z_top_in,
                    tread_depth_in=tread_depth_in,
                    tread_length_in=tread_length_in,
                    tread_thick_in=tread_thick_in,
                    rise_per_step_in=actual_rise_in,
                    tread_label=tread_label,
                    stringer_label="2x12x96_PT",
                    header_label="2x12x96_PT",  # Header for Run 4
                    supplier="lowes",
                    tread_overhang_in=tread_overhang_in,
                )
                created.extend(run4_result["treads"])
                if run4_result["header"]:
                    created.append(run4_result["header"])
                created.extend(run4_result["stringers"])

                # Track last Run 4 position for Landing 4 (not used for east direction in current config)
                last_run4_tread_north_in = run4_start_y_in

            # ===== LANDING 4 and RUN 5 (5-run stair) =====
            if has_landing4:
                # Landing 4 position: at the south end of Run 4 (when Run 4 goes south)
                # Same pattern as Landing 1: landing edge = last tread edge
                # For south direction, landing north edge = last tread north edge
                landing4_x_west_in = run4_start_x_in - landing_tread_offset_in
                landing4_x_east_in = landing4_x_west_in + landing4_size_in
                landing4_y_north_in = last_run4_tread_north_in
                landing4_y_south_in = landing4_y_north_in - landing4_size_in

                # Convert to center coordinates for create_landing_frame()
                landing4_x_center_in = landing4_x_west_in + landing4_size_in / 2.0
                landing4_y_center_in = landing4_y_south_in + landing4_size_in / 2.0

                # Create landing frame (posts + rim joists + deck boards)
                landing4_frame = create_landing_frame(
                    doc=doc,
                    catalog_rows=rows,
                    landing_x_center_in=landing4_x_center_in,
                    landing_y_center_in=landing4_y_center_in,
                    landing_size_in=landing4_size_in,
                    landing_z_top_in=landing4_z_top_in,
                    slab_z_in=slab_top_z_in,
                    landing_idx=4,
                    post_label="post_4x4x96_PT",
                    rim_label="2x12x96_PT",
                    deck_board_label="deckboard_5_4x6x96_PT",
                    supplier="lowes",
                )
                if landing4_frame:
                    created.append(landing4_frame["group"])

                # ===== RUN 5: Descending EAST =====
                # Use create_stair_run helper function
                # Calculate landing5 Z for stringer bottom cut
                landing5_z_top_in = landing4_z_top_in - ((run5_tread_count + 1) * actual_rise_in)

                # Run 5 starts at landing 4 east edge (header will be placed there)
                run5_start_x_in = landing4_x_east_in
                run5_start_y_in = landing4_y_south_in + landing_tread_offset_in

                run5_result = create_stair_run(
                    doc=doc,
                    catalog_rows=rows,
                    run_idx=5,
                    direction="east",
                    tread_count=run5_tread_count,
                    start_x_in=run5_start_x_in,
                    start_y_in=run5_start_y_in,
                    top_z_in=landing4_z_top_in
                    - actual_rise_in,  # First Run 5 tread is one rise below landing 4
                    landing_z_in=landing5_z_top_in,
                    tread_depth_in=tread_depth_in,
                    tread_length_in=tread_length_in,
                    tread_thick_in=tread_thick_in,
                    rise_per_step_in=actual_rise_in,
                    tread_label=tread_label,
                    stringer_label="2x12x96_PT",
                    header_label="2x12x96_PT",  # Header for Run 5
                    supplier="lowes",
                    tread_overhang_in=tread_overhang_in,
                )
                created.extend(run5_result["treads"])
                if run5_result["header"]:
                    created.append(run5_result["header"])
                created.extend(run5_result["stringers"])

                # Track last Run 5 position for Landing 5 (same pattern as Landing 1)
                # Last tread west edge = run5_start_x_in + (count-1) * spacing
                last_run5_tread_west_in = run5_start_x_in + (
                    (run5_tread_count - 1) * tread_spacing_in
                )

                # ===== LANDING 5 and RUN 6 (6-run stair) =====
                if has_landing5:
                    # Landing 5 position: at the east end of Run 5
                    # Same pattern as Landing 1: landing edge = last tread edge
                    # For east direction, landing west edge = last tread west edge
                    landing5_x_west_in = last_run5_tread_west_in
                    landing5_y_south_in = run5_start_y_in - landing_tread_offset_in
                    landing5_y_north_in = landing5_y_south_in + landing5_size_in

                    # Convert to center coordinates for create_landing_frame()
                    landing5_x_center_in = landing5_x_west_in + landing5_size_in / 2.0
                    landing5_y_center_in = landing5_y_south_in + landing5_size_in / 2.0

                    # Create landing frame (posts + rim joists + deck boards)
                    landing5_frame = create_landing_frame(
                        doc=doc,
                        catalog_rows=rows,
                        landing_x_center_in=landing5_x_center_in,
                        landing_y_center_in=landing5_y_center_in,
                        landing_size_in=landing5_size_in,
                        landing_z_top_in=landing5_z_top_in,
                        slab_z_in=slab_top_z_in,
                        landing_idx=5,
                        post_label="post_4x4x96_PT",
                        rim_label="2x12x96_PT",
                        deck_board_label="deckboard_5_4x6x96_PT",
                        supplier="lowes",
                    )
                    if landing5_frame:
                        created.append(landing5_frame["group"])

                    # ===== RUN 6: Descending NORTH to slab =====
                    # Use create_stair_run helper function
                    # Run 6 is the last run - stringers sit on concrete slab
                    run6_start_x_in = landing5_x_west_in + landing_tread_offset_in
                    run6_start_y_in = landing5_y_north_in

                    run6_result = create_stair_run(
                        doc=doc,
                        catalog_rows=rows,
                        run_idx=6,
                        direction="north",
                        tread_count=run6_tread_count,
                        start_x_in=run6_start_x_in,
                        start_y_in=run6_start_y_in,
                        top_z_in=landing5_z_top_in
                        - actual_rise_in,  # First Run 6 tread is one rise below landing 5
                        landing_z_in=slab_top_z_in,  # Bottom cut at slab level
                        tread_depth_in=tread_depth_in,
                        tread_length_in=tread_length_in,
                        tread_thick_in=tread_thick_in,
                        rise_per_step_in=actual_rise_in,
                        tread_label=tread_label,
                        stringer_label="2x12x144_PT",  # 12' for longer run
                        header_label="2x12x96_PT",  # Header for Run 6
                        supplier="lowes",
                        tread_overhang_in=tread_overhang_in,
                    )
                    created.extend(run6_result["treads"])
                    if run6_result["header"]:
                        created.append(run6_result["header"])
                    created.extend(run6_result["stringers"])

    else:
        # STRAIGHT STAIR: Original single-run behavior
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
                bc.ft(
                    x_ft
                ),  # West face at X position (aligned with stair rim east face = pile east face)
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

    # Electrical infrastructure (meter -> disconnect -> panel)
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
