"""
KiCad file parsing utilities using kiutils library.

This module provides high-level interfaces for loading and parsing
KiCad PCB files (.kicad_pcb) and footprint files (.kicad_mod).
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

try:
    from kiutils.board import Board
    from kiutils.footprint import Footprint
    from kiutils.items.common import Position
except ImportError:
    raise ImportError(
        "kiutils library is required. Install with: pip install kiutils"
    )

from .geometry import Point, BoundingBox


@dataclass
class ParsedFootprint:
    """Parsed footprint with computed geometry information."""

    reference: str
    footprint_name: str
    position: Point
    rotation: float
    layer: str
    bbox: BoundingBox
    pad_count: int
    pads: List[Dict[str, Any]]
    library: Optional[str] = None


@dataclass
class ParsedPCB:
    """Parsed PCB with computed information."""

    file_path: Path
    thickness: float
    footprints: List[ParsedFootprint]
    layer_count: int
    layers: List[str]
    board_bbox: Optional[BoundingBox]
    has_edge_cuts: bool


class KiCadParser:
    """
    High-level parser for KiCad files using kiutils.

    This class provides convenient methods for loading and extracting
    information from KiCad PCB and footprint files.
    """

    @staticmethod
    def load_pcb(file_path: Path) -> Board:
        """
        Load a KiCad PCB file.

        Args:
            file_path: Path to .kicad_pcb file

        Returns:
            Board object from kiutils

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be parsed
        """
        if not file_path.exists():
            raise FileNotFoundError(f"PCB file not found: {file_path}")

        try:
            return Board.from_file(str(file_path))
        except Exception as e:
            raise ValueError(f"Failed to parse PCB file: {e}") from e

    @staticmethod
    def load_footprint(file_path: Path) -> Footprint:
        """
        Load a KiCad footprint file.

        Args:
            file_path: Path to .kicad_mod file

        Returns:
            Footprint object from kiutils

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be parsed
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Footprint file not found: {file_path}")

        try:
            return Footprint.from_file(str(file_path))
        except Exception as e:
            raise ValueError(f"Failed to parse footprint file: {e}") from e

    @staticmethod
    def extract_footprint_bbox(footprint: Footprint) -> BoundingBox:
        """
        Calculate bounding box from footprint pads.

        Args:
            footprint: Footprint object from kiutils

        Returns:
            BoundingBox enclosing all pads

        Raises:
            ValueError: If footprint has no pads
        """
        if not footprint.pads:
            raise ValueError("Footprint has no pads to calculate bounding box")

        points = []
        for pad in footprint.pads:
            # Get pad position
            pos = pad.position
            x, y = pos.X, pos.Y

            # Get pad size
            size_x = pad.size.X if pad.size else 0
            size_y = pad.size.Y if pad.size else 0

            # Add corners of pad bounding box
            points.extend([
                Point(x - size_x/2, y - size_y/2),
                Point(x + size_x/2, y - size_y/2),
                Point(x + size_x/2, y + size_y/2),
                Point(x - size_x/2, y + size_y/2),
            ])

        return BoundingBox.from_points(points)

    @staticmethod
    def get_pcb_thickness(board: Board) -> float:
        """
        Extract PCB thickness from board setup.

        Args:
            board: Board object

        Returns:
            PCB thickness in mm
        """
        try:
            # Access board thickness from setup
            if hasattr(board, 'setup') and board.setup:
                if hasattr(board.setup, 'stackup') and board.setup.stackup:
                    for layer in board.setup.stackup.layers:
                        if layer.type == 'core':
                            return layer.thickness if hasattr(layer, 'thickness') else 1.6
            # Default to 1.6mm if not found
            return 1.6
        except Exception:
            return 1.6

    @classmethod
    def parse_pcb_footprints(cls, board: Board) -> List[ParsedFootprint]:
        """
        Parse all footprints from a PCB board.

        Args:
            board: Board object from kiutils

        Returns:
            List of ParsedFootprint objects
        """
        parsed = []

        for fp in board.footprints:
            try:
                # Extract position
                pos = fp.position
                position = Point(pos.X, pos.Y)

                # Extract rotation
                rotation = pos.angle if hasattr(pos, 'angle') else 0.0

                # Extract layer
                layer = fp.layer if hasattr(fp, 'layer') else 'F.Cu'

                # Calculate bounding box
                try:
                    bbox = cls.extract_footprint_bbox(fp)
                except ValueError:
                    # If no pads, create small placeholder bbox
                    bbox = BoundingBox.from_center_size(position, 1.0, 1.0)

                # Extract pad information
                pads = []
                for pad in fp.pads:
                    pad_info = {
                        'number': pad.number if hasattr(pad, 'number') else '',
                        'type': pad.type if hasattr(pad, 'type') else '',
                        'shape': pad.shape if hasattr(pad, 'shape') else '',
                        'size': (pad.size.X, pad.size.Y) if pad.size else (0, 0),
                        'position': (pad.position.X, pad.position.Y),
                    }
                    pads.append(pad_info)

                parsed_fp = ParsedFootprint(
                    reference=fp.entryName if hasattr(fp, 'entryName') else 'Unknown',
                    footprint_name=fp.libraryNickname if hasattr(fp, 'libraryNickname') else '',
                    position=position,
                    rotation=rotation,
                    layer=layer,
                    bbox=bbox,
                    pad_count=len(fp.pads),
                    pads=pads,
                    library=fp.libraryNickname if hasattr(fp, 'libraryNickname') else None,
                )

                parsed.append(parsed_fp)

            except Exception as e:
                print(f"Warning: Failed to parse footprint: {e}")
                continue

        return parsed

    @classmethod
    def parse_pcb_full(cls, file_path: Path) -> ParsedPCB:
        """
        Parse a complete PCB file with all information.

        Args:
            file_path: Path to .kicad_pcb file

        Returns:
            ParsedPCB object with all extracted information
        """
        board = cls.load_pcb(file_path)

        # Parse footprints
        footprints = cls.parse_pcb_footprints(board)

        # Get layer information
        layers = []
        if hasattr(board, 'layers') and board.layers:
            # Check if layers is a list or has a layers attribute
            if isinstance(board.layers, list):
                layers = [layer.name if hasattr(layer, 'name') else str(layer) for layer in board.layers]
            elif hasattr(board.layers, 'layers'):
                layers = [layer.name if hasattr(layer, 'name') else str(layer) for layer in board.layers.layers]

        layer_count = len(layers)

        # Get PCB thickness
        thickness = cls.get_pcb_thickness(board)

        # Check for edge cuts
        has_edge_cuts = False
        if hasattr(board, 'graphicItems') and board.graphicItems:
            for item in board.graphicItems:
                if hasattr(item, 'layer') and item.layer == 'Edge.Cuts':
                    has_edge_cuts = True
                    break

        # Calculate board bounding box from footprints
        board_bbox = None
        if footprints:
            all_points = []
            for fp in footprints:
                all_points.extend(fp.bbox.corners)
            board_bbox = BoundingBox.from_points(all_points)

        return ParsedPCB(
            file_path=file_path,
            thickness=thickness,
            footprints=footprints,
            layer_count=layer_count,
            layers=layers,
            board_bbox=board_bbox,
            has_edge_cuts=has_edge_cuts,
        )

    @staticmethod
    def get_layer_name(layer_id: str) -> str:
        """
        Convert KiCad layer ID to readable name.

        Args:
            layer_id: Layer identifier (e.g., 'F.Cu', 'B.Cu')

        Returns:
            Human-readable layer name
        """
        layer_map = {
            'F.Cu': 'Front Copper',
            'B.Cu': 'Back Copper',
            'F.SilkS': 'Front Silkscreen',
            'B.SilkS': 'Back Silkscreen',
            'F.Mask': 'Front Soldermask',
            'B.Mask': 'Back Soldermask',
            'F.Paste': 'Front Paste',
            'B.Paste': 'Back Paste',
            'Edge.Cuts': 'Board Outline',
            'F.CrtYd': 'Front Courtyard',
            'B.CrtYd': 'Back Courtyard',
            'F.Fab': 'Front Fabrication',
            'B.Fab': 'Back Fabrication',
        }
        return layer_map.get(layer_id, layer_id)
