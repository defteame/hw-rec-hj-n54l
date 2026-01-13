#!/bin/bash
# Example script to analyze the hw-rec-hj-n54l project

set -e  # Exit on error

echo "======================================"
echo "KiCad Analyzer - Project Analysis"
echo "======================================"
echo ""

# Configuration
PCB_FILE="../layouts/main/main.kicad_pcb"
PLACEMENT_FILE="../planv7/placement_main_v1.csv"
BOARD_RADIUS=9.3
CLEARANCE=0.3

# Check if files exist
if [ ! -f "$PCB_FILE" ]; then
    echo "ERROR: PCB file not found: $PCB_FILE"
    exit 1
fi

echo "Analyzing: $PCB_FILE"
echo ""

# PCB Information
echo "======== PCB Information ========"
python kicad-analyzer.py pcb info "$PCB_FILE"
echo ""

# List components
echo "======== Component List ========"
python kicad-analyzer.py pcb list "$PCB_FILE" --sort area
echo ""

# Check circular fit
echo "======== Circular Fit Check (R=${BOARD_RADIUS}mm) ========"
python kicad-analyzer.py pcb circular-fit "$PCB_FILE" --radius $BOARD_RADIUS
echo ""

# Check collisions
echo "======== Collision Detection (Clearance=${CLEARANCE}mm) ========"
python kicad-analyzer.py pcb collisions "$PCB_FILE" --clearance $CLEARANCE
echo ""

# Layer distribution
echo "======== Layer Distribution ========"
python kicad-analyzer.py pcb layers "$PCB_FILE"
echo ""

# Validate placement if file exists
if [ -f "$PLACEMENT_FILE" ]; then
    echo "======== Placement Validation ========"
    python kicad-analyzer.py placement validate "$PLACEMENT_FILE" --circular --radius $BOARD_RADIUS
    echo ""
else
    echo "Note: Placement file not found: $PLACEMENT_FILE"
    echo ""
fi

echo "======================================"
echo "Analysis complete!"
echo "======================================"
