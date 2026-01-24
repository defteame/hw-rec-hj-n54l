"""
KiCad Analyzer CLI - Main entrypoint.

This module provides the main CLI application that coordinates all subcommands
for analyzing KiCad PCB files, footprints, and component placements.
"""

import typer
from rich.console import Console
from pathlib import Path

from . import __version__, __author__
from .commands import footprint_app, pcb_app, placement_app, analyze_app, render_app
from .utils.output import OutputManager


# Main CLI application
app = typer.Typer(
    name="kicad-analyzer",
    help="""
    KiCad Analyzer - Comprehensive PCB analysis toolkit

    A powerful CLI tool for analyzing KiCad PCB files, footprints,
    and component placements. Provides detailed geometry analysis,
    collision detection, and placement validation.

    Use --help on any command for detailed usage information.
    """,
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


# Add subcommands
app.add_typer(footprint_app, name="footprint")
app.add_typer(pcb_app, name="pcb")
app.add_typer(placement_app, name="placement")
app.add_typer(analyze_app, name="analyze")
app.add_typer(render_app, name="render")


@app.command()
def version():
    """
    Display version information.
    """
    console.print(f"[bold cyan]KiCad Analyzer[/bold cyan] version [bold]{__version__}[/bold]")
    console.print(f"Author: {__author__}")


@app.command()
def latest():
    """
    Show information about the latest analysis run.
    """
    latest_run = OutputManager.get_latest_run()

    if latest_run is None:
        console.print("[yellow]No analysis runs found.[/yellow]")
        console.print()
        console.print("Run an analysis first:")
        console.print("  kicad-analyzer analyze placement <pcb_file>")
        raise typer.Exit(1)

    console.print("=" * 80)
    console.print("[bold]Latest KiCad Analysis Results[/bold]")
    console.print("=" * 80)
    console.print()
    console.print(f"[bold]Run directory:[/bold] {latest_run.name}")
    console.print()

    # Read and display summary
    summary_file = latest_run / "_run_summary.md"
    if summary_file.exists():
        console.print(summary_file.read_text(encoding='utf-8'))
    else:
        console.print("Summary file not found.")
        console.print()
        console.print("Files in directory:")
        for file in sorted(latest_run.iterdir()):
            if file.is_file():
                size_kb = file.stat().st_size / 1024
                console.print(f"  - {file.name} ({size_kb:.1f} KB)")

    console.print()
    console.print("=" * 80)
    console.print(f"[bold]Full path:[/bold] {latest_run}")
    console.print("=" * 80)


@app.callback()
def main_callback():
    """
    KiCad Analyzer - A comprehensive toolkit for PCB analysis.
    """
    pass


def main():
    """Main entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
