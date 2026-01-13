"""
High-level analysis functions for KiCad footprints and PCBs.

This module provides analyzers that compute statistics, check constraints,
and generate reports from parsed KiCad data.
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from .parser import KiCadParser, ParsedFootprint, ParsedPCB
from .geometry import BoundingBox, Point, check_collision


@dataclass
class FootprintStats:
    """Statistics for a footprint."""

    reference: str
    footprint_name: str
    bbox_width: float
    bbox_height: float
    bbox_area: float
    pad_count: int
    layer: str
    position: Point
    rotation: float


@dataclass
class CollisionReport:
    """Report of collision between two footprints."""

    ref1: str
    ref2: str
    distance: float
    overlap_area: float
    severity: str  # 'critical', 'warning', 'ok'


@dataclass
class CircularFitReport:
    """Report of footprint fit within circular board."""

    reference: str
    fits: bool
    max_distance: float
    margin: float


class FootprintAnalyzer:
    """Analyzer for individual footprint files."""

    def __init__(self, footprint_path: Path):
        """
        Initialize analyzer with a footprint file.

        Args:
            footprint_path: Path to .kicad_mod file
        """
        self.footprint_path = footprint_path
        self.parser = KiCadParser()
        self.footprint = self.parser.load_footprint(footprint_path)

    def get_bbox(self) -> BoundingBox:
        """Calculate and return the footprint's bounding box."""
        return self.parser.extract_footprint_bbox(self.footprint)

    def get_pad_info(self) -> List[Dict[str, Any]]:
        """Extract detailed information about all pads."""
        pads = []
        for pad in self.footprint.pads:
            pad_info = {
                'number': pad.number if hasattr(pad, 'number') else '',
                'type': pad.type if hasattr(pad, 'type') else '',
                'shape': pad.shape if hasattr(pad, 'shape') else '',
                'size': (pad.size.X, pad.size.Y) if pad.size else (0, 0),
                'position': (pad.position.X, pad.position.Y),
                'layers': pad.layers if hasattr(pad, 'layers') else [],
                'drill': pad.drill if hasattr(pad, 'drill') else None,
            }
            pads.append(pad_info)
        return pads

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of the footprint."""
        bbox = self.get_bbox()
        pads = self.get_pad_info()

        return {
            'name': self.footprint.entryName if hasattr(self.footprint, 'entryName') else 'Unknown',
            'library': self.footprint.libraryNickname if hasattr(self.footprint, 'libraryNickname') else None,
            'bbox': {
                'width': bbox.width,
                'height': bbox.height,
                'area': bbox.area,
            },
            'pad_count': len(pads),
            'pads': pads,
            'file_path': str(self.footprint_path),
        }


class PCBAnalyzer:
    """Analyzer for PCB files with multiple footprints."""

    def __init__(self, pcb_path: Path):
        """
        Initialize analyzer with a PCB file.

        Args:
            pcb_path: Path to .kicad_pcb file
        """
        self.pcb_path = pcb_path
        self.parser = KiCadParser()
        self.parsed_pcb = self.parser.parse_pcb_full(pcb_path)

    def get_footprint_stats(self) -> List[FootprintStats]:
        """Get statistics for all footprints on the PCB."""
        stats = []
        for fp in self.parsed_pcb.footprints:
            stat = FootprintStats(
                reference=fp.reference,
                footprint_name=fp.footprint_name,
                bbox_width=fp.bbox.width,
                bbox_height=fp.bbox.height,
                bbox_area=fp.bbox.area,
                pad_count=fp.pad_count,
                layer=fp.layer,
                position=fp.position,
                rotation=fp.rotation,
            )
            stats.append(stat)
        return stats

    def check_collisions(self, clearance: float = 0.0) -> List[CollisionReport]:
        """
        Check for collisions between footprints.

        Args:
            clearance: Minimum required clearance in mm

        Returns:
            List of collision reports
        """
        collisions = []
        footprints = self.parsed_pcb.footprints

        for i, fp1 in enumerate(footprints):
            for fp2 in footprints[i+1:]:
                if check_collision(fp1.bbox, fp2.bbox, clearance):
                    # Calculate center-to-center distance
                    distance = fp1.position.distance_to(fp2.position)

                    # Calculate overlap area
                    overlap = fp1.bbox.intersection_area(fp2.bbox)

                    # Determine severity
                    if overlap > 0:
                        severity = 'critical'
                    elif distance < (fp1.bbox.width + fp2.bbox.width) / 2 + clearance:
                        severity = 'warning'
                    else:
                        severity = 'ok'

                    report = CollisionReport(
                        ref1=fp1.reference,
                        ref2=fp2.reference,
                        distance=distance,
                        overlap_area=overlap,
                        severity=severity,
                    )
                    collisions.append(report)

        return collisions

    def check_circular_fit(self, radius: float, center: Optional[Point] = None) -> List[CircularFitReport]:
        """
        Check if all footprints fit within a circular board outline.

        Args:
            radius: Board radius in mm
            center: Center point (defaults to origin)

        Returns:
            List of fit reports for each footprint
        """
        if center is None:
            center = Point(0, 0)

        reports = []
        for fp in self.parsed_pcb.footprints:
            max_dist = fp.bbox.max_distance_from_point(center)
            fits = max_dist <= radius
            margin = radius - max_dist

            report = CircularFitReport(
                reference=fp.reference,
                fits=fits,
                max_distance=max_dist,
                margin=margin,
            )
            reports.append(report)

        return reports

    def get_layer_distribution(self) -> Dict[str, int]:
        """Get count of footprints on each layer."""
        distribution = {}
        for fp in self.parsed_pcb.footprints:
            layer = fp.layer
            distribution[layer] = distribution.get(layer, 0) + 1
        return distribution

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of the PCB."""
        stats = self.get_footprint_stats()
        layer_dist = self.get_layer_distribution()

        # Calculate statistics
        total_footprints = len(stats)
        total_pads = sum(s.pad_count for s in stats)
        total_area = sum(s.bbox_area for s in stats)

        avg_width = sum(s.bbox_width for s in stats) / total_footprints if total_footprints > 0 else 0
        avg_height = sum(s.bbox_height for s in stats) / total_footprints if total_footprints > 0 else 0

        return {
            'file_path': str(self.pcb_path),
            'pcb_thickness': self.parsed_pcb.thickness,
            'layer_count': self.parsed_pcb.layer_count,
            'layers': self.parsed_pcb.layers,
            'has_edge_cuts': self.parsed_pcb.has_edge_cuts,
            'footprint_count': total_footprints,
            'total_pads': total_pads,
            'total_component_area': total_area,
            'layer_distribution': layer_dist,
            'average_footprint_size': {
                'width': avg_width,
                'height': avg_height,
            },
            'board_bbox': {
                'width': self.parsed_pcb.board_bbox.width if self.parsed_pcb.board_bbox else 0,
                'height': self.parsed_pcb.board_bbox.height if self.parsed_pcb.board_bbox else 0,
            } if self.parsed_pcb.board_bbox else None,
        }

    def find_footprint_by_reference(self, reference: str) -> Optional[ParsedFootprint]:
        """Find a footprint by its reference designator."""
        for fp in self.parsed_pcb.footprints:
            if fp.reference == reference:
                return fp
        return None

    def get_footprints_by_layer(self, layer: str) -> List[ParsedFootprint]:
        """Get all footprints on a specific layer."""
        return [fp for fp in self.parsed_pcb.footprints if fp.layer == layer]

    def calculate_density(self) -> float:
        """
        Calculate PCB component density.

        Returns:
            Percentage of board area covered by components
        """
        if not self.parsed_pcb.board_bbox:
            return 0.0

        board_area = self.parsed_pcb.board_bbox.area
        component_area = sum(fp.bbox.area for fp in self.parsed_pcb.footprints)

        return (component_area / board_area * 100) if board_area > 0 else 0.0
