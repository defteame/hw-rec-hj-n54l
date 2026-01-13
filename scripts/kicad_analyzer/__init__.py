"""
KiCad Analyzer - A comprehensive CLI tool for analyzing KiCad PCB files.

This package provides utilities for:
- Analyzing footprint dimensions and geometries
- Inspecting PCB layouts and component placements
- Validating placement constraints
- Generating reports and visualizations
"""

__version__ = "0.1.0"
__author__ = "HW-REC Project"

from .core.geometry import BoundingBox, Point
from .core.analyzer import FootprintAnalyzer, PCBAnalyzer

__all__ = [
    "BoundingBox",
    "Point",
    "FootprintAnalyzer",
    "PCBAnalyzer",
]
