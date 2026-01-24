"""
Configuration data models for KiCad Analyzer.

This module defines dataclasses for all configuration types
used throughout the application.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class LayerSpec:
    """
    Specification for a 2D layer render.

    Attributes:
        name: Output filename (without extension).
        description: Human-readable description.
        layers: List of KiCad layer names to include.
    """

    name: str
    description: str
    layers: List[str]


@dataclass
class View3DSpec:
    """
    Specification for a 3D render view.

    Attributes:
        name: Output filename (without extension).
        description: Human-readable description.
        side: View side ("top", "bottom", "front", "back", "left", "right").
        rotate: Custom rotation as "X,Y,Z" degrees string.
    """

    name: str
    description: str
    side: Optional[str] = None
    rotate: Optional[str] = None


@dataclass
class RenderConfig:
    """
    Render command configuration.

    Attributes:
        output_dir: Output subdirectory name within build_dir.
        width: Default image width in pixels.
        height: Default image height for 3D renders.
        format: Default output format ("png" or "svg").
        cleanup: Whether to clean up previous renders.
        include_3d: Whether to include 3D renders.
        layers_2d: List of 2D layer render specifications.
        views_3d: List of 3D view specifications.
    """

    output_dir: str = "renders"
    width: int = 1200
    height: int = 900
    format: str = "png"
    cleanup: bool = True
    include_3d: bool = True
    layers_2d: List[LayerSpec] = field(default_factory=list)
    views_3d: List[View3DSpec] = field(default_factory=list)


@dataclass
class KiCadConfig:
    """
    KiCad-specific configuration.

    Attributes:
        additional_cli_paths: Extra paths to search for kicad-cli.
        additional_inkscape_paths: Extra paths to search for Inkscape.
    """

    additional_cli_paths: List[Path] = field(default_factory=list)
    additional_inkscape_paths: List[Path] = field(default_factory=list)


@dataclass
class ProjectConfig:
    """
    Complete project configuration.

    Attributes:
        project_root: Absolute path to project root directory.
        pcb_file: Absolute path to the KiCad PCB file.
        build_dir: Absolute path to build output directory.
        render: Render command configuration.
        kicad: KiCad-specific configuration.
    """

    project_root: Path
    pcb_file: Path
    build_dir: Path
    render: RenderConfig = field(default_factory=RenderConfig)
    kicad: KiCadConfig = field(default_factory=KiCadConfig)

    @property
    def renders_dir(self) -> Path:
        """Get the absolute path to renders directory."""
        return self.build_dir / self.render.output_dir


def get_default_layers_2d() -> List[LayerSpec]:
    """Get default 2D layer specifications."""
    return [
        LayerSpec(
            name="full-board",
            description="Complete board view with all copper and silkscreen",
            layers=["F.Cu", "B.Cu", "F.SilkS", "B.SilkS", "Edge.Cuts"],
        ),
        LayerSpec(
            name="top-copper",
            description="Front copper layer only",
            layers=["F.Cu", "Edge.Cuts"],
        ),
        LayerSpec(
            name="bottom-copper",
            description="Back copper layer only",
            layers=["B.Cu", "Edge.Cuts"],
        ),
        LayerSpec(
            name="top-silkscreen",
            description="Front silkscreen layer only",
            layers=["F.SilkS", "Edge.Cuts"],
        ),
        LayerSpec(
            name="bottom-silkscreen",
            description="Back silkscreen layer only",
            layers=["B.SilkS", "Edge.Cuts"],
        ),
        LayerSpec(
            name="top-mask",
            description="Front solder mask layer",
            layers=["F.Mask", "Edge.Cuts"],
        ),
        LayerSpec(
            name="bottom-mask",
            description="Back solder mask layer",
            layers=["B.Mask", "Edge.Cuts"],
        ),
        LayerSpec(
            name="top-assembly",
            description="Front assembly/fabrication view",
            layers=["F.Fab", "F.SilkS", "Edge.Cuts"],
        ),
        LayerSpec(
            name="bottom-assembly",
            description="Back assembly/fabrication view",
            layers=["B.Fab", "B.SilkS", "Edge.Cuts"],
        ),
    ]


def get_default_views_3d() -> List[View3DSpec]:
    """Get default 3D view specifications."""
    return [
        # Standard orthographic views
        View3DSpec(name="3d-top", description="Top-down view", side="top"),
        View3DSpec(name="3d-bottom", description="Bottom-up view", side="bottom"),
        View3DSpec(name="3d-front", description="Front view", side="front"),
        View3DSpec(name="3d-back", description="Back view", side="back"),
        View3DSpec(name="3d-left", description="Left side view", side="left"),
        View3DSpec(name="3d-right", description="Right side view", side="right"),
        # Isometric views
        View3DSpec(name="3d-iso-front-right", description="Isometric front-right", rotate="60,0,30"),
        View3DSpec(name="3d-iso-front-left", description="Isometric front-left", rotate="60,0,-30"),
        View3DSpec(name="3d-iso-back-right", description="Isometric back-right", rotate="60,0,150"),
        View3DSpec(name="3d-iso-back-left", description="Isometric back-left", rotate="60,0,-150"),
        # Bottom isometric views
        View3DSpec(name="3d-iso-bottom-front", description="Isometric bottom front", rotate="120,0,30"),
        View3DSpec(name="3d-iso-bottom-back", description="Isometric bottom back", rotate="120,0,-150"),
    ]
