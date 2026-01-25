#!/bin/bash
# Render PCB board using KiCad Analyzer
# Usage: ./render_board.sh [optional: path to pcb file]
#
# Note: 2D renders use SVG format by default (PNG requires Inkscape/ImageMagick)
#       3D renders are always PNG

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON="$SCRIPT_DIR/../.venv/bin/python"
DEFAULT_PCB="$SCRIPT_DIR/../layouts/main/main.kicad_pcb"
PCB_FILE="${1:-$DEFAULT_PCB}"

echo "Rendering board: $PCB_FILE"
"$VENV_PYTHON" kicad-analyzer.py render all --pcb "$PCB_FILE" --format svg
