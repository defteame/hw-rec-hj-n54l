"""
Image conversion utilities for KiCad Analyzer.

This module provides SVG to PNG conversion using various backends:
- cairosvg (Python library)
- Inkscape CLI
- ImageMagick
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


class ImageConverter:
    """
    SVG to PNG converter with multiple backend support.

    Tries conversion methods in order of preference:
    1. cairosvg (fastest, Python-native)
    2. Inkscape CLI (high quality)
    3. ImageMagick (widely available)

    Attributes:
        additional_inkscape_paths: Extra paths to search for Inkscape.
    """

    # Common Inkscape installation paths
    _INKSCAPE_PATHS = [
        Path(r"C:\Program Files\Inkscape\bin\inkscape.exe"),
        Path(r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe"),
        Path.home() / "AppData" / "Local" / "Programs" / "Inkscape" / "bin" / "inkscape.exe",
        Path("/usr/bin/inkscape"),
        Path("/usr/local/bin/inkscape"),
        Path("/Applications/Inkscape.app/Contents/MacOS/inkscape"),
    ]

    def __init__(self, additional_inkscape_paths: Optional[List[Path]] = None) -> None:
        """
        Initialize the converter.

        Args:
            additional_inkscape_paths: Extra paths to search for Inkscape.
        """
        self._additional_paths = additional_inkscape_paths or []
        self._inkscape_path: Optional[Path] = None

    def _find_inkscape(self) -> Optional[Path]:
        """
        Find Inkscape executable.

        Returns:
            Path to inkscape if found, None otherwise.
        """
        if self._inkscape_path is not None:
            return self._inkscape_path

        # Check additional paths first
        for path in self._additional_paths:
            if path.exists():
                self._inkscape_path = path
                return path

        # Check standard paths
        for path in self._INKSCAPE_PATHS:
            if path.exists():
                self._inkscape_path = path
                return path

        # Try to find in PATH
        try:
            cmd = "where" if sys.platform == "win32" else "which"
            result = subprocess.run(
                [cmd, "inkscape"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self._inkscape_path = Path(result.stdout.strip().split("\n")[0])
                return self._inkscape_path
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return None

    def check_available(self) -> Tuple[bool, str, List[str]]:
        """
        Check if any conversion tool is available.

        Returns:
            Tuple of (available, tool_name, installation_guidance).
        """
        guidance: List[str] = []

        # Check cairosvg
        try:
            import cairosvg  # noqa: F401

            return True, "cairosvg", []
        except ImportError:
            guidance.append("  - cairosvg: pip install cairosvg (requires Cairo library)")
        except OSError as e:
            if "cairo" in str(e).lower():
                guidance.append("  - cairosvg: Install Cairo library (GTK runtime on Windows)")

        # Check Inkscape
        inkscape_path = self._find_inkscape()
        if inkscape_path:
            try:
                result = subprocess.run(
                    [str(inkscape_path), "--version"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return True, f"inkscape ({inkscape_path})", []
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        guidance.append("  - Inkscape: https://inkscape.org/release/")

        # Check ImageMagick
        try:
            result = subprocess.run(
                ["magick", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True, "imagemagick", []
        except (FileNotFoundError, subprocess.TimeoutExpired):
            guidance.append("  - ImageMagick: https://imagemagick.org/script/download.php")

        return False, "", guidance

    def convert(
        self,
        svg_path: Path,
        png_path: Path,
        *,
        width: int = 1200,
        dpi: int = 300,
    ) -> Tuple[bool, Optional[str]]:
        """
        Convert SVG to PNG.

        Tries multiple backends in order until one succeeds.

        Args:
            svg_path: Path to input SVG file.
            png_path: Path to output PNG file.
            width: Target width in pixels.
            dpi: DPI for rasterization.

        Returns:
            Tuple of (success, error_message).
        """
        # Ensure output directory exists
        png_path.parent.mkdir(parents=True, exist_ok=True)

        # Method 1: cairosvg
        try:
            import cairosvg

            cairosvg.svg2png(
                url=str(svg_path),
                write_to=str(png_path),
                output_width=width,
            )
            return True, None
        except ImportError:
            pass
        except OSError:
            pass
        except Exception:
            pass

        # Method 2: Inkscape
        inkscape_path = self._find_inkscape()
        if inkscape_path:
            try:
                result = subprocess.run(
                    [
                        str(inkscape_path),
                        str(svg_path),
                        "--export-type=png",
                        f"--export-filename={png_path}",
                        f"--export-width={width}",
                    ],
                    capture_output=True,
                    timeout=60,
                )
                if result.returncode == 0 and png_path.exists():
                    return True, None
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        # Method 3: ImageMagick
        try:
            result = subprocess.run(
                [
                    "magick",
                    "convert",
                    "-density",
                    str(dpi),
                    str(svg_path),
                    "-resize",
                    f"{width}x",
                    str(png_path),
                ],
                capture_output=True,
                timeout=60,
            )
            if result.returncode == 0 and png_path.exists():
                return True, None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        error_msg = (
            "PNG conversion failed. No conversion tool available.\n"
            "Install ONE of the following:\n"
            "  - cairosvg: pip install cairosvg (+ Cairo library)\n"
            "  - Inkscape: https://inkscape.org/release/\n"
            "  - ImageMagick: https://imagemagick.org/script/download.php\n"
            "\n"
            "On Windows, the easiest option is Inkscape."
        )
        return False, error_msg
