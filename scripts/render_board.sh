#!/bin/bash
# Render PCB board using KiCad Analyzer
# Usage: ./render_board.sh [pcb_file] [width]
#   pcb_file: Path to .kicad_pcb file (default: layouts/main/main.kicad_pcb)
#   width:    Image width in pixels (default: 3840 for 4K)
#
# Output structure:
#   build/renders/<iso timestamp>/
#     - 3d/   - 3D renders (PNG)
#     - svg/  - SVG exports
#     - png/  - PNGs converted from SVGs
#
# Requires: KiCad CLI (8.0+) and Inkscape for PNG conversion

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON="$SCRIPT_DIR/../.venv/bin/python"
DEFAULT_PCB="$SCRIPT_DIR/../layouts/main/main.kicad_pcb"
DEFAULT_WIDTH=3840

PCB_FILE="${1:-$DEFAULT_PCB}"
WIDTH="${2:-$DEFAULT_WIDTH}"

# Check for Inkscape
check_inkscape() {
    # Check common locations
    if command -v inkscape &> /dev/null; then
        echo "Inkscape found: $(command -v inkscape)"
        return 0
    fi

    # Check Windows paths (in case running under WSL or Git Bash)
    local windows_paths=(
        "/c/Program Files/Inkscape/bin/inkscape.exe"
        "/mnt/c/Program Files/Inkscape/bin/inkscape.exe"
        "$HOME/AppData/Local/Programs/Inkscape/bin/inkscape.exe"
    )

    for path in "${windows_paths[@]}"; do
        if [ -f "$path" ]; then
            echo "Inkscape found: $path"
            return 0
        fi
    done

    return 1
}

echo "========================================"
echo "KiCad PCB Render Script"
echo "========================================"
echo ""

# Check for Inkscape
echo "Checking for Inkscape..."
if ! check_inkscape; then
    echo ""
    echo "ERROR: Inkscape not found!"
    echo ""
    echo "Inkscape is required for converting SVG renders to PNG."
    echo ""
    echo "To install Inkscape:"
    echo "  - Windows: winget install Inkscape.Inkscape"
    echo "  - macOS:   brew install inkscape"
    echo "  - Linux:   sudo apt install inkscape"
    echo ""
    echo "After installation, re-run this script."
    exit 1
fi
echo ""

# Check for Python venv
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Python virtual environment not found at: $VENV_PYTHON"
    echo "Please create and activate the virtual environment first."
    exit 1
fi

# Check for PCB file
if [ ! -f "$PCB_FILE" ]; then
    echo "ERROR: PCB file not found: $PCB_FILE"
    echo ""
    echo "Usage: ./render_board.sh [pcb_file] [width]"
    echo "  pcb_file: Path to .kicad_pcb file"
    echo "  width:    Image width in pixels (default: 3840 for 4K)"
    exit 1
fi

echo "Rendering board: $PCB_FILE"
echo "Resolution: ${WIDTH}px"
echo ""

# Run the render command with PNG format
# This will:
# - Export SVGs to svg/ folder
# - Convert SVGs to PNGs in png/ folder using Inkscape
# - Render 3D views to 3d/ folder
"$VENV_PYTHON" kicad-analyzer.py render all --pcb "$PCB_FILE" --format png --width "$WIDTH"

echo ""
echo "Render complete!"
