"""
Configuration loader for KiCad Analyzer.

This module handles loading and parsing configuration from YAML files,
with auto-detection of project roots and sensible defaults.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .models import (
    KiCadConfig,
    LayerSpec,
    ProjectConfig,
    RenderConfig,
    View3DSpec,
    get_default_layers_2d,
    get_default_views_3d,
)


# Config file name to search for
CONFIG_FILENAME = "kicad-analyzer.config.yaml"


def find_config_file(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Search for configuration file starting from given path.

    Searches upward through parent directories looking for the config file.

    Args:
        start_path: Starting directory for search. Defaults to cwd.

    Returns:
        Path to config file if found, None otherwise.
    """
    if start_path is None:
        start_path = Path.cwd()

    start_path = start_path.resolve()

    # If start_path is a file, start from its parent
    if start_path.is_file():
        start_path = start_path.parent

    current = start_path
    for _ in range(20):  # Limit search depth
        config_path = current / CONFIG_FILENAME
        if config_path.exists():
            return config_path

        # Also check scripts/ subdirectory
        scripts_config = current / "scripts" / CONFIG_FILENAME
        if scripts_config.exists():
            return scripts_config

        # Move to parent
        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def find_pcb_file(project_root: Path) -> Optional[Path]:
    """
    Auto-detect the PCB file in a project.

    Searches common locations for .kicad_pcb files.

    Args:
        project_root: Project root directory.

    Returns:
        Path to PCB file if found, None otherwise.
    """
    # Check common paths
    common_paths = [
        project_root / "layouts" / "main" / "main.kicad_pcb",
        project_root / "layouts" / "default" / "default.kicad_pcb",
        project_root / "build" / "builds" / "main" / "main.kicad_pcb",
    ]

    for path in common_paths:
        if path.exists():
            return path

    # Search for any .kicad_pcb file in layouts/
    layouts_dir = project_root / "layouts"
    if layouts_dir.exists():
        for pcb_file in layouts_dir.rglob("*.kicad_pcb"):
            return pcb_file

    # Search for any .kicad_pcb file in build/builds/
    builds_dir = project_root / "build" / "builds"
    if builds_dir.exists():
        for pcb_file in builds_dir.rglob("*.kicad_pcb"):
            return pcb_file

    return None


def _parse_layer_spec(data: Dict[str, Any]) -> LayerSpec:
    """Parse a layer specification from YAML data."""
    return LayerSpec(
        name=data.get("name", "unnamed"),
        description=data.get("description", ""),
        layers=data.get("layers", []),
    )


def _parse_view_3d_spec(data: Dict[str, Any]) -> View3DSpec:
    """Parse a 3D view specification from YAML data."""
    return View3DSpec(
        name=data.get("name", "unnamed"),
        description=data.get("description", ""),
        side=data.get("side"),
        rotate=data.get("rotate"),
    )


def _parse_render_config(data: Dict[str, Any]) -> RenderConfig:
    """Parse render configuration from YAML data."""
    layers_2d_data = data.get("layers_2d", [])
    views_3d_data = data.get("views_3d", [])

    # Use defaults if not specified
    layers_2d = [_parse_layer_spec(l) for l in layers_2d_data] if layers_2d_data else get_default_layers_2d()
    views_3d = [_parse_view_3d_spec(v) for v in views_3d_data] if views_3d_data else get_default_views_3d()

    return RenderConfig(
        output_dir=data.get("output_dir", "renders"),
        width=data.get("width", 1200),
        height=data.get("height", 900),
        format=data.get("format", "png"),
        cleanup=data.get("cleanup", True),
        include_3d=data.get("include_3d", True),
        layers_2d=layers_2d,
        views_3d=views_3d,
    )


def _parse_kicad_config(data: Dict[str, Any]) -> KiCadConfig:
    """Parse KiCad configuration from YAML data."""
    cli_paths = [Path(p) for p in data.get("additional_cli_paths", [])]
    inkscape_paths = [Path(p) for p in data.get("additional_inkscape_paths", [])]

    return KiCadConfig(
        additional_cli_paths=cli_paths,
        additional_inkscape_paths=inkscape_paths,
    )


def load_config(
    start_path: Optional[Path] = None,
    pcb_file: Optional[Path] = None,
) -> ProjectConfig:
    """
    Load project configuration.

    Searches for config file, loads settings, and resolves paths.
    Falls back to sensible defaults if config file not found.

    Args:
        start_path: Starting path for config search.
        pcb_file: Explicit PCB file path (overrides config/auto-detect).

    Returns:
        ProjectConfig instance.

    Raises:
        ValueError: If PCB file cannot be found.
    """
    config_path = find_config_file(start_path)

    if config_path:
        config_dir = config_path.parent
        project_root = config_dir.parent if config_dir.name == "scripts" else config_dir

        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}
    else:
        # No config file - use defaults
        project_root = Path(start_path or Path.cwd()).resolve()
        if project_root.is_file():
            project_root = project_root.parent
        raw_config = {}
        config_dir = project_root

    # Parse configuration sections
    project_data = raw_config.get("project", {})
    render_data = raw_config.get("render", {})
    kicad_data = raw_config.get("kicad", {})

    # Resolve PCB file path
    if pcb_file:
        resolved_pcb = Path(pcb_file).resolve()
    elif "pcb_file" in project_data:
        resolved_pcb = (config_dir / project_data["pcb_file"]).resolve()
    else:
        resolved_pcb = find_pcb_file(project_root)

    if resolved_pcb is None:
        raise ValueError(
            f"Could not find PCB file in project: {project_root}\n"
            "Please specify pcb_file in config or use --pcb argument."
        )

    # Resolve build directory
    if "build_dir" in project_data:
        build_dir = (config_dir / project_data["build_dir"]).resolve()
    else:
        build_dir = project_root / "build"

    return ProjectConfig(
        project_root=project_root,
        pcb_file=resolved_pcb,
        build_dir=build_dir,
        render=_parse_render_config(render_data),
        kicad=_parse_kicad_config(kicad_data),
    )
