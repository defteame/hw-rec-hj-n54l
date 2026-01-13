"""
Validation utilities for input checking and error handling.

This module provides functions for validating file paths, formats,
and other user inputs before processing.
"""

from pathlib import Path
from typing import Optional
import csv


def validate_file_exists(file_path: Path, extension: Optional[str] = None) -> None:
    """
    Validate that a file exists and optionally has correct extension.

    Args:
        file_path: Path to check
        extension: Expected file extension (e.g., '.kicad_pcb')

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file has wrong extension
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if extension and file_path.suffix != extension:
        raise ValueError(
            f"Expected {extension} file, got {file_path.suffix}"
        )


def validate_pcb_file(file_path: Path) -> None:
    """
    Validate that a path is a valid KiCad PCB file.

    Args:
        file_path: Path to validate

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file has wrong extension
    """
    validate_file_exists(file_path, '.kicad_pcb')


def validate_footprint_file(file_path: Path) -> None:
    """
    Validate that a path is a valid KiCad footprint file.

    Args:
        file_path: Path to validate

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file has wrong extension
    """
    validate_file_exists(file_path, '.kicad_mod')


def validate_placement_csv(file_path: Path) -> None:
    """
    Validate that a CSV file contains required placement columns.

    Args:
        file_path: Path to CSV file

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If CSV format is invalid
    """
    validate_file_exists(file_path, '.csv')

    required_columns = {'Ref', 'X_mm', 'Y_mm', 'Rotation_deg', 'Side'}

    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            headers = set(reader.fieldnames or [])

            missing = required_columns - headers
            if missing:
                raise ValueError(
                    f"CSV missing required columns: {', '.join(missing)}"
                )
    except csv.Error as e:
        raise ValueError(f"Invalid CSV format: {e}") from e


def validate_positive_number(value: float, name: str) -> None:
    """
    Validate that a number is positive.

    Args:
        value: Number to check
        name: Parameter name for error message

    Raises:
        ValueError: If value is not positive
    """
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def validate_clearance(clearance: float) -> None:
    """
    Validate clearance value.

    Args:
        clearance: Clearance in mm

    Raises:
        ValueError: If clearance is negative or unreasonably large
    """
    if clearance < 0:
        raise ValueError(f"Clearance cannot be negative: {clearance}")

    if clearance > 100:
        raise ValueError(
            f"Clearance seems unreasonably large: {clearance}mm. "
            "Please check your units."
        )


def validate_board_radius(radius: float) -> None:
    """
    Validate board radius value.

    Args:
        radius: Radius in mm

    Raises:
        ValueError: If radius is invalid
    """
    validate_positive_number(radius, "Board radius")

    if radius > 500:
        raise ValueError(
            f"Board radius seems unreasonably large: {radius}mm. "
            "Please check your units."
        )
