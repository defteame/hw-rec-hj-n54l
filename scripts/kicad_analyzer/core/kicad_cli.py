"""
KiCad CLI interface module.

This module provides a Python interface to the KiCad command-line tools,
specifically kicad-cli for PCB rendering and export operations.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


class KiCadCLI:
    """
    Interface to KiCad command-line tools.

    This class wraps the kicad-cli executable and provides methods
    for exporting PCB renders in various formats.

    Attributes:
        pcb_file: Path to the PCB file to work with.
        is_available: Whether kicad-cli was found on the system.
        cli_path: Path to the kicad-cli executable (if found).
    """

    # Common installation paths for kicad-cli
    _SEARCH_PATHS = [
        # Windows user-local install (most common)
        Path.home() / "AppData" / "Local" / "Programs" / "KiCad" / "9.0" / "bin" / "kicad-cli.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "KiCad" / "8.0" / "bin" / "kicad-cli.exe",
        # Windows system-wide installs
        Path(r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe"),
        Path(r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe"),
        Path(r"C:\Program Files (x86)\KiCad\9.0\bin\kicad-cli.exe"),
        # Linux
        Path("/usr/bin/kicad-cli"),
        Path("/usr/local/bin/kicad-cli"),
        # macOS
        Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"),
    ]

    def __init__(
        self,
        pcb_file: Path,
        additional_cli_paths: Optional[List[Path]] = None,
    ) -> None:
        """
        Initialize the KiCad CLI interface.

        Args:
            pcb_file: Path to the PCB file to work with.
            additional_cli_paths: Extra paths to search for kicad-cli.
        """
        self.pcb_file = pcb_file
        self._additional_paths = additional_cli_paths or []
        self._cli_path = self._find_kicad_cli()

    @property
    def is_available(self) -> bool:
        """Check if KiCad CLI is available on the system."""
        return self._cli_path is not None

    @property
    def cli_path(self) -> Optional[Path]:
        """Path to the kicad-cli executable, or None if not found."""
        return self._cli_path

    def _find_kicad_cli(self) -> Optional[Path]:
        """
        Search for the kicad-cli executable.

        Returns:
            Path to kicad-cli if found, None otherwise.
        """
        # Check additional paths first
        for path in self._additional_paths:
            if path.exists():
                return path

        # Check predefined paths
        for path in self._SEARCH_PATHS:
            if path.exists():
                return path

        # Try to find in PATH
        try:
            cmd = "where" if sys.platform == "win32" else "which"
            result = subprocess.run(
                [cmd, "kicad-cli"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return Path(result.stdout.strip().split("\n")[0])
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return None

    def _run_command(
        self,
        args: List[str],
        timeout: int = 60,
    ) -> Tuple[bool, str, str]:
        """
        Run a kicad-cli command.

        Args:
            args: Command arguments (without the kicad-cli path).
            timeout: Command timeout in seconds.

        Returns:
            Tuple of (success, stdout, stderr).
        """
        if not self.is_available:
            return False, "", "kicad-cli not found"

        cmd = [str(self._cli_path)] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return (
                result.returncode == 0,
                result.stdout,
                result.stderr,
            )
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    def export_svg(
        self,
        output_path: Path,
        layers: List[str],
        *,
        exclude_drawing_sheet: bool = True,
        fit_to_board: bool = True,
    ) -> bool:
        """
        Export PCB as SVG using kicad-cli.

        Args:
            output_path: Output file path (.svg).
            layers: List of layer names to include.
            exclude_drawing_sheet: Whether to exclude the drawing sheet border.
            fit_to_board: Whether to fit/crop the output to the board outline.

        Returns:
            True if export succeeded, False otherwise.
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        args = [
            "pcb",
            "export",
            "svg",
            "--output",
            str(output_path),
            "--layers",
            ",".join(layers),
        ]

        if exclude_drawing_sheet:
            args.append("--exclude-drawing-sheet")

        if fit_to_board:
            # page-size-mode 2 = board area only
            args.extend(["--page-size-mode", "2"])

        args.append(str(self.pcb_file))

        success, _, _ = self._run_command(args)
        return success

    def render_3d(
        self,
        output_path: Path,
        *,
        side: Optional[str] = None,
        rotate: Optional[str] = None,
        width: int = 1600,
        height: int = 900,
        quality: str = "high",
        background: str = "transparent",
        perspective: bool = True,
        floor: bool = False,
    ) -> bool:
        """
        Render 3D view of the PCB to PNG/JPEG.

        Args:
            output_path: Output file path (.png or .jpg).
            side: View side - "top", "bottom", "front", "back", "left", "right".
            rotate: Custom rotation as "X,Y,Z" angles in degrees.
            width: Image width in pixels.
            height: Image height in pixels.
            quality: Render quality - "basic", "high", "user".
            background: Background type - "default", "transparent", "opaque".
            perspective: Use perspective projection.
            floor: Enable floor and shadows.

        Returns:
            True if render succeeded, False otherwise.
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        args = [
            "pcb",
            "render",
            "--output",
            str(output_path),
            "--width",
            str(width),
            "--height",
            str(height),
            "--quality",
            quality,
        ]

        # Handle view angle - rotate takes precedence
        if rotate:
            args.extend(["--rotate", rotate])
        elif side:
            args.extend(["--side", side])
        else:
            args.extend(["--side", "top"])

        if background:
            args.extend(["--background", background])

        if perspective:
            args.append("--perspective")

        if floor:
            args.append("--floor")

        args.append(str(self.pcb_file))

        success, _, _ = self._run_command(args, timeout=120)
        return success

    def get_version(self) -> Optional[str]:
        """
        Get the KiCad CLI version.

        Returns:
            Version string or None if unavailable.
        """
        if not self.is_available:
            return None

        success, stdout, _ = self._run_command(["--version"], timeout=5)
        if success:
            return stdout.strip()
        return None

    def run_drc(
        self,
        output_path: Path,
        *,
        format: str = "json",
        all_track_errors: bool = True,
        schematic_parity: bool = False,
        units: str = "mm",
        severity_all: bool = True,
        exit_code_violations: bool = True,
    ) -> Tuple[bool, str, str]:
        """
        Run Design Rule Check (DRC) on the PCB.

        Args:
            output_path: Output file path for the DRC report.
            format: Report format - "report" (text) or "json".
            all_track_errors: Report all errors for each track.
            schematic_parity: Test for parity between PCB and schematic.
            units: Measurement units - "mm", "mils", or "in".
            severity_all: Include all severity levels.
            exit_code_violations: Return non-zero exit code if violations found.

        Returns:
            Tuple of (success, stdout, stderr).
            Note: If exit_code_violations is True, success will be False
            if there are DRC violations.
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        args = [
            "pcb",
            "drc",
            "--output",
            str(output_path),
            "--format",
            format,
            "--units",
            units,
        ]

        if all_track_errors:
            args.append("--all-track-errors")

        if schematic_parity:
            args.append("--schematic-parity")

        if severity_all:
            args.append("--severity-all")

        if exit_code_violations:
            args.append("--exit-code-violations")

        args.append(str(self.pcb_file))

        return self._run_command(args, timeout=120)
