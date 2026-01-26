"""
DRC (Design Rule Check) command implementation.

This module implements the 'drc' subcommand which runs KiCad's
Design Rule Check and generates reports.
"""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..config import load_config
from ..core.kicad_cli import KiCadCLI
from ..utils.output import OutputManager


# Create Typer app for DRC commands
drc_app = typer.Typer(
    name="drc",
    help="Run Design Rule Check (DRC) on PCB files",
)

console = Console()


def parse_drc_json(json_path: Path) -> dict:
    """
    Parse DRC JSON report file.

    Args:
        json_path: Path to the JSON report file.

    Returns:
        Parsed DRC data dictionary.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def display_drc_summary(drc_data: dict) -> None:
    """
    Display a summary of DRC results.

    Args:
        drc_data: Parsed DRC JSON data.
    """
    # Extract violation counts
    violations = drc_data.get("violations", [])
    unconnected = drc_data.get("unconnected_items", [])
    schematic_parity = drc_data.get("schematic_parity", [])

    error_count = sum(1 for v in violations if v.get("severity") == "error")
    warning_count = sum(1 for v in violations if v.get("severity") == "warning")
    unconnected_count = len(unconnected)
    parity_count = len(schematic_parity)

    # Create summary table
    table = Table(title="DRC Summary", show_header=True, header_style="bold cyan")
    table.add_column("Category", style="dim")
    table.add_column("Count", justify="right")
    table.add_column("Status")

    # Add rows
    if error_count > 0:
        table.add_row("Errors", str(error_count), "[bold red]FAIL[/bold red]")
    else:
        table.add_row("Errors", str(error_count), "[green]PASS[/green]")

    if warning_count > 0:
        table.add_row("Warnings", str(warning_count), "[yellow]WARNING[/yellow]")
    else:
        table.add_row("Warnings", str(warning_count), "[green]PASS[/green]")

    if unconnected_count > 0:
        table.add_row("Unconnected Items", str(unconnected_count), "[bold red]FAIL[/bold red]")
    else:
        table.add_row("Unconnected Items", str(unconnected_count), "[green]PASS[/green]")

    if parity_count > 0:
        table.add_row("Schematic Parity", str(parity_count), "[yellow]WARNING[/yellow]")
    else:
        table.add_row("Schematic Parity", str(parity_count), "[dim]-[/dim]")

    console.print()
    console.print(table)

    # Display detailed violations if any
    if violations:
        console.print("\n[bold cyan]Violations:[/bold cyan]")
        for idx, v in enumerate(violations[:20], 1):  # Limit to first 20
            severity = v.get("severity", "unknown")
            type_name = v.get("type", "unknown")
            description = v.get("description", "No description")

            if severity == "error":
                severity_style = "[bold red]ERROR[/bold red]"
            elif severity == "warning":
                severity_style = "[yellow]WARNING[/yellow]"
            else:
                severity_style = f"[dim]{severity}[/dim]"

            console.print(f"  {idx}. {severity_style} [{type_name}]: {description}")

        if len(violations) > 20:
            console.print(f"\n  [dim]... and {len(violations) - 20} more violations[/dim]")

    # Display unconnected items if any
    if unconnected:
        console.print("\n[bold cyan]Unconnected Items:[/bold cyan]")
        for idx, item in enumerate(unconnected[:10], 1):  # Limit to first 10
            description = item.get("description", "Unknown")
            console.print(f"  {idx}. {description}")

        if len(unconnected) > 10:
            console.print(f"\n  [dim]... and {len(unconnected) - 10} more unconnected items[/dim]")


@drc_app.command("run")
def run_drc(
    pcb: Optional[Path] = typer.Option(
        None,
        "--pcb",
        "-p",
        help="Path to PCB file (auto-detected if not specified)",
    ),
    run_dir: Optional[Path] = typer.Option(
        None,
        "--run-dir",
        "-r",
        help="Use existing run directory instead of creating new one",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Report format: json or report (text)",
    ),
    schematic_parity: bool = typer.Option(
        False,
        "--schematic-parity",
        "-s",
        help="Test for parity between PCB and schematic",
    ),
    no_cleanup: bool = typer.Option(
        False,
        "--no-cleanup",
        help="Keep previous analysis folders",
    ),
):
    """
    Run Design Rule Check on the PCB.

    Generates a DRC report with violations, warnings, and unconnected items.
    """
    try:
        config = load_config(pcb_file=pcb)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)

    # Create or use existing output directory
    output_manager = OutputManager(config.project_root)
    if run_dir and run_dir.exists():
        output_manager.current_run_dir = run_dir
    else:
        output_manager.create_run_directory()

        # Cleanup old runs
        if not no_cleanup:
            removed = output_manager.cleanup_old_runs(
                config.project_root,
                keep_current=output_manager.current_run_dir,
            )
            if removed > 0:
                console.print(f"[dim]Cleaned up {removed} previous analysis folder(s)[/dim]")

    # Get DRC directory
    drc_dir = output_manager.get_drc_dir()

    # Determine output file
    extension = "json" if format == "json" else "rpt"
    report_file = drc_dir / f"drc_report.{extension}"

    # Initialize KiCad CLI
    kicad = KiCadCLI(
        config.pcb_file,
        additional_cli_paths=list(config.kicad.additional_cli_paths),
    )

    # Print header
    console.print()
    console.print("[bold]KiCad Analyzer - DRC Command[/bold]")
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

    # Run DRC
    console.print("\n[bold cyan]Running Design Rule Check...[/bold cyan]")

    success, stdout, stderr = kicad.run_drc(
        report_file,
        format=format,
        schematic_parity=schematic_parity,
    )

    # DRC returns non-zero if there are violations (when exit_code_violations=True)
    # So we check if the report file was created instead
    if not report_file.exists():
        console.print(f"\n[bold red]Error: DRC failed to generate report[/bold red]")
        if stderr:
            console.print(f"[red]{stderr}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]DRC report generated: {report_file}[/green]")

    # Parse and display results for JSON format
    if format == "json":
        try:
            drc_data = parse_drc_json(report_file)
            display_drc_summary(drc_data)

            # Determine overall status
            violations = drc_data.get("violations", [])
            unconnected = drc_data.get("unconnected_items", [])
            error_count = sum(1 for v in violations if v.get("severity") == "error")

            if error_count > 0 or len(unconnected) > 0:
                console.print("\n[bold red]DRC FAILED[/bold red] - Errors found")
                console.print(f"\n[bold]Full report:[/bold] {report_file}")
                raise typer.Exit(1)
            else:
                console.print("\n[bold green]DRC PASSED[/bold green]")
        except json.JSONDecodeError:
            console.print("[yellow]Warning: Could not parse JSON report[/yellow]")
    else:
        # For text format, just show the file location
        console.print(f"\n[bold]DRC report saved to:[/bold] {report_file}")
        # Try to determine if there are errors by checking exit code
        if not success:
            console.print("\n[bold red]DRC FAILED[/bold red] - Check report for details")
            raise typer.Exit(1)
        else:
            console.print("\n[bold green]DRC PASSED[/bold green]")

    console.print(f"\n[bold]Output directory:[/bold] {output_manager.current_run_dir}")


@drc_app.command("check")
def check_drc_tools():
    """
    Check if KiCad CLI is available for running DRC.
    """
    console.print("\n[bold]KiCad Analyzer - DRC Tool Check[/bold]")
    console.print("=" * 60)

    # Check KiCad CLI
    kicad = KiCadCLI(Path("."))
    if kicad.is_available:
        console.print(f"[green]OK[/green] KiCad CLI found: {kicad.cli_path}")
        version = kicad.get_version()
        if version:
            console.print(f"  Version: {version}")
    else:
        console.print("[red]X[/red] KiCad CLI not found")
        console.print("  Please install KiCad 8.0+ from https://www.kicad.org/")

    console.print()
