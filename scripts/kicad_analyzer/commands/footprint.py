"""
Footprint analysis commands.

This module provides CLI commands for analyzing individual KiCad footprint files,
including size calculations, pad information, and detailed geometry analysis.
"""

from pathlib import Path
from typing import Optional
import json

import typer
from rich.console import Console

from ..core.analyzer import FootprintAnalyzer
from ..utils.validation import validate_footprint_file
from ..utils.formatting import (
    format_table, format_measurement, format_size,
    print_summary_panel, print_error, print_success
)


console = Console()
footprint_app = typer.Typer(help="Analyze KiCad footprint files (.kicad_mod)")


@footprint_app.command("info")
def footprint_info(
    footprint_file: Path = typer.Argument(
        ...,
        help="Path to .kicad_mod footprint file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed pad information"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output as JSON"
    ),
):
    """
    Display information about a footprint file.

    Shows bounding box dimensions, pad count, and other footprint properties.

    Example:
        kicad-analyzer footprint info parts/MyPart/footprint.kicad_mod
    """
    try:
        validate_footprint_file(footprint_file)
        analyzer = FootprintAnalyzer(footprint_file)
        summary = analyzer.get_summary()

        if json_output:
            console.print_json(data=summary)
            return

        # Print summary panel
        bbox = summary['bbox']
        summary_data = {
            'Footprint Name': summary['name'],
            'Library': summary.get('library', 'N/A'),
            'Bounding Box': format_size(bbox['width'], bbox['height']),
            'Area': format_measurement(bbox['area'], 'mm²'),
            'Pad Count': summary['pad_count'],
            'File': summary['file_path'],
        }
        print_summary_panel("Footprint Information", summary_data)

        # Print pad details if verbose
        if verbose and summary['pads']:
            rows = []
            for pad in summary['pads']:
                size = pad['size']
                pos = pad['position']
                rows.append([
                    pad['number'],
                    pad['type'],
                    pad['shape'],
                    f"{size[0]:.2f}×{size[1]:.2f}",
                    f"({pos[0]:+.2f}, {pos[1]:+.2f})",
                    str(pad.get('drill', 'N/A')),
                ])

            table = format_table(
                "Pad Details",
                ["Number", "Type", "Shape", "Size (mm)", "Position", "Drill"],
                rows,
                show_lines=True
            )
            console.print(table)

        print_success("Analysis complete")

    except Exception as e:
        print_error(f"Failed to analyze footprint: {e}")
        raise typer.Exit(1)


@footprint_app.command("bbox")
def footprint_bbox(
    footprint_file: Path = typer.Argument(
        ...,
        help="Path to .kicad_mod footprint file",
        exists=True,
    ),
):
    """
    Calculate and display the bounding box of a footprint.

    Shows the minimum and maximum X/Y coordinates and overall dimensions.

    Example:
        kicad-analyzer footprint bbox parts/MyPart/footprint.kicad_mod
    """
    try:
        validate_footprint_file(footprint_file)
        analyzer = FootprintAnalyzer(footprint_file)
        bbox = analyzer.get_bbox()

        data = {
            'Min X': format_measurement(bbox.min_x),
            'Max X': format_measurement(bbox.max_x),
            'Min Y': format_measurement(bbox.min_y),
            'Max Y': format_measurement(bbox.max_y),
            'Width': format_measurement(bbox.width),
            'Height': format_measurement(bbox.height),
            'Area': format_measurement(bbox.area, 'mm²'),
            'Center': f"({bbox.center.x:.3f}, {bbox.center.y:.3f})",
        }

        print_summary_panel(f"Bounding Box - {footprint_file.name}", data)
        print_success("Bounding box calculated")

    except Exception as e:
        print_error(f"Failed to calculate bounding box: {e}")
        raise typer.Exit(1)


@footprint_app.command("pads")
def footprint_pads(
    footprint_file: Path = typer.Argument(
        ...,
        help="Path to .kicad_mod footprint file",
        exists=True,
    ),
    filter_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by pad type (smd, thru_hole, np_thru_hole)"
    ),
):
    """
    List all pads in a footprint with detailed information.

    Example:
        kicad-analyzer footprint pads parts/MyPart/footprint.kicad_mod
        kicad-analyzer footprint pads parts/MyPart/footprint.kicad_mod --type smd
    """
    try:
        validate_footprint_file(footprint_file)
        analyzer = FootprintAnalyzer(footprint_file)
        pads = analyzer.get_pad_info()

        # Filter by type if specified
        if filter_type:
            pads = [p for p in pads if p['type'] == filter_type]

        if not pads:
            msg = "No pads found"
            if filter_type:
                msg += f" with type '{filter_type}'"
            print_error(msg)
            raise typer.Exit(1)

        # Create table
        rows = []
        for pad in pads:
            size = pad['size']
            pos = pad['position']
            layers = ', '.join(pad.get('layers', [])) if pad.get('layers') else 'N/A'

            rows.append([
                pad['number'],
                pad['type'],
                pad['shape'],
                f"{size[0]:.2f}×{size[1]:.2f}",
                f"({pos[0]:+.2f}, {pos[1]:+.2f})",
                layers[:30],  # Truncate long layer lists
            ])

        table = format_table(
            f"Pads - {footprint_file.name}",
            ["Number", "Type", "Shape", "Size (mm)", "Position", "Layers"],
            rows,
            show_lines=True
        )
        console.print(table)

        print_success(f"Found {len(pads)} pad(s)")

    except Exception as e:
        print_error(f"Failed to analyze pads: {e}")
        raise typer.Exit(1)
