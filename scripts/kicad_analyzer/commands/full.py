"""
Full analysis command implementation.

This module implements the 'full' subcommand which runs both
DRC and renders in a single analysis run.
"""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console

from ..config import load_config
from ..core.kicad_cli import KiCadCLI
from ..core.converters import ImageConverter
from ..utils.output import OutputManager
from .drc import parse_drc_json, display_drc_summary
from .render import render_2d_layers, render_3d_views


# Create Typer app for full analysis
full_app = typer.Typer(
    name="full",
    help="Run full PCB analysis (DRC + renders)",
)

console = Console()


@full_app.command("run")
def run_full_analysis(
    pcb: Optional[Path] = typer.Option(
        None,
        "--pcb",
        "-p",
        help="Path to PCB file (auto-detected if not specified)",
    ),
    width: int = typer.Option(
        3840,
        "--width",
        "-w",
        help="Image width in pixels (default: 3840 for 4K)",
    ),
    height: int = typer.Option(
        900,
        "--height",
        help="Image height for 3D renders",
    ),
    format: str = typer.Option(
        "png",
        "--format",
        "-f",
        help="Output format for 2D renders (png or svg)",
    ),
    no_3d: bool = typer.Option(
        False,
        "--no-3d",
        help="Skip 3D renders",
    ),
    no_drc: bool = typer.Option(
        False,
        "--no-drc",
        help="Skip DRC check",
    ),
    no_cleanup: bool = typer.Option(
        False,
        "--no-cleanup",
        help="Keep previous analysis folders",
    ),
    schematic_parity: bool = typer.Option(
        False,
        "--schematic-parity",
        "-s",
        help="Test for parity between PCB and schematic in DRC",
    ),
):
    """
    Run full PCB analysis (DRC + 2D/3D renders).

    Creates a complete analysis run with DRC report and render images
    in a single timestamped output folder.
    """
    try:
        config = load_config(pcb_file=pcb)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)

    # Create output directory with timestamp
    output_manager = OutputManager(config.project_root)
    output_manager.create_run_directory()

    # Cleanup old runs
    if not no_cleanup:
        removed = output_manager.cleanup_old_runs(
            config.project_root,
            keep_current=output_manager.current_run_dir,
        )
        if removed > 0:
            console.print(f"[dim]Cleaned up {removed} previous analysis folder(s)[/dim]")

    # Initialize KiCad CLI
    kicad = KiCadCLI(
        config.pcb_file,
        additional_cli_paths=list(config.kicad.additional_cli_paths),
    )
    converter = ImageConverter(list(config.kicad.additional_inkscape_paths))

    # Print header
    console.print()
    console.print("[bold]KiCad Analyzer - Full Analysis[/bold]")
    console.print("=" * 60)
    console.print(f"PCB File: [cyan]{config.pcb_file}[/cyan]")
    console.print(f"Output Directory: [cyan]{output_manager.current_run_dir}[/cyan]")
    console.print(f"KiCad CLI Available: [{'green' if kicad.is_available else 'red'}]{kicad.is_available}[/]")
    if kicad.cli_path:
        console.print(f"KiCad CLI Path: [dim]{kicad.cli_path}[/dim]")
    console.print("=" * 60)

    # Check prerequisites
    if not config.pcb_file.exists():
        console.print(f"\n[bold red]Error: PCB file not found:[/bold red] {config.pcb_file}")
        raise typer.Exit(1)

    if not kicad.is_available:
        console.print("\n[bold red]Error: KiCad CLI not found.[/bold red]")
        console.print("Please ensure KiCad 8.0+ is installed.")
        raise typer.Exit(1)

    drc_passed = True
    generated_files: List[Path] = []

    # Step 1: Run DRC
    if not no_drc:
        console.print("\n[bold cyan]Step 1: Design Rule Check (DRC)[/bold cyan]")
        console.print("-" * 40)

        drc_dir = output_manager.get_drc_dir()
        report_file = drc_dir / "drc_report.json"

        success, stdout, stderr = kicad.run_drc(
            report_file,
            format="json",
            schematic_parity=schematic_parity,
        )

        if report_file.exists():
            generated_files.append(report_file)
            console.print(f"[green]DRC report generated: {report_file}[/green]")

            try:
                drc_data = parse_drc_json(report_file)
                display_drc_summary(drc_data)

                violations = drc_data.get("violations", [])
                unconnected = drc_data.get("unconnected_items", [])
                error_count = sum(1 for v in violations if v.get("severity") == "error")

                if error_count > 0 or len(unconnected) > 0:
                    console.print("\n[bold red]DRC FAILED[/bold red] - Errors found")
                    drc_passed = False
                else:
                    console.print("\n[bold green]DRC PASSED[/bold green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not parse DRC report: {e}[/yellow]")
        else:
            console.print(f"[bold red]Error: DRC failed to generate report[/bold red]")
            if stderr:
                console.print(f"[red]{stderr}[/red]")
            drc_passed = False
    else:
        console.print("\n[dim]Skipping DRC (--no-drc)[/dim]")

    # Step 2: Generate renders
    render_cfg = config.render
    include_3d = not no_3d

    total_2d = len(render_cfg.layers_2d)
    total_3d = len(render_cfg.views_3d) if include_3d else 0

    console.print(f"\n[bold cyan]Step 2: PCB Renders ({total_2d} 2D + {total_3d} 3D)[/bold cyan]")
    console.print("-" * 40)

    renders_dir = output_manager.get_renders_dir()

    # Generate 2D renders
    render_2d_files = render_2d_layers(
        kicad,
        converter,
        renders_dir,
        render_cfg.layers_2d,
        width,
        format,
    )
    generated_files.extend(render_2d_files)

    # Generate 3D renders
    if include_3d:
        render_3d_files = render_3d_views(
            kicad,
            renders_dir,
            render_cfg.views_3d,
            width,
            height,
        )
        generated_files.extend(render_3d_files)

    # Create summary file
    output_manager.create_summary_file()

    # Print final summary
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]Analysis Summary[/bold cyan]")
    console.print("=" * 60)

    console.print(f"\nDRC Status: [{'green' if drc_passed else 'red'}]{'PASSED' if drc_passed else 'FAILED'}[/]")
    console.print(f"Files Generated: [bold]{len(generated_files)}[/bold]")
    console.print(f"\n[bold]Output Directory:[/bold] {output_manager.current_run_dir}")

    # List subdirectories
    console.print("\n[bold]Contents:[/bold]")
    for item in sorted(output_manager.current_run_dir.iterdir()):
        if item.is_dir():
            file_count = sum(1 for f in item.rglob("*") if f.is_file())
            console.print(f"  - {item.name}/ ({file_count} files)")
        elif item.is_file():
            size_kb = item.stat().st_size / 1024
            console.print(f"  - {item.name} ({size_kb:.1f} KB)")

    console.print()

    # Exit with error if DRC failed (but renders were still generated)
    if not drc_passed:
        console.print("[yellow]Note: Analysis completed but DRC has errors.[/yellow]")
        raise typer.Exit(1)
