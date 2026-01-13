"""
KiCad Analyzer CLI - Main entrypoint.

This module provides the main CLI application that coordinates all subcommands
for analyzing KiCad PCB files, footprints, and component placements.
"""

import typer
from rich.console import Console
from pathlib import Path

from . import __version__, __author__
from .commands import footprint_app, pcb_app, placement_app


# Main CLI application
app = typer.Typer(
    name="kicad-analyzer",
    help="""
    🔧 KiCad Analyzer - Comprehensive PCB analysis toolkit

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


@app.command()
def version():
    """
    Display version information.
    """
    console.print(f"[bold cyan]KiCad Analyzer[/bold cyan] version [bold]{__version__}[/bold]")
    console.print(f"Author: {__author__}")


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
