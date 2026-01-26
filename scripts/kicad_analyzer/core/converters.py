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

# Try to import PIL for checkerboard background
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


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

    @staticmethod
    def _create_checkerboard(width: int, height: int, square_size: int = 16) -> "Image.Image":
        """
        Create a checkerboard pattern image.

        Args:
            width: Image width in pixels.
            height: Image height in pixels.
            square_size: Size of each checkerboard square in pixels.

        Returns:
            PIL Image with checkerboard pattern.
        """
        if not HAS_PIL:
            raise ImportError("PIL/Pillow required for checkerboard background")

        # Very dark colors for subtle checkerboard
        color1 = (15, 15, 15)    # #0f0f0f
        color2 = (25, 25, 25)    # #191919

        img = Image.new("RGB", (width, height), color1)
        pixels = img.load()

        for y in range(height):
            for x in range(width):
                if ((x // square_size) + (y // square_size)) % 2 == 1:
                    pixels[x, y] = color2

        return img

    def _apply_checkerboard_background(self, png_path: Path, square_size: int = 16) -> bool:
        """
        Apply checkerboard background to an existing PNG with transparency.

        Args:
            png_path: Path to PNG file (will be modified in place).
            square_size: Size of checkerboard squares.

        Returns:
            True if successful, False otherwise.
        """
        if not HAS_PIL:
            return False

        try:
            # Open the PNG with transparency
            foreground = Image.open(png_path).convert("RGBA")
            width, height = foreground.size

            # Create checkerboard background
            background = self._create_checkerboard(width, height, square_size).convert("RGBA")

            # Composite foreground onto checkerboard
            composite = Image.alpha_composite(background, foreground)

            # Save as RGB (no transparency needed now)
            composite.convert("RGB").save(png_path, "PNG")
            return True
        except Exception:
            return False

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
        background: str = "checkerboard",
    ) -> Tuple[bool, Optional[str]]:
        """
        Convert SVG to PNG.

        Tries multiple backends in order until one succeeds.

        Args:
            svg_path: Path to input SVG file.
            png_path: Path to output PNG file.
            width: Target width in pixels.
            dpi: DPI for rasterization.
            background: Background - "checkerboard", "transparent", or hex color.

        Returns:
            Tuple of (success, error_message).
        """
        # Ensure output directory exists
        png_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine if we need checkerboard post-processing
        use_checkerboard = background.lower() == "checkerboard"
        use_transparent = background.lower() == "transparent"

        # For checkerboard, first render with transparent background
        render_bg = "transparent" if use_checkerboard else background
        render_bg_opacity = "0" if (use_checkerboard or use_transparent) else "1.0"

        converted = False

        # Method 1: cairosvg
        if not converted:
            try:
                import cairosvg

                bg_color = None if (use_checkerboard or use_transparent) else background
                cairosvg.svg2png(
                    url=str(svg_path),
                    write_to=str(png_path),
                    output_width=width,
                    background_color=bg_color,
                )
                converted = True
            except ImportError:
                pass
            except OSError:
                pass
            except Exception:
                pass

        # Method 2: Inkscape
        if not converted:
            inkscape_path = self._find_inkscape()
            if inkscape_path:
                try:
                    cmd = [
                        str(inkscape_path),
                        str(svg_path),
                        "--export-type=png",
                        f"--export-filename={png_path}",
                        f"--export-width={width}",
                    ]
                    if use_checkerboard or use_transparent:
                        # Export with transparent background
                        cmd.extend(["--export-background-opacity=0"])
                    else:
                        cmd.extend([
                            f"--export-background={background}",
                            "--export-background-opacity=1.0",
                        ])

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=60,
                    )
                    if result.returncode == 0 and png_path.exists():
                        converted = True
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass

        # Method 3: ImageMagick
        if not converted:
            try:
                cmd = [
                    "magick",
                    "convert",
                    "-density",
                    str(dpi),
                ]
                if not (use_checkerboard or use_transparent):
                    cmd.extend(["-background", background, "-flatten"])

                cmd.extend([
                    str(svg_path),
                    "-resize",
                    f"{width}x",
                    str(png_path),
                ])

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=60,
                )
                if result.returncode == 0 and png_path.exists():
                    converted = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        if not converted:
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

        # Apply checkerboard background if requested
        if use_checkerboard and png_path.exists():
            if HAS_PIL:
                self._apply_checkerboard_background(png_path)
            else:
                # Fallback: just leave transparent or return warning
                pass

        return True, None
