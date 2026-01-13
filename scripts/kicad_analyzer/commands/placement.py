"""
Placement commands for applying and validating component placements.

This module provides CLI commands for reading placement data from CSV files,
applying placements to KiCad PCB files, and validating placement constraints.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import csv
import shutil

import typer
from rich.console import Console

try:
    from kiutils.board import Board
except ImportError:
    raise ImportError("kiutils library required. Install with: pip install kiutils")

from ..core.analyzer import PCBAnalyzer
from ..core.geometry import Point, BoundingBox
from ..utils.validation import validate_pcb_file, validate_placement_csv
from ..utils.formatting import (
    format_table, format_position, format_rotation,
    print_summary_panel, print_error, print_success, print_warning, print_info
)


console = Console()
placement_app = typer.Typer(help="Apply and validate component placements")


def read_placement_csv(csv_path: Path) -> List[Dict[str, any]]:
    """
    Read placement data from CSV file.

    Args:
        csv_path: Path to CSV file with columns: Ref, X_mm, Y_mm, Rotation_deg, Side

    Returns:
        List of placement dictionaries
    """
    placements = []

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            placement = {
                'ref': row['Ref'],
                'x': float(row['X_mm']),
                'y': float(row['Y_mm']),
                'rotation': float(row['Rotation_deg']),
                'side': row['Side'],
            }
            placements.append(placement)

    return placements


@placement_app.command("validate")
def validate_placement(
    csv_file: Path = typer.Argument(
        ...,
        help="Path to placement CSV file",
        exists=True,
    ),
    circular: bool = typer.Option(
        False,
        "--circular",
        help="Validate for circular board"
    ),
    radius: float = typer.Option(
        None,
        "--radius",
        "-r",
        help="Board radius in mm (required with --circular)"
    ),
    clearance: float = typer.Option(
        0.0,
        "--clearance",
        "-c",
        help="Minimum clearance between components in mm"
    ),
):
    """
    Validate a placement CSV file without applying it.

    Checks format, required fields, and can validate geometric constraints.

    Example:
        kicad-analyzer placement validate planv7/placement_main_v1.csv
        kicad-analyzer placement validate placement.csv --circular --radius 9.3
    """
    try:
        validate_placement_csv(csv_file)
        placements = read_placement_csv(csv_file)

        print_success(f"CSV format valid: {len(placements)} placement(s) found")

        # Show summary
        refs = [p['ref'] for p in placements]
        sides = {}
        for p in placements:
            sides[p['side']] = sides.get(p['side'], 0) + 1

        summary_data = {
            'Total Components': len(placements),
            'Unique References': len(set(refs)),
            'Duplicates': len(refs) - len(set(refs)),
        }

        for side, count in sorted(sides.items()):
            summary_data[f'{side} Components'] = count

        print_summary_panel("Placement Summary", summary_data)

        # Check for circular fit if requested
        if circular:
            if radius is None:
                print_error("--radius required when using --circular")
                raise typer.Exit(1)

            center = Point(0, 0)
            violations = []

            for p in placements:
                point = Point(p['x'], p['y'])
                dist = point.distance_to(center)

                if dist > radius:
                    violations.append((p['ref'], dist, dist - radius))

            if violations:
                rows = []
                for ref, dist, excess in violations:
                    rows.append([
                        ref,
                        f"{dist:.3f}",
                        f"[red]{excess:.3f}[/red]",
                    ])

                table = format_table(
                    f"Circular Fit Violations (Radius={radius}mm)",
                    ["Reference", "Distance (mm)", "Excess (mm)"],
                    rows
                )
                console.print(table)

                print_error(f"{len(violations)} component(s) outside circular boundary")
                raise typer.Exit(1)
            else:
                print_success("All components within circular boundary")

        print_success("Validation complete")

    except Exception as e:
        print_error(f"Validation failed: {e}")
        raise typer.Exit(1)


@placement_app.command("apply")
def apply_placement(
    pcb_file: Path = typer.Argument(
        ...,
        help="Path to .kicad_pcb file",
        exists=True,
    ),
    csv_file: Path = typer.Argument(
        ...,
        help="Path to placement CSV file",
        exists=True,
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output PCB file (defaults to overwriting input)"
    ),
    backup: bool = typer.Option(
        True,
        "--backup/--no-backup",
        help="Create backup of original PCB file"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be changed without applying"
    ),
):
    """
    Apply placements from CSV to a KiCad PCB file.

    Updates component positions, rotations, and layers based on CSV data.

    Example:
        kicad-analyzer placement apply main.kicad_pcb placement.csv
        kicad-analyzer placement apply main.kicad_pcb placement.csv -o main_placed.kicad_pcb
        kicad-analyzer placement apply main.kicad_pcb placement.csv --dry-run
    """
    try:
        validate_pcb_file(pcb_file)
        validate_placement_csv(csv_file)

        placements = read_placement_csv(csv_file)
        placement_map = {p['ref']: p for p in placements}

        # Load PCB
        board = Board.from_file(str(pcb_file))

        # Track changes
        updated = []
        not_found = []
        unchanged = []

        for footprint in board.footprints:
            # Extract reference from properties (not entryName which is the footprint name)
            ref = None
            if hasattr(footprint, 'properties') and footprint.properties and isinstance(footprint.properties, dict):
                ref = footprint.properties.get('Reference')

            if ref and ref in placement_map:
                p = placement_map[ref]

                # Check if placement actually changes
                current_x = footprint.position.X
                current_y = footprint.position.Y
                current_rot = footprint.position.angle if hasattr(footprint.position, 'angle') else 0
                current_layer = footprint.layer if hasattr(footprint, 'layer') else 'F.Cu'

                changes = []

                if abs(current_x - p['x']) > 0.001 or abs(current_y - p['y']) > 0.001:
                    changes.append(f"pos: ({current_x:.2f},{current_y:.2f}) -> ({p['x']:.2f},{p['y']:.2f})")
                    footprint.position.X = p['x']
                    footprint.position.Y = p['y']

                if abs(current_rot - p['rotation']) > 0.1:
                    changes.append(f"rot: {current_rot:.1f} -> {p['rotation']:.1f}")
                    footprint.position.angle = p['rotation']

                if current_layer != p['side']:
                    changes.append(f"layer: {current_layer} -> {p['side']}")
                    footprint.layer = p['side']

                if changes:
                    updated.append((ref, changes))
                else:
                    unchanged.append(ref)

        # Check for placements without matching footprints
        pcb_refs = set()
        for fp in board.footprints:
            if hasattr(fp, 'properties') and fp.properties and isinstance(fp.properties, dict):
                fp_ref = fp.properties.get('Reference')
                if fp_ref:
                    pcb_refs.add(fp_ref)

        for ref in placement_map:
            if ref not in pcb_refs:
                not_found.append(ref)

        # Print summary
        summary_data = {
            'Placements in CSV': len(placements),
            'Footprints Updated': len(updated),
            'Unchanged': len(unchanged),
            'Not Found in PCB': len(not_found),
        }
        print_summary_panel("Placement Application Summary", summary_data)

        if updated and not dry_run:
            # Show updated components
            rows = []
            for ref, changes in updated[:20]:  # Show first 20
                rows.append([ref, '\n'.join(changes)])

            table = format_table(
                "Updated Components",
                ["Reference", "Changes"],
                rows,
                show_lines=True
            )
            console.print(table)

            if len(updated) > 20:
                print_info(f"... and {len(updated) - 20} more")

        if not_found:
            print_warning(f"References not found in PCB: {', '.join(not_found[:10])}")
            if len(not_found) > 10:
                print_info(f"... and {len(not_found) - 10} more")

        if dry_run:
            print_info("Dry run mode - no changes applied")
            return

        if not updated:
            print_info("No changes needed - all placements match")
            return

        # Determine output path
        output_path = output if output else pcb_file

        # Create backup if requested
        if backup and output_path == pcb_file:
            backup_path = pcb_file.with_suffix('.kicad_pcb.bak')
            shutil.copy2(pcb_file, backup_path)
            print_success(f"Backup created: {backup_path}")

        # Write updated PCB
        board.to_file(str(output_path))
        print_success(f"Placements applied to: {output_path}")

    except Exception as e:
        print_error(f"Failed to apply placements: {e}")
        raise typer.Exit(1)


@placement_app.command("export")
def export_placement(
    pcb_file: Path = typer.Argument(
        ...,
        help="Path to .kicad_pcb file",
        exists=True,
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output CSV file (defaults to <pcb_name>_placement.csv)"
    ),
    layer: str = typer.Option(
        None,
        "--layer",
        "-l",
        help="Export only components on specific layer"
    ),
):
    """
    Export current component placements from PCB to CSV.

    Creates a CSV file with current positions that can be modified and re-applied.

    Example:
        kicad-analyzer placement export main.kicad_pcb
        kicad-analyzer placement export main.kicad_pcb -o my_placement.csv
        kicad-analyzer placement export main.kicad_pcb --layer F.Cu
    """
    try:
        validate_pcb_file(pcb_file)

        analyzer = PCBAnalyzer(pcb_file)
        footprints = analyzer.parsed_pcb.footprints

        # Filter by layer if specified
        if layer:
            footprints = [fp for fp in footprints if fp.layer == layer]

        if not footprints:
            print_error(f"No footprints found" + (f" on layer {layer}" if layer else ""))
            raise typer.Exit(1)

        # Determine output path
        if output is None:
            output = pcb_file.with_name(f"{pcb_file.stem}_placement.csv")

        # Write CSV
        with open(output, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Ref', 'X_mm', 'Y_mm', 'Rotation_deg', 'Side'])
            writer.writeheader()

            for fp in footprints:
                writer.writerow({
                    'Ref': fp.reference,
                    'X_mm': f"{fp.position.x:.4f}",
                    'Y_mm': f"{fp.position.y:.4f}",
                    'Rotation_deg': f"{fp.rotation:.2f}",
                    'Side': fp.layer,
                })

        print_success(f"Exported {len(footprints)} placement(s) to: {output}")

    except Exception as e:
        print_error(f"Failed to export placements: {e}")
        raise typer.Exit(1)
