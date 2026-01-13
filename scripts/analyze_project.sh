#!/bin/bash
# Example script to analyze the hw-rec-hj-n54l project (Linux/Mac)
#
# Usage:
#   ./analyze_project.sh          - Quick analysis
#   ./analyze_project.sh full     - Full comprehensive analysis

set -e  # Exit on error

echo "======================================"
echo "KiCad Analyzer - Project Analysis"
echo "======================================"
echo ""

# Configuration
PCB_FILE="../layouts/main/main.kicad_pcb"
BOARD_RADIUS=9.3
CLEARANCE=0.3

# Check if files exist
if [ ! -f "$PCB_FILE" ]; then
    echo "ERROR: PCB file not found: $PCB_FILE"
    exit 1
fi

echo "Analyzing: $PCB_FILE"
echo ""

# Check if full analysis requested
if [ "$1" = "full" ]; then
    echo "Running comprehensive placement analysis..."
    echo ""
    python kicad-analyzer.py analyze placement "$PCB_FILE"
    echo ""
    echo "======== View Latest Results ========"
    python kicad-analyzer.py latest
    exit 0
fi

# Quick analysis (default)
# PCB Information
echo "======== PCB Information ========"
python kicad-analyzer.py pcb info "$PCB_FILE"
echo ""

# Check circular fit
echo "======== Circular Fit Check (R=${BOARD_RADIUS}mm) ========"
python kicad-analyzer.py pcb circular-fit "$PCB_FILE" --radius $BOARD_RADIUS
echo ""

# Check collisions
echo "======== Collision Detection (Clearance=${CLEARANCE}mm) ========"
python kicad-analyzer.py pcb collisions "$PCB_FILE" --clearance $CLEARANCE
echo ""

# List largest components
echo "======== Largest Components (Top 10) ========"
python kicad-analyzer.py pcb list "$PCB_FILE" --sort area | head -15
echo ""

echo "======================================"
echo "Analysis complete!"
echo "======================================"
echo ""
echo "For comprehensive analysis with placement, run:"
echo "  ./analyze_project.sh full"
echo ""
