"""Core functionality for KiCad file parsing and analysis."""

from .geometry import BoundingBox, Point
from .parser import KiCadParser
from .analyzer import FootprintAnalyzer, PCBAnalyzer
from .kicad_cli import KiCadCLI
from .converters import ImageConverter

__all__ = [
    "BoundingBox",
    "Point",
    "KiCadParser",
    "FootprintAnalyzer",
    "PCBAnalyzer",
    "KiCadCLI",
    "ImageConverter",
]
