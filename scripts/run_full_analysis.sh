#!/bin/bash
# Full KiCad PCB Analysis Script (Unix/macOS/Git Bash)
# Runs: DRC, 2D Renders, 3D Renders
# Usage: ./run_full_analysis.sh [pcb_file] [width]
#   pcb_file: Path to .kicad_pcb file (default: layouts/main/main.kicad_pcb)
#   width:    Image width in pixels (default: 3840 for 4K)
#
# Output structure:
#   build/kicad_analyzer/<iso timestamp>/
#     - drc/   - DRC reports
#     - renders/
#       - 3d/   - 3D renders (PNG)
#       - svg/  - SVG exports
#       - png/  - PNGs converted from SVGs
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

# Check for KiCad CLI
check_kicad_cli() {
    if command -v kicad-cli &> /dev/null; then
        echo "KiCad CLI found: $(command -v kicad-cli)"
        return 0
    fi

    # Check Windows paths (in case running under WSL or Git Bash)
    local windows_paths=(
        "/c/Program Files/KiCad/9.0/bin/kicad-cli.exe"
        "/mnt/c/Program Files/KiCad/9.0/bin/kicad-cli.exe"
        "/c/Program Files/KiCad/8.0/bin/kicad-cli.exe"
        "/mnt/c/Program Files/KiCad/8.0/bin/kicad-cli.exe"
        "$HOME/AppData/Local/Programs/KiCad/9.0/bin/kicad-cli.exe"
        "$HOME/AppData/Local/Programs/KiCad/8.0/bin/kicad-cli.exe"
    )

    for path in "${windows_paths[@]}"; do
        if [ -f "$path" ]; then
            echo "KiCad CLI found: $path"
            return 0
        fi
    done

    return 1
}

# Check for Inkscape
check_inkscape() {
    if command -v inkscape &> /dev/null; then
        echo "Inkscape found: $(command -v inkscape)"
        return 0
    fi

    # Check Windows paths
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
echo "KiCad Full Analysis Script"
echo "========================================"
echo ""

# Check for KiCad CLI
echo "Checking for KiCad CLI..."
if ! check_kicad_cli; then
    echo ""
    echo "ERROR: KiCad CLI not found!"
    echo ""
    echo "Please install KiCad 8.0+ from https://www.kicad.org/"
    exit 1
fi
echo ""

# Check for Inkscape
echo "Checking for Inkscape..."
if ! check_inkscape; then
    echo ""
    echo "WARNING: Inkscape not found - PNG conversion may fail"
    echo ""
    echo "To install Inkscape:"
    echo "  - Windows: winget install Inkscape.Inkscape"
    echo "  - macOS:   brew install inkscape"
    echo "  - Linux:   sudo apt install inkscape"
    echo ""
fi
echo ""

# Check for Python venv
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Python virtual environment not found at: $VENV_PYTHON"
    echo "Please create and activate the virtual environment first."
    exit 1
fi
echo "Python found."
echo ""

# Check for PCB file
if [ ! -f "$PCB_FILE" ]; then
    echo "ERROR: PCB file not found: $PCB_FILE"
    echo ""
    echo "Usage: ./run_full_analysis.sh [pcb_file] [width]"
    echo "  pcb_file: Path to .kicad_pcb file"
    echo "  width:    Image width in pixels (default: 3840 for 4K)"
    exit 1
fi
echo "PCB file found."
echo ""

echo "Analysis Target: $PCB_FILE"
echo "Render Resolution: ${WIDTH}px"
echo ""

echo "Running full analysis (DRC + Renders)..."
echo ""

# Run full analysis (DRC + renders in single folder)
set +e
"$VENV_PYTHON" kicad-analyzer.py full run --pcb "$PCB_FILE" --format png --width "$WIDTH"
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "WARNING: Analysis completed with DRC errors"
fi

echo ""
echo "========================================"
echo "Analysis Complete!"
echo "========================================"
echo ""
echo "Output location: $(dirname "$SCRIPT_DIR")/build/kicad_analyzer/"
echo ""
echo "Run 'python kicad-analyzer.py latest' to see the latest results."
echo ""
