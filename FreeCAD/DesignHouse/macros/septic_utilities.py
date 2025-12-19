#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
septic_utilities.py - Septic system, utilities, and concrete slab for 950 Surf.

Underground Infrastructure:
  1. Septic tank (1000-1500 gallon, buried in northern back lot)
  2. Leach field (drain field with multiple trenches)
  3. Drain line (4" PVC from house to tank)
  4. Concrete slab (6" thick, driveway grade)
  5. Plumbing stub-ups (kitchen, bath, laundry)
  6. Electrical stub-ups (service entrance, sub-panel)

Design Notes:
  - Septic tank: 10' x 5' x 5' deep (typical 1500 gallon)
  - Leach field: 30' x 20' with 3 trenches @ 10' OC
  - Drain line: 4" diameter, 24" below grade (frost + code)
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
    Create drain line from house to septic tank (4" PVC with slope and radius bends).

    Design:
        - 4" Schedule 40 PVC (typical sewer drain)
        - Slope: 1/4" per foot (2% grade, typical for 4" drain per IPC 704.1)
        - 90-degree bends with 12" radius (typical for 4" PVC)
        - Path: Routes around piles to side of house, then to tank
        - Uses waypoint to avoid pile grid

    Args:
        doc: FreeCAD document
        config: SEPTIC_SYSTEM config dict
        start_x_ft: Starting X position (house rear stub-up)
        start_y_ft: Starting Y position (house rear stub-up)
        end_x_ft: Ending X position (septic tank inlet)
        end_y_ft: Ending Y position (septic tank inlet)

    Returns:
        Drain line Part::Feature object (compound of pipe segments and bends)
    """
    diameter_in = config["drain_line_diameter_in"]
    depth_start_in = config["drain_line_depth_in"]  # Start depth at house

    # Waypoint to route around piles
    waypoint_x_ft = config.get("drain_line_waypoint_x_ft", start_x_ft)
    waypoint_y_ft = config.get("drain_line_waypoint_y_ft", start_y_ft)

    # Calculate slope (1/4" per foot = 0.02083 ft/ft)
    slope_in_per_ft = 0.25

    # Calculate total horizontal run including waypoint routing
    run_1_ft = ((waypoint_x_ft - start_x_ft) ** 2 + (waypoint_y_ft - start_y_ft) ** 2) ** 0.5
    run_2_ft = ((end_x_ft - waypoint_x_ft) ** 2 + (end_y_ft - waypoint_y_ft) ** 2) ** 0.5
    total_run_ft = run_1_ft + run_2_ft

    depth_change_in = total_run_ft * slope_in_per_ft
    depth_end_in = depth_start_in + depth_change_in

    # PVC pipe parameters
    outer_radius_in = diameter_in / 2.0  # 2" for 4" PVC
    wall_thickness_in = 0.25  # Schedule 40 wall thickness  # noqa: F841 (for future hollow pipe)
    bend_radius_in = 12.0  # 12" radius for 90° bends  # noqa: F841 (for future torus bends)

    # Create path segments with slope
    # Segment 1: Vertical drop from stub-up (0" depth) to run depth (24")
    seg1_start = App.Vector(bc.ft(start_x_ft), bc.ft(start_y_ft), 0)
    seg1_end = App.Vector(bc.ft(start_x_ft), bc.ft(start_y_ft), bc.inch(-depth_start_in))

    # Segment 2: Horizontal run to waypoint (around piles)
    seg2_start = seg1_end
    depth_at_waypoint_in = depth_start_in + (run_1_ft * slope_in_per_ft)
    seg2_end = App.Vector(
        bc.ft(waypoint_x_ft), bc.ft(waypoint_y_ft), bc.inch(-depth_at_waypoint_in)
    )

    # Segment 3: Horizontal run from waypoint to tank
    seg3_start = seg2_end
    seg3_end = App.Vector(bc.ft(end_x_ft), bc.ft(end_y_ft), bc.inch(-depth_end_in))

    # Create pipe segments as cylinders
    segments = []

    # Segment 1: Vertical drop (cylinder along Z axis)
    seg1_length_mm = abs(seg1_end.z - seg1_start.z)
    if seg1_length_mm > 0.1:  # Only create if non-zero length
        seg1_pipe = Part.makeCylinder(
            bc.inch(outer_radius_in),
            seg1_length_mm,
            seg1_start,
            App.Vector(0, 0, -1),  # Direction: downward
        )
        segments.append(seg1_pipe)

    # Segment 2: Sloped horizontal run to waypoint
    seg2_vec = seg2_end - seg2_start
    seg2_length_mm = seg2_vec.Length
    if seg2_length_mm > 0.1:  # Only create if non-zero length
        seg2_direction = seg2_vec.normalize()
        seg2_pipe = Part.makeCylinder(
            bc.inch(outer_radius_in), seg2_length_mm, seg2_start, seg2_direction
        )
        segments.append(seg2_pipe)

    # Segment 3: Sloped horizontal run from waypoint to tank
    seg3_vec = seg3_end - seg3_start
    seg3_length_mm = seg3_vec.Length
    if seg3_length_mm > 0.1:  # Only create if non-zero length
        seg3_direction = seg3_vec.normalize()
        seg3_pipe = Part.makeCylinder(
            bc.inch(outer_radius_in), seg3_length_mm, seg3_start, seg3_direction
        )
        segments.append(seg3_pipe)

    # Create bends at junctions (elbow fittings)
    # Bend 1: vertical to horizontal at stub-up
    if len(segments) >= 1:
        bend1 = Part.makeSphere(bc.inch(outer_radius_in * 1.5), seg1_end)
        segments.append(bend1)

    # Bend 2: waypoint turn
    if len(segments) >= 3:
        bend2 = Part.makeSphere(bc.inch(outer_radius_in * 1.5), seg2_end)
        segments.append(bend2)

    # Combine all segments into compound shape
    drain_line = doc.addObject("Part::Feature", "Drain_Line_4in_PVC")
    if segments:
        drain_line.Shape = Part.Compound(segments)
    else:
        # Fallback: simple line if segments failed
        drain_line.Shape = Part.makeLine(seg1_start, seg3_end)

    return drain_line


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

                # Create cutout box for pile (slightly larger for clearance)
                cutout_size_in = pile_size_in + 0.5  # 0.5" clearance
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


def create_water_service_line(doc, config):
    """
    Create water supply line from street to house (1" PVC).

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict

    Returns:
        Water service line Part::Feature object
    """
    diameter_in = config["water_service_line_diameter_in"]  # noqa: F841 (for future pipe modeling)
    depth_in = config["water_service_depth_in"]
    stub_x_ft = config["water_stub_x_ft"]
    stub_y_ft = config["water_stub_y_ft"]
    street_y_ft = config["water_entry_from_street_y_ft"]

    # Create line from street to house
    start_pt = App.Vector(bc.ft(stub_x_ft), bc.ft(street_y_ft), bc.inch(-depth_in))
    end_pt = App.Vector(bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(-depth_in))

    water_line = doc.addObject("Part::Feature", "Water_Service_Line_1in")
    water_line.Shape = Part.makeLine(start_pt, end_pt)

    return water_line


def create_electrical_service_line(doc, config):
    """
    Create electrical service conduit from street to house (2" conduit).

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict

    Returns:
        Electrical service line Part::Feature object
    """
    diameter_in = config["electrical_service_conduit_diameter_in"]  # noqa: F841
    depth_in = config["electrical_service_depth_in"]
    stub_x_ft = config["electrical_stub_x_ft"]
    stub_y_ft = config["electrical_stub_y_ft"]
    street_y_ft = config["electrical_entry_from_street_y_ft"]

    # Create line from street to house
    start_pt = App.Vector(bc.ft(stub_x_ft), bc.ft(street_y_ft), bc.inch(-depth_in))
    end_pt = App.Vector(bc.ft(stub_x_ft), bc.ft(stub_y_ft), bc.inch(-depth_in))

    electrical_line = doc.addObject("Part::Feature", "Electrical_Service_Conduit_2in")
    electrical_line.Shape = Part.makeLine(start_pt, end_pt)

    return electrical_line


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
    Create electrical service stub-up (2" conduit, extend 12" above slab).

    Args:
        doc: FreeCAD document
        config: UTILITIES config dict

    Returns:
        Electrical stub-up Part::Feature object
    """
    diameter_in = config["electrical_service_conduit_diameter_in"]
    x_ft = config["electrical_stub_x_ft"]
    y_ft = config["electrical_stub_y_ft"]
    slab_thickness_in = config["slab_thickness_in"]
    stub_height_in = 12.0  # Extend 12" above slab

    stub = doc.addObject("Part::Feature", "Electrical_Stub_Up_2in")
    radius_mm = bc.inch(diameter_in / 2.0)
    height_mm = bc.inch(slab_thickness_in + stub_height_in)

    stub.Shape = Part.makeCylinder(radius_mm, height_mm)
    stub.Placement.Base = App.Vector(
        bc.ft(x_ft), bc.ft(y_ft), bc.inch(-slab_thickness_in)  # Start at bottom of slab
    )

    return stub


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

    drain_line = create_drain_line(
        doc,
        septic_config,
        start_x_ft=stub_x_ft,
        start_y_ft=stub_y_ft,
        end_x_ft=tank_x_ft,
        end_y_ft=tank_y_ft,
    )
    created.append(drain_line)

    # Group all septic objects
    septic_grp = bc.create_group(doc, "Septic_System")
    bc.add_to_group(septic_grp, created)

    App.Console.PrintMessage(
        f"[septic_utilities] Created septic system: "
        f"1 tank, {len(trenches)} leach trenches, 1 drain line\n"
    )

    return septic_grp


def create_utilities_slab(doc, utilities_config, pile_positions_ft=None, pile_size_in=12.0):
    """
    Create utilities (concrete slab + stub-ups + service lines).

    Args:
        doc: FreeCAD document
        utilities_config: UTILITIES config dict
        pile_positions_ft: List of (x_ft, y_ft) tuples for pile centers
        pile_size_in: Pile cross-section size (default 12")

    Returns:
        Group containing slab, stub-ups, and service lines
    """
    App.Console.PrintMessage("[septic_utilities] Creating utilities and concrete slab...\n")

    created = []

    # Concrete slab (with pile cutouts)
    slab = create_concrete_slab(doc, utilities_config, pile_positions_ft, pile_size_in)
    created.append(slab)

    # Water service line from street
    water_line = create_water_service_line(doc, utilities_config)
    created.append(water_line)

    # Water stub-up
    water_stub = create_water_stub_up(doc, utilities_config)
    created.append(water_stub)

    # Electrical service line from street
    electrical_line = create_electrical_service_line(doc, utilities_config)
    created.append(electrical_line)

    # Electrical stub-up
    electrical_stub = create_electrical_stub_up(doc, utilities_config)
    created.append(electrical_stub)

    # Plumbing drain/waste/vent stub-ups
    plumbing_stubs = create_plumbing_stub_ups(doc, utilities_config)
    created.extend(plumbing_stubs)

    # Group all utility objects
    utilities_grp = bc.create_group(doc, "Utilities_and_Slab")
    bc.add_to_group(utilities_grp, created)

    App.Console.PrintMessage(
        f"[septic_utilities] Created utilities: "
        f"1 slab (w/ pile cutouts), 1 water line, 1 electrical line, "
        f"{len(plumbing_stubs)} plumbing stubs\n"
    )

    return utilities_grp


if __name__ == "__main__":
    print("[septic_utilities] This module provides septic and utilities creation helpers.")
    print("[septic_utilities] Import into your macro: import septic_utilities as su")
