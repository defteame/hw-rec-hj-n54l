"""
Formatting utilities for CLI output.

This module provides functions for formatting data into human-readable
tables, measurements, and other display formats.
"""

from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


console = Console()


def format_measurement(value: float, unit: str = "mm", precision: int = 3) -> str:
    """
    Format a measurement value with units.

    Args:
        value: Numeric value
        unit: Unit string (e.g., 'mm', 'µm')
        precision: Number of decimal places

    Returns:
        Formatted string
    """
    return f"{value:.{precision}f} {unit}"


def format_layer_name(layer_id: str) -> str:
    """
    Convert KiCad layer ID to human-readable name.

    Args:
        layer_id: Layer identifier (e.g., 'F.Cu')

    Returns:
        Formatted layer name
    """
    layer_map = {
        'F.Cu': '🔵 Front Copper',
        'B.Cu': '🔴 Back Copper',
        'F.SilkS': 'Front Silkscreen',
        'B.SilkS': 'Back Silkscreen',
        'F.Mask': 'Front Soldermask',
        'B.Mask': 'Back Soldermask',
        'Edge.Cuts': '✂️  Board Outline',
    }
    return layer_map.get(layer_id, layer_id)


def format_table(
    title: str,
    columns: List[str],
    rows: List[List[Any]],
    show_header: bool = True,
    show_lines: bool = False
) -> Table:
    """
    Create a rich Table for CLI display.

    Args:
        title: Table title
        columns: Column headers
        rows: List of row data
        show_header: Whether to show header row
        show_lines: Whether to show lines between rows

    Returns:
        Rich Table object
    """
    table = Table(
        title=title,
        show_header=show_header,
        show_lines=show_lines,
        header_style="bold cyan"
    )

    # Add columns
    for col in columns:
        table.add_column(col)

    # Add rows
    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    return table


def print_summary_panel(title: str, data: Dict[str, Any]) -> None:
    """
    Print a formatted summary panel.

    Args:
        title: Panel title
        data: Dictionary of key-value pairs to display
    """
    lines = []
    for key, value in data.items():
        formatted_key = key.replace('_', ' ').title()
        lines.append(f"[bold cyan]{formatted_key}:[/bold cyan] {value}")

    content = "\n".join(lines)
    panel = Panel(content, title=title, border_style="green")
    console.print(panel)


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]✓[/bold green] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]✗[/bold red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[bold blue]ℹ[/bold blue] {message}")


def format_size(width: float, height: float) -> str:
    """
    Format component size as WxH string.

    Args:
        width: Width in mm
        height: Height in mm

    Returns:
        Formatted size string
    """
    return f"{width:.2f}×{height:.2f} mm"


def format_position(x: float, y: float) -> str:
    """
    Format position coordinates.

    Args:
        x: X coordinate in mm
        y: Y coordinate in mm

    Returns:
        Formatted position string
    """
    return f"({x:+.2f}, {y:+.2f})"


def format_rotation(angle: float) -> str:
    """
    Format rotation angle.

    Args:
        angle: Angle in degrees

    Returns:
        Formatted angle string
    """
    return f"{angle:.1f}°"


def format_percentage(value: float) -> str:
    """
    Format a value as percentage.

    Args:
        value: Numeric value (0-100)

    Returns:
        Formatted percentage string
    """
    return f"{value:.1f}%"


def create_collision_table(collisions: List[Any]) -> Table:
    """
    Create a formatted table for collision reports.

    Args:
        collisions: List of CollisionReport objects

    Returns:
        Rich Table object
    """
    table = Table(
        title="Collision Detection Report",
        show_header=True,
        header_style="bold red"
    )

    table.add_column("Component 1", style="cyan")
    table.add_column("Component 2", style="cyan")
    table.add_column("Distance", justify="right")
    table.add_column("Overlap", justify="right")
    table.add_column("Severity", justify="center")

    for collision in collisions:
        severity_style = {
            'critical': '[bold red]CRITICAL[/bold red]',
            'warning': '[bold yellow]WARNING[/bold yellow]',
            'ok': '[green]OK[/green]'
        }.get(collision.severity, collision.severity)

        table.add_row(
            collision.ref1,
            collision.ref2,
            format_measurement(collision.distance),
            format_measurement(collision.overlap_area, "mm²"),
            severity_style
        )

    return table


def create_fit_table(fit_reports: List[Any], radius: float) -> Table:
    """
    Create a formatted table for circular fit reports.

    Args:
        fit_reports: List of CircularFitReport objects
        radius: Board radius in mm

    Returns:
        Rich Table object
    """
    table = Table(
        title=f"Circular Board Fit Analysis (Ø{radius*2:.1f}mm)",
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("Reference", style="cyan")
    table.add_column("Max Distance", justify="right")
    table.add_column("Margin", justify="right")
    table.add_column("Status", justify="center")

    for report in fit_reports:
        status = "[green]✓ Fits[/green]" if report.fits else "[red]✗ Outside[/red]"
        margin_color = "green" if report.margin > 0 else "red"

        table.add_row(
            report.reference,
            format_measurement(report.max_distance),
            f"[{margin_color}]{format_measurement(report.margin)}[/{margin_color}]",
            status
        )

    return table
