"""Core functionality for KiCad file parsing and analysis."""

from .geometry import BoundingBox, Point
from .parser import KiCadParser
from .analyzer import FootprintAnalyzer, PCBAnalyzer

__all__ = [
    "BoundingBox",
    "Point",
    "KiCadParser",
    "FootprintAnalyzer",
    "PCBAnalyzer",
]
