"""
PCB analysis commands.

This module provides CLI commands for analyzing complete KiCad PCB files,
including component placement, collision detection, and board statistics.
"""

from pathlib import Path
from typing import Optional
import json

import typer
from rich.console import Console

from ..core.analyzer import PCBAnalyzer
from ..core.geometry import Point
from ..utils.validation import (
    validate_pcb_file, validate_clearance, validate_board_radius
)
from ..utils.formatting import (
    format_table, format_measurement, format_size, format_position,
    format_rotation, format_layer_name, format_percentage,
    print_summary_panel, print_error, print_success, print_warning,
    create_collision_table, create_fit_table, console
)


pcb_app = typer.Typer(help="Analyze KiCad PCB files (.kicad_pcb)")


@pcb_app.command("info")
def pcb_info(
    pcb_file: Path = typer.Argument(
        ...,
        help="Path to .kicad_pcb file",
        exists=True,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output as JSON"
    ),
):
    """
    Display comprehensive information about a PCB file.

    Shows PCB statistics, layer information, and component counts.

    Example:
        kicad-analyzer pcb info layouts/main/main.kicad_pcb
    """
    try:
        validate_pcb_file(pcb_file)
        analyzer = PCBAnalyzer(pcb_file)
        summary = analyzer.get_summary()

        if json_output:
            console.print_json(data=summary)
            return

        # Print main summary
        main_data = {
            'File': summary['file_path'],
            'PCB Thickness': format_measurement(summary['pcb_thickness']),
            'Layer Count': summary['layer_count'],
            'Footprint Count': summary['footprint_count'],
            'Total Pads': summary['total_pads'],
            'Total Component Area': format_measurement(summary['total_component_area'], 'mm²'),
            'Has Edge Cuts': 'Yes' if summary['has_edge_cuts'] else 'No',
        }

        if summary.get('board_bbox'):
            bbox = summary['board_bbox']
            main_data['Board Dimensions'] = format_size(bbox['width'], bbox['height'])

        print_summary_panel("PCB Information", main_data)

        # Print layer distribution
        if summary['layer_distribution']:
            rows = []
            for layer, count in sorted(summary['layer_distribution'].items()):
                rows.append([
                    format_layer_name(layer),
                    count,
                ])

            table = format_table(
                "Component Distribution by Layer",
                ["Layer", "Count"],
                rows
            )
            console.print(table)

        # Calculate and show density
        density = analyzer.calculate_density()
        if density > 0:
            console.print(f"\n[bold]Component Density:[/bold] {format_percentage(density)}")

        print_success("Analysis complete")

    except Exception as e:
        print_error(f"Failed to analyze PCB: {e}")
        raise typer.Exit(1)


@pcb_app.command("list")
def pcb_list_footprints(
    pcb_file: Path = typer.Argument(
        ...,
        help="Path to .kicad_pcb file",
        exists=True,
    ),
    layer: Optional[str] = typer.Option(
        None,
        "--layer",
        "-l",
        help="Filter by layer (e.g., F.Cu, B.Cu)"
    ),
    sort_by: str = typer.Option(
        "reference",
        "--sort",
        "-s",
        help="Sort by: reference, size, area, x, y"
    ),
):
    """
    List all footprints on the PCB with their properties.

    Example:
        kicad-analyzer pcb list layouts/main/main.kicad_pcb
        kicad-analyzer pcb list layouts/main/main.kicad_pcb --layer F.Cu
        kicad-analyzer pcb list layouts/main/main.kicad_pcb --sort area
    """
    try:
        validate_pcb_file(pcb_file)
        analyzer = PCBAnalyzer(pcb_file)
        stats = analyzer.get_footprint_stats()

        # Filter by layer if specified
        if layer:
            stats = [s for s in stats if s.layer == layer]

        if not stats:
            msg = "No footprints found"
            if layer:
                msg += f" on layer '{layer}'"
            print_error(msg)
            raise typer.Exit(1)

        # Sort
        sort_keys = {
            'reference': lambda s: s.reference,
            'size': lambda s: max(s.bbox_width, s.bbox_height),
            'area': lambda s: s.bbox_area,
            'x': lambda s: s.position.x,
            'y': lambda s: s.position.y,
        }

        if sort_by in sort_keys:
            stats.sort(key=sort_keys[sort_by])

        # Create table
        rows = []
        for stat in stats:
            rows.append([
                stat.reference,
                stat.footprint_name[:30],  # Truncate long names
                format_size(stat.bbox_width, stat.bbox_height),
                format_measurement(stat.bbox_area, 'mm²'),
                format_position(stat.position.x, stat.position.y),
                format_rotation(stat.rotation),
                format_layer_name(stat.layer),
            ])

        table = format_table(
            f"Footprints on PCB ({len(stats)} components)",
            ["Ref", "Footprint", "Size", "Area", "Position", "Rotation", "Layer"],
            rows,
            show_lines=False
        )
        console.print(table)

        print_success(f"Listed {len(stats)} footprint(s)")

    except Exception as e:
        print_error(f"Failed to list footprints: {e}")
        raise typer.Exit(1)


@pcb_app.command("collisions")
def pcb_check_collisions(
    pcb_file: Path = typer.Argument(
        ...,
        help="Path to .kicad_pcb file",
        exists=True,
    ),
    clearance: float = typer.Option(
        0.0,
        "--clearance",
        "-c",
        help="Required clearance between components in mm"
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Show all pairs checked, not just collisions"
    ),
):
    """
    Check for collisions between footprints on the PCB.

    Detects overlapping components and clearance violations.

    Example:
        kicad-analyzer pcb collisions layouts/main/main.kicad_pcb
        kicad-analyzer pcb collisions layouts/main/main.kicad_pcb --clearance 0.5
    """
    try:
        validate_pcb_file(pcb_file)
        validate_clearance(clearance)

        analyzer = PCBAnalyzer(pcb_file)
        collisions = analyzer.check_collisions(clearance)

        if not show_all:
            # Filter to only critical and warning
            collisions = [c for c in collisions if c.severity in ['critical', 'warning']]

        if not collisions:
            print_success("No collisions detected!")
            return

        # Create collision table
        table = create_collision_table(collisions)
        console.print(table)

        # Summary
        critical_count = sum(1 for c in collisions if c.severity == 'critical')
        warning_count = sum(1 for c in collisions if c.severity == 'warning')

        if critical_count > 0:
            print_error(f"Found {critical_count} critical collision(s)")
        if warning_count > 0:
            print_warning(f"Found {warning_count} clearance violation(s)")

        if critical_count > 0 or warning_count > 0:
            raise typer.Exit(1)

    except Exception as e:
        print_error(f"Failed to check collisions: {e}")
        raise typer.Exit(1)


@pcb_app.command("circular-fit")
def pcb_circular_fit(
    pcb_file: Path = typer.Argument(
        ...,
        help="Path to .kicad_pcb file",
        exists=True,
    ),
    radius: float = typer.Option(
        ...,
        "--radius",
        "-r",
        help="Board radius in mm"
    ),
    center_x: float = typer.Option(
        0.0,
        "--cx",
        help="Board center X coordinate in mm"
    ),
    center_y: float = typer.Option(
        0.0,
        "--cy",
        help="Board center Y coordinate in mm"
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Show all components, not just violations"
    ),
):
    """
    Check if all footprints fit within a circular board outline.

    Useful for circular PCB designs to validate component placement.

    Example:
        kicad-analyzer pcb circular-fit layouts/main/main.kicad_pcb --radius 9.3
        kicad-analyzer pcb circular-fit layouts/main/main.kicad_pcb -r 10 --cx 5 --cy 5
    """
    try:
        validate_pcb_file(pcb_file)
        validate_board_radius(radius)

        analyzer = PCBAnalyzer(pcb_file)
        center = Point(center_x, center_y)
        fit_reports = analyzer.check_circular_fit(radius, center)

        if not show_all:
            # Only show violations
            fit_reports = [r for r in fit_reports if not r.fits]

        if not fit_reports:
            if show_all:
                print_warning("No components found")
            else:
                print_success("All components fit within circular outline!")
            return

        # Create fit table
        table = create_fit_table(fit_reports, radius)
        console.print(table)

        # Summary
        violations = [r for r in fit_reports if not r.fits]
        if violations:
            print_error(f"Found {len(violations)} component(s) outside circular outline")
            raise typer.Exit(1)
        else:
            print_success("All components fit within circular outline!")

    except Exception as e:
        print_error(f"Failed to check circular fit: {e}")
        raise typer.Exit(1)


@pcb_app.command("layers")
def pcb_layers(
    pcb_file: Path = typer.Argument(
        ...,
        help="Path to .kicad_pcb file",
        exists=True,
    ),
):
    """
    List all layers defined in the PCB.

    Example:
        kicad-analyzer pcb layers layouts/main/main.kicad_pcb
    """
    try:
        validate_pcb_file(pcb_file)
        analyzer = PCBAnalyzer(pcb_file)
        summary = analyzer.get_summary()

        layers = summary['layers']
        layer_dist = summary['layer_distribution']

        if not layers:
            print_warning("No layers found in PCB")
            return

        rows = []
        for i, layer in enumerate(layers, 1):
            component_count = layer_dist.get(layer, 0)
            rows.append([
                i,
                layer,
                format_layer_name(layer),
                component_count if component_count > 0 else '-',
            ])

        table = format_table(
            f"PCB Layers ({len(layers)} total)",
            ["#", "Layer ID", "Name", "Components"],
            rows
        )
        console.print(table)

        print_success(f"Found {len(layers)} layer(s)")

    except Exception as e:
        print_error(f"Failed to list layers: {e}")
        raise typer.Exit(1)
