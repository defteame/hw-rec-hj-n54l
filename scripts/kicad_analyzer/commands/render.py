"""
Render command implementation.

This module implements the 'render' subcommand which generates
2D layer renders and 3D views of the PCB using KiCad CLI.
"""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..config import load_config, LayerSpec, View3DSpec, ProjectConfig
from ..core.kicad_cli import KiCadCLI
from ..core.converters import ImageConverter


# Create Typer app for render commands
render_app = typer.Typer(
    name="render",
    help="Generate PCB renders (2D layers and 3D views)",
)

console = Console()


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string for use as a filename.

    Replaces dots and special characters with underscores.
    """
    name = name.replace(".", "_")
    name = re.sub(r"[^\w\-]", "_", name)
    name = name.lower()
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    return name


def layers_to_filename(layers: List[str]) -> str:
    """Generate a filename from a list of layer names."""
    if len(layers) == 1:
        return sanitize_filename(layers[0])
    return "_".join(sanitize_filename(layer) for layer in layers)


def cleanup_old_renders(renders_dir: Path, keep_current: Optional[Path] = None) -> int:
    """
    Remove previous render directories.

    Args:
        renders_dir: Base renders directory.
        keep_current: Path to current render folder to preserve.

    Returns:
        Number of directories removed.
    """
    removed_count = 0

    if not renders_dir.exists():
        return 0

    for item in renders_dir.iterdir():
        if not item.is_dir():
            continue

        if keep_current and item.resolve() == keep_current.resolve():
            continue

        try:
            shutil.rmtree(item)
            removed_count += 1
        except OSError as e:
            console.print(f"[yellow]Warning: Could not remove {item}: {e}[/yellow]")

    return removed_count


def render_2d_layers(
    kicad: KiCadCLI,
    converter: ImageConverter,
    output_dir: Path,
    layer_specs: List[LayerSpec],
    width: int,
    format: str,
    keep_svg: bool = True,
) -> List[Path]:
    """
    Generate 2D layer renders.

    Args:
        kicad: KiCad CLI instance.
        converter: Image converter instance.
        output_dir: Directory to save renders.
        layer_specs: List of layer specifications to render.
        width: Image width in pixels.
        format: Output format ('png' or 'svg').
        keep_svg: If True and format is 'png', also save SVG.

    Returns:
        List of generated file paths.
    """
    generated: List[Path] = []

    # Create SVG subfolder if keeping SVGs
    svg_dir = output_dir / "svg"
    if format == "png" and keep_svg:
        svg_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold cyan]2D Layer Renders ({len(layer_specs)} files)[/bold cyan]")

    # Check PNG tools upfront if PNG format requested
    if format == "png":
        available, tool_name, guidance = converter.check_available()
        if not available:
            console.print("\n[bold red]Error: PNG conversion tools not available![/bold red]")
            console.print("\nTo generate PNG renders, install ONE of the following:")
            for hint in guidance:
                console.print(hint)
            console.print("\nOn Windows, the easiest option is to install Inkscape.")
            console.print("Alternatively, use --format svg to output SVG files.\n")
            return []
        console.print(f"  PNG conversion tool: [green]{tool_name}[/green]")

    for idx, spec in enumerate(layer_specs, 1):
        filename = layers_to_filename(spec.layers)

        console.print(f"\n  [{idx}/{len(layer_specs)}] {spec.description}")
        console.print(f"    Layers: {', '.join(spec.layers)}")

        if format == "svg":
            output_file = output_dir / f"{filename}.svg"
            success = kicad.export_svg(output_file, spec.layers)
            if success and output_file.exists():
                generated.append(output_file)
                console.print(f"    [green]-> {output_file}[/green]")
            else:
                console.print(f"    [red]!! FAILED[/red]")
        else:
            # PNG format - also keep SVG in subfolder
            png_file = output_dir / f"{filename}.png"
            svg_file = svg_dir / f"{filename}.svg"

            # First export SVG
            if not kicad.export_svg(svg_file, spec.layers):
                console.print(f"    [red]!! SVG export failed[/red]")
                continue

            # Convert to PNG
            success, error_msg = converter.convert(svg_file, png_file, width=width)

            if success and png_file.exists():
                generated.append(png_file)
                generated.append(svg_file)
                console.print(f"    [green]-> {png_file}[/green]")
                console.print(f"    [green]-> {svg_file}[/green]")
            else:
                console.print(f"    [red]!! {error_msg or 'PNG conversion failed'}[/red]")

    return generated


def render_3d_views(
    kicad: KiCadCLI,
    output_dir: Path,
    view_specs: List[View3DSpec],
    width: int,
    height: int,
) -> List[Path]:
    """
    Generate 3D view renders.

    Args:
        kicad: KiCad CLI instance.
        output_dir: Directory to save renders.
        view_specs: List of 3D view specifications.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        List of generated file paths.
    """
    generated: List[Path] = []

    console.print(f"\n[bold cyan]3D Renders ({len(view_specs)} files)[/bold cyan]")

    for idx, spec in enumerate(view_specs, 1):
        output_file = output_dir / f"{spec.name}.png"
        console.print(f"\n  [{idx}/{len(view_specs)}] {spec.name}")
        console.print(f"    View: {spec.description}")

        success = kicad.render_3d(
            output_file,
            side=spec.side,
            rotate=spec.rotate,
            width=width,
            height=height,
        )

        if success and output_file.exists():
            generated.append(output_file)
            console.print(f"    [green]-> {output_file}[/green]")
        else:
            console.print(f"    [red]!! 3D render failed[/red]")

    return generated


@render_app.command("all")
def render_all(
    pcb: Optional[Path] = typer.Option(
        None,
        "--pcb",
        "-p",
        help="Path to PCB file (auto-detected if not specified)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: build/renders/<timestamp>)",
    ),
    width: int = typer.Option(
        1200,
        "--width",
        "-w",
        help="Image width in pixels",
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
    no_cleanup: bool = typer.Option(
        False,
        "--no-cleanup",
        help="Keep previous render folders",
    ),
):
    """
    Generate all PCB renders (2D layers and 3D views).

    Creates a complete set of render images showing different layers
    and 3D perspectives of the PCB design.
    """
    try:
        config = load_config(pcb_file=pcb)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)

    # Override config with CLI options
    render_cfg = config.render
    actual_width = width
    actual_height = height
    actual_format = format
    include_3d = not no_3d
    do_cleanup = not no_cleanup

    # Create output directory with timestamp
    if output is None:
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        output_dir = config.renders_dir / timestamp
    else:
        output_dir = output

    output_dir.mkdir(parents=True, exist_ok=True)

    # Cleanup old renders
    if do_cleanup:
        removed = cleanup_old_renders(config.renders_dir, keep_current=output_dir)
        if removed > 0:
            console.print(f"[dim]Cleaned up {removed} previous render folder(s)[/dim]")

    # Initialize KiCad CLI
    kicad = KiCadCLI(
        config.pcb_file,
        additional_cli_paths=list(config.kicad.additional_cli_paths),
    )
    converter = ImageConverter(list(config.kicad.additional_inkscape_paths))

    # Calculate totals
    total_2d = len(render_cfg.layers_2d)
    total_3d = len(render_cfg.views_3d) if include_3d else 0
    total_files = total_2d + total_3d

    # Print header
    console.print()
    console.print("[bold]KiCad Analyzer - Render Command[/bold]")
    console.print("=" * 60)
    console.print(f"PCB File: [cyan]{config.pcb_file}[/cyan]")
    console.print(f"Output Directory: [cyan]{output_dir}[/cyan]")
    console.print(f"KiCad CLI Available: [{'green' if kicad.is_available else 'red'}]{kicad.is_available}[/]")
    if kicad.cli_path:
        console.print(f"KiCad CLI Path: [dim]{kicad.cli_path}[/dim]")
    console.print("=" * 60)
    console.print(f"\nTotal renders to generate: {total_files} ({total_2d} 2D + {total_3d} 3D)")
    console.print("[yellow]WARNING: Please wait for all files to complete rendering.[/yellow]\n")

    # Check prerequisites
    if not config.pcb_file.exists():
        console.print(f"\n[bold red]Error: PCB file not found:[/bold red] {config.pcb_file}")
        raise typer.Exit(1)

    if not kicad.is_available:
        console.print("\n[bold red]Error: KiCad CLI not found.[/bold red]")
        console.print("Please ensure KiCad 8.0+ is installed.")
        raise typer.Exit(1)

    generated_files: List[Path] = []

    # Generate 2D renders
    render_2d_files = render_2d_layers(
        kicad,
        converter,
        output_dir,
        render_cfg.layers_2d,
        actual_width,
        actual_format,
    )
    generated_files.extend(render_2d_files)

    # If 2D renders failed completely, stop
    if not render_2d_files and actual_format == "png":
        console.print("\n[bold yellow]Render stopped due to errors.[/bold yellow]")
        raise typer.Exit(1)

    # Generate 3D renders
    if include_3d:
        render_3d_files = render_3d_views(
            kicad,
            output_dir,
            render_cfg.views_3d,
            actual_width,
            actual_height,
        )
        generated_files.extend(render_3d_files)

    # Print summary
    console.print("\n[bold cyan]Summary[/bold cyan]")
    console.print("=" * 60)
    console.print(f"Total files generated: [bold]{len(generated_files)}[/bold]")

    if generated_files:
        console.print("\n[bold]Generated files:[/bold]")
        for f in generated_files:
            console.print(f"  [green]{f}[/green]")
    else:
        console.print("\n[yellow]No files were generated.[/yellow]")

    console.print(f"\n[bold]Output directory:[/bold] {output_dir}")


@render_app.command("2d")
def render_2d_only(
    pcb: Optional[Path] = typer.Option(
        None,
        "--pcb",
        "-p",
        help="Path to PCB file",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory",
    ),
    width: int = typer.Option(
        1200,
        "--width",
        "-w",
        help="Image width in pixels",
    ),
    format: str = typer.Option(
        "png",
        "--format",
        "-f",
        help="Output format (png or svg)",
    ),
    layers: Optional[str] = typer.Option(
        None,
        "--layers",
        "-l",
        help="Comma-separated layers (e.g., F.Cu,Edge.Cuts)",
    ),
    name: str = typer.Option(
        "custom",
        "--name",
        "-n",
        help="Output filename (without extension)",
    ),
):
    """
    Render specific 2D layers only.

    Use this for quick custom layer exports without full render sets.
    """
    try:
        config = load_config(pcb_file=pcb)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)

    if output is None:
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        output_dir = config.renders_dir / timestamp
    else:
        output_dir = output

    output_dir.mkdir(parents=True, exist_ok=True)

    kicad = KiCadCLI(
        config.pcb_file,
        additional_cli_paths=list(config.kicad.additional_cli_paths),
    )
    converter = ImageConverter(list(config.kicad.additional_inkscape_paths))

    if not kicad.is_available:
        console.print("[bold red]Error: KiCad CLI not found.[/bold red]")
        raise typer.Exit(1)

    # Parse layers
    if layers:
        layer_list = [l.strip() for l in layers.split(",")]
        layer_specs = [LayerSpec(name=name, description="Custom layers", layers=layer_list)]
    else:
        layer_specs = config.render.layers_2d

    generated = render_2d_layers(
        kicad,
        converter,
        output_dir,
        layer_specs,
        width,
        format,
    )

    console.print(f"\n[bold]Generated {len(generated)} files in:[/bold] {output_dir}")


@render_app.command("3d")
def render_3d_only(
    pcb: Optional[Path] = typer.Option(
        None,
        "--pcb",
        "-p",
        help="Path to PCB file",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory",
    ),
    width: int = typer.Option(
        1600,
        "--width",
        "-w",
        help="Image width in pixels",
    ),
    height: int = typer.Option(
        900,
        "--height",
        help="Image height in pixels",
    ),
    side: Optional[str] = typer.Option(
        None,
        "--side",
        "-s",
        help="View side (top, bottom, front, back, left, right)",
    ),
    rotate: Optional[str] = typer.Option(
        None,
        "--rotate",
        "-r",
        help="Custom rotation as X,Y,Z degrees",
    ),
    name: str = typer.Option(
        "3d-custom",
        "--name",
        "-n",
        help="Output filename (without extension)",
    ),
):
    """
    Render specific 3D view only.

    Use this for quick custom 3D exports.
    """
    try:
        config = load_config(pcb_file=pcb)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)

    if output is None:
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        output_dir = config.renders_dir / timestamp
    else:
        output_dir = output

    output_dir.mkdir(parents=True, exist_ok=True)

    kicad = KiCadCLI(
        config.pcb_file,
        additional_cli_paths=list(config.kicad.additional_cli_paths),
    )

    if not kicad.is_available:
        console.print("[bold red]Error: KiCad CLI not found.[/bold red]")
        raise typer.Exit(1)

    # Create view spec
    if side or rotate:
        view_specs = [View3DSpec(
            name=name,
            description=f"Custom view ({side or rotate})",
            side=side,
            rotate=rotate,
        )]
    else:
        view_specs = config.render.views_3d

    generated = render_3d_views(
        kicad,
        output_dir,
        view_specs,
        width,
        height,
    )

    console.print(f"\n[bold]Generated {len(generated)} files in:[/bold] {output_dir}")


@render_app.command("check")
def check_tools():
    """
    Check if required tools (KiCad CLI, PNG converters) are available.
    """
    console.print("\n[bold]KiCad Analyzer - Tool Check[/bold]")
    console.print("=" * 60)

    # Check KiCad CLI
    kicad = KiCadCLI(Path("."))
    if kicad.is_available:
        console.print(f"[green]✓[/green] KiCad CLI found: {kicad.cli_path}")
        version = kicad.get_version()
        if version:
            console.print(f"  Version: {version}")
    else:
        console.print("[red]✗[/red] KiCad CLI not found")
        console.print("  Please install KiCad 8.0+ from https://www.kicad.org/")

    # Check PNG converter
    converter = ImageConverter()
    available, tool_name, guidance = converter.check_available()
    if available:
        console.print(f"[green]✓[/green] PNG converter found: {tool_name}")
    else:
        console.print("[red]✗[/red] PNG converter not found")
        console.print("  Install ONE of the following:")
        for hint in guidance:
            console.print(f"  {hint}")

    console.print()
