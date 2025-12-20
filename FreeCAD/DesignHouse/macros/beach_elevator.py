#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Beach House Elevator Module

Simple open metal beach house elevator/lift. Typical beach house elevators are
open metal platforms with corner posts, hydraulic or cable-driven, not enclosed
(to save cost and match beach aesthetic).

BOM Handling:
    Elevator is tracked as a single purchased assembly (not individual catalog parts).
    The Beach_Elevator group has BOM metadata attached:
        - label: beach_elevator_4x5_20ft (platform size and travel)
        - qty: 1.0
        - supplier: garaventa_lift (or similar manufacturer)
        - sku: VPL-48x60-20 (Vertical Platform Lift spec)
        - url: Product page

    This ensures the elevator appears as ONE line item in BOM exports, rather than
    breaking down into individual steel posts/beams/cylinders which aren't catalog parts.

For Luke Dombrowski. Stay Alive.
"""

import FreeCAD as App
import Part
import beach_common as bc


def _set_color(obj, color):
    """Safely set object color (guards against headless mode where ViewObject may not exist)."""
    if hasattr(obj, "ViewObject") and obj.ViewObject:
        obj.ViewObject.ShapeColor = color


def create_beach_elevator(doc, config, foundation_config=None):
    """
    Create a simple open metal beach house elevator/lift.

    Args:
        doc: FreeCAD document
        config: Elevator configuration dict with keys:
            - elevator_x_ft: X position (east-west)
            - elevator_y_ft: Y position (north-south)
            - platform_width_ft: Platform width (default 4.0 for wheelchair access)
            - platform_depth_ft: Platform depth (default 5.0)
            - travel_height_ft: Full travel from ground to deck (default 20.0)
        foundation_config: Foundation config (for deck height reference)

    Returns:
        Group containing all elevator parts
    """
    # Configuration
    elevator_x_ft = config.get("elevator_x_ft", 42.0)  # East side, south of deck
    elevator_y_ft = config.get("elevator_y_ft", 18.0)  # Just south of front deck
    platform_width_ft = config.get("platform_width_ft", 4.0)  # 4' wide (ADA min 42", use 48")
    platform_depth_ft = config.get("platform_depth_ft", 5.0)  # 5' deep
    travel_height_ft = config.get("travel_height_ft", 20.0)  # Match deck height

    # Get deck height from foundation config if available
    if foundation_config:
        travel_height_ft = foundation_config.get("above_grade_ft", 20.0)

    # Steel colors
    steel_color = (0.7, 0.7, 0.7)  # Galvanized steel gray
    platform_color = (0.6, 0.6, 0.6)  # Darker gray for platform deck

    created = []

    # ====================
    # CORNER POSTS (4 vertical steel tubes, 4" square)
    # ====================
    post_size_in = 4.0  # 4x4 steel tube
    post_height_ft = travel_height_ft + 2.0  # Extend 2' above deck for overhead support

    # Corner positions (centered on elevator_x, elevator_y)
    corners = [
        (elevator_x_ft - platform_width_ft / 2.0, elevator_y_ft - platform_depth_ft / 2.0),  # SW
        (elevator_x_ft + platform_width_ft / 2.0, elevator_y_ft - platform_depth_ft / 2.0),  # SE
        (elevator_x_ft - platform_width_ft / 2.0, elevator_y_ft + platform_depth_ft / 2.0),  # NW
        (elevator_x_ft + platform_width_ft / 2.0, elevator_y_ft + platform_depth_ft / 2.0),  # NE
    ]

    for i, (corner_x, corner_y) in enumerate(corners):
        post = doc.addObject("Part::Box", f"Elevator_Post_{i+1}")
        post.Length = bc.inch(post_size_in)
        post.Width = bc.inch(post_size_in)
        post.Height = bc.ft(post_height_ft)
        post.Placement.Base = App.Vector(
            bc.ft(corner_x) - bc.inch(post_size_in / 2.0),
            bc.ft(corner_y) - bc.inch(post_size_in / 2.0),
            0.0,  # Start at grade
        )
        _set_color(post, steel_color)
        created.append(post)

    # ====================
    # PLATFORM (at ground level initially, moves up to deck)
    # ====================
    platform_thickness_in = 2.0  # 2" steel grating platform
    platform = doc.addObject("Part::Box", "Elevator_Platform")
    platform.Length = bc.ft(platform_width_ft)
    platform.Width = bc.ft(platform_depth_ft)
    platform.Height = bc.inch(platform_thickness_in)
    platform.Placement.Base = App.Vector(
        bc.ft(elevator_x_ft - platform_width_ft / 2.0),
        bc.ft(elevator_y_ft - platform_depth_ft / 2.0),
        bc.ft(travel_height_ft),  # Show at top position (deck level)
    )
    _set_color(platform, platform_color)
    created.append(platform)

    # ====================
    # SAFETY RAILINGS (3 sides - open on house side for access)
    # ====================
    railing_height_in = 42.0  # 42" handrail height (ADA)
    railing_tube_dia_in = 1.5  # 1.5" diameter steel tube

    # Railing top rail position: platform top + railing height
    platform_top_z = bc.ft(travel_height_ft) + bc.inch(platform_thickness_in)
    railing_z = platform_top_z + bc.inch(railing_height_in)

    # South railing (front, full width, runs east-west)
    south_railing = doc.addObject("Part::Feature", "Elevator_Railing_South")
    south_railing_shape = Part.makeCylinder(
        bc.inch(railing_tube_dia_in / 2.0), bc.ft(platform_width_ft)
    )
    south_railing_shape.Placement = App.Placement(
        App.Vector(
            bc.ft(elevator_x_ft - platform_width_ft / 2.0),  # Start at west edge
            bc.ft(elevator_y_ft - platform_depth_ft / 2.0),  # South edge of platform
            railing_z,  # Railing height above platform
        ),
        App.Rotation(App.Vector(0, 1, 0), 90),  # Rotate to run east-west
    )
    south_railing.Shape = south_railing_shape
    _set_color(south_railing, steel_color)
    created.append(south_railing)

    # East railing (right side, full depth, runs north-south)
    east_railing = doc.addObject("Part::Feature", "Elevator_Railing_East")
    east_railing_shape = Part.makeCylinder(
        bc.inch(railing_tube_dia_in / 2.0), bc.ft(platform_depth_ft)
    )
    east_railing_shape.Placement = App.Placement(
        App.Vector(
            bc.ft(elevator_x_ft + platform_width_ft / 2.0),  # East edge of platform
            bc.ft(elevator_y_ft - platform_depth_ft / 2.0),  # Start at south edge
            railing_z,  # Railing height above platform
        ),
        App.Rotation(App.Vector(1, 0, 0), 90),  # Rotate to run north-south
    )
    east_railing.Shape = east_railing_shape
    _set_color(east_railing, steel_color)
    created.append(east_railing)

    # West railing (left side, full depth, runs north-south)
    west_railing = doc.addObject("Part::Feature", "Elevator_Railing_West")
    west_railing_shape = Part.makeCylinder(
        bc.inch(railing_tube_dia_in / 2.0), bc.ft(platform_depth_ft)
    )
    west_railing_shape.Placement = App.Placement(
        App.Vector(
            bc.ft(elevator_x_ft - platform_width_ft / 2.0),  # West edge of platform
            bc.ft(elevator_y_ft - platform_depth_ft / 2.0),  # Start at south edge
            railing_z,  # Railing height above platform
        ),
        App.Rotation(App.Vector(1, 0, 0), 90),  # Rotate to run north-south
    )
    west_railing.Shape = west_railing_shape
    _set_color(west_railing, steel_color)
    created.append(west_railing)

    # North side (house side) - NO RAILING for deck access

    # ====================
    # HYDRAULIC CYLINDER (central cylinder for lift mechanism)
    # ====================
    cylinder_dia_in = 6.0  # 6" hydraulic cylinder
    cylinder_height_ft = travel_height_ft - 1.0  # Slightly shorter than travel (retracted state)

    hydraulic_cylinder = doc.addObject("Part::Feature", "Elevator_Hydraulic_Cylinder")
    hydraulic_cylinder_shape = Part.makeCylinder(
        bc.inch(cylinder_dia_in / 2.0), bc.ft(cylinder_height_ft)
    )
    hydraulic_cylinder_shape.Placement.Base = App.Vector(
        bc.ft(elevator_x_ft) - bc.inch(cylinder_dia_in / 2.0),
        bc.ft(elevator_y_ft) - bc.inch(cylinder_dia_in / 2.0),
        0.0,  # Start at grade
    )
    hydraulic_cylinder.Shape = hydraulic_cylinder_shape
    _set_color(hydraulic_cylinder, (0.3, 0.3, 0.3))  # Dark gray for cylinder
    created.append(hydraulic_cylinder)

    # ====================
    # OVERHEAD BEAM (connects top of posts for structural support)
    # ====================
    beam_size_in = 6.0  # 6" I-beam (simplified as box)

    # South beam (connects SW and SE posts)
    south_beam = doc.addObject("Part::Box", "Elevator_Beam_South")
    south_beam.Length = bc.ft(platform_width_ft)
    south_beam.Width = bc.inch(beam_size_in)
    south_beam.Height = bc.inch(beam_size_in)
    south_beam.Placement.Base = App.Vector(
        bc.ft(elevator_x_ft - platform_width_ft / 2.0),
        bc.ft(elevator_y_ft - platform_depth_ft / 2.0) - bc.inch(beam_size_in / 2.0),
        bc.ft(post_height_ft) - bc.inch(beam_size_in),
    )
    _set_color(south_beam, steel_color)
    created.append(south_beam)

    # North beam (connects NW and NE posts)
    north_beam = doc.addObject("Part::Box", "Elevator_Beam_North")
    north_beam.Length = bc.ft(platform_width_ft)
    north_beam.Width = bc.inch(beam_size_in)
    north_beam.Height = bc.inch(beam_size_in)
    north_beam.Placement.Base = App.Vector(
        bc.ft(elevator_x_ft - platform_width_ft / 2.0),
        bc.ft(elevator_y_ft + platform_depth_ft / 2.0) - bc.inch(beam_size_in / 2.0),
        bc.ft(post_height_ft) - bc.inch(beam_size_in),
    )
    _set_color(north_beam, steel_color)
    created.append(north_beam)

    # Create group and add all parts
    elevator_grp = bc.create_group(doc, "Beach_Elevator")
    bc.add_to_group(elevator_grp, created)

    # Add BOM metadata to group (elevator is purchased as complete assembly, not built from catalog parts)
    # This ensures it appears as one line item in BOM instead of individual metal pieces
    elevator_grp.addProperty("App::PropertyString", "label", "BOM", "Item label for BOM")
    elevator_grp.addProperty("App::PropertyFloat", "qty", "BOM", "Quantity")
    elevator_grp.addProperty("App::PropertyString", "supplier", "BOM", "Supplier name")
    elevator_grp.addProperty("App::PropertyString", "sku", "BOM", "SKU or part number")
    elevator_grp.addProperty("App::PropertyString", "url", "BOM", "Product URL")

    elevator_grp.label = f"beach_elevator_{int(platform_width_ft)}x{int(platform_depth_ft)}_{int(travel_height_ft)}ft"
    elevator_grp.qty = 1.0
    elevator_grp.supplier = (
        "garaventa_lift"  # Example: Garaventa Lift or similar beach elevator manufacturer
    )
    elevator_grp.sku = f"VPL-{int(platform_width_ft*12)}x{int(platform_depth_ft*12)}-{int(travel_height_ft)}"  # Vertical Platform Lift
    elevator_grp.url = "https://www.garaventalift.com/us/platform-lifts"  # Example vendor

    App.Console.PrintMessage(
        f"[beach_elevator] Created beach elevator: "
        f"{platform_width_ft:.1f}' × {platform_depth_ft:.1f}' platform, "
        f"{travel_height_ft:.1f}' travel height, "
        f"position X={elevator_x_ft:.1f}', Y={elevator_y_ft:.1f}'\n"
    )

    return elevator_grp


if __name__ == "__main__":
    print("[beach_elevator] This module provides beach house elevator creation.")
    print("[beach_elevator] Import into your macro: import beach_elevator as be")
