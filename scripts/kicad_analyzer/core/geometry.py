"""
Geometric primitives and calculations for KiCad footprint analysis.

This module provides classes and functions for working with 2D geometry,
including points, bounding boxes, and rotation transformations.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import math


@dataclass
class Point:
    """A 2D point with x and y coordinates in millimeters."""

    x: float
    y: float

    def rotate(self, angle_deg: float, origin: Optional['Point'] = None) -> 'Point':
        """
        Rotate point around origin by given angle in degrees.

        Args:
            angle_deg: Rotation angle in degrees (counter-clockwise)
            origin: Point to rotate around (defaults to 0,0)

        Returns:
            New rotated Point
        """
        if origin is None:
            origin = Point(0, 0)

        # Translate to origin
        dx = self.x - origin.x
        dy = self.y - origin.y

        # Rotate
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        x_rot = dx * cos_a - dy * sin_a
        y_rot = dx * sin_a + dy * cos_a

        # Translate back
        return Point(x_rot + origin.x, y_rot + origin.y)

    def distance_to(self, other: 'Point') -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def __str__(self) -> str:
        return f"({self.x:.3f}, {self.y:.3f})"


@dataclass
class BoundingBox:
    """
    Axis-aligned bounding box in millimeters.

    Represents the rectangular bounds of a footprint or component,
    defined by minimum and maximum x and y coordinates.
    """

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @classmethod
    def from_points(cls, points: List[Point]) -> 'BoundingBox':
        """
        Create bounding box from a list of points.

        Args:
            points: List of Point objects

        Returns:
            BoundingBox enclosing all points

        Raises:
            ValueError: If points list is empty
        """
        if not points:
            raise ValueError("Cannot create bounding box from empty point list")

        xs = [p.x for p in points]
        ys = [p.y for p in points]

        return cls(
            min_x=min(xs),
            min_y=min(ys),
            max_x=max(xs),
            max_y=max(ys)
        )

    @classmethod
    def from_center_size(cls, center: Point, width: float, height: float) -> 'BoundingBox':
        """
        Create bounding box from center point and dimensions.

        Args:
            center: Center point of the box
            width: Width in mm
            height: Height in mm

        Returns:
            BoundingBox centered at given point
        """
        half_w = width / 2
        half_h = height / 2

        return cls(
            min_x=center.x - half_w,
            min_y=center.y - half_h,
            max_x=center.x + half_w,
            max_y=center.y + half_h
        )

    @property
    def width(self) -> float:
        """Width of the bounding box in mm."""
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        """Height of the bounding box in mm."""
        return self.max_y - self.min_y

    @property
    def area(self) -> float:
        """Area of the bounding box in mm²."""
        return self.width * self.height

    @property
    def center(self) -> Point:
        """Center point of the bounding box."""
        return Point(
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2
        )

    @property
    def corners(self) -> List[Point]:
        """Get all four corners of the bounding box."""
        return [
            Point(self.min_x, self.min_y),  # Bottom-left
            Point(self.max_x, self.min_y),  # Bottom-right
            Point(self.max_x, self.max_y),  # Top-right
            Point(self.min_x, self.max_y),  # Top-left
        ]

    def contains_point(self, point: Point) -> bool:
        """Check if a point is inside this bounding box."""
        return (self.min_x <= point.x <= self.max_x and
                self.min_y <= point.y <= self.max_y)

    def intersects(self, other: 'BoundingBox') -> bool:
        """Check if this bounding box intersects with another."""
        return not (self.max_x < other.min_x or
                   self.min_x > other.max_x or
                   self.max_y < other.min_y or
                   self.min_y > other.max_y)

    def intersection_area(self, other: 'BoundingBox') -> float:
        """
        Calculate the area of intersection with another bounding box.

        Returns:
            Intersection area in mm², or 0 if no intersection
        """
        if not self.intersects(other):
            return 0.0

        x_overlap = min(self.max_x, other.max_x) - max(self.min_x, other.min_x)
        y_overlap = min(self.max_y, other.max_y) - max(self.min_y, other.min_y)

        return x_overlap * y_overlap

    def expand(self, margin: float) -> 'BoundingBox':
        """
        Expand bounding box by adding margin on all sides.

        Args:
            margin: Distance to expand in mm

        Returns:
            New expanded BoundingBox
        """
        return BoundingBox(
            min_x=self.min_x - margin,
            min_y=self.min_y - margin,
            max_x=self.max_x + margin,
            max_y=self.max_y + margin
        )

    def is_inside_circle(self, center: Point, radius: float) -> bool:
        """
        Check if all corners of this bounding box are inside a circle.

        Args:
            center: Center point of the circle
            radius: Radius of the circle in mm

        Returns:
            True if all corners are inside the circle
        """
        for corner in self.corners:
            if corner.distance_to(center) > radius:
                return False
        return True

    def max_distance_from_point(self, point: Point) -> float:
        """
        Calculate maximum distance from a point to any corner of the box.

        Useful for checking if box fits within a circular area.
        """
        return max(corner.distance_to(point) for corner in self.corners)

    def __str__(self) -> str:
        return (f"BBox[({self.min_x:.3f}, {self.min_y:.3f}) to "
                f"({self.max_x:.3f}, {self.max_y:.3f}), "
                f"{self.width:.3f}×{self.height:.3f}mm]")


def rotate_bbox_around_center(bbox: BoundingBox, angle_deg: float) -> BoundingBox:
    """
    Rotate a bounding box around its center and return axis-aligned bounds.

    This calculates the new axis-aligned bounding box that encloses the
    rotated original box. Useful for checking placement constraints.

    Args:
        bbox: Original bounding box
        angle_deg: Rotation angle in degrees

    Returns:
        New axis-aligned BoundingBox enclosing the rotated box
    """
    center = bbox.center
    rotated_corners = [corner.rotate(angle_deg, center) for corner in bbox.corners]
    return BoundingBox.from_points(rotated_corners)


def check_collision(bbox1: BoundingBox, bbox2: BoundingBox,
                    clearance: float = 0.0) -> bool:
    """
    Check if two bounding boxes collide, considering optional clearance.

    Args:
        bbox1: First bounding box
        bbox2: Second bounding box
        clearance: Minimum required clearance in mm

    Returns:
        True if boxes collide (including clearance violation)
    """
    expanded1 = bbox1.expand(clearance / 2)
    expanded2 = bbox2.expand(clearance / 2)
    return expanded1.intersects(expanded2)


def calculate_centroid(points: List[Point]) -> Point:
    """
    Calculate the centroid (center of mass) of a set of points.

    Args:
        points: List of Point objects

    Returns:
        Point at the centroid

    Raises:
        ValueError: If points list is empty
    """
    if not points:
        raise ValueError("Cannot calculate centroid of empty point list")

    avg_x = sum(p.x for p in points) / len(points)
    avg_y = sum(p.y for p in points) / len(points)

    return Point(avg_x, avg_y)
