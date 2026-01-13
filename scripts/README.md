# KiCad Analyzer

A comprehensive Python CLI toolkit for analyzing KiCad PCB files, footprints, and component placements.

## Features

- **Footprint Analysis**: Inspect footprint files, calculate bounding boxes, analyze pads
- **PCB Analysis**: Analyze complete PCB layouts, check component distribution, validate constraints
- **Collision Detection**: Detect overlapping components and clearance violations
- **Circular Board Validation**: Verify all components fit within circular board outlines
- **Placement Management**: Export, validate, and apply component placements from CSV files
- **Rich Terminal Output**: Beautiful tables and formatted output using Rich library

## Architecture

```
kicad_analyzer/
├── __init__.py              # Package initialization
├── cli.py                   # Main CLI entrypoint
├── commands/                # CLI command implementations
│   ├── footprint.py        # Footprint analysis commands
│   ├── pcb.py              # PCB analysis commands
│   └── placement.py        # Placement management commands
├── core/                    # Core functionality
│   ├── geometry.py         # Geometric primitives (Point, BoundingBox)
│   ├── parser.py           # KiCad file parsing with kiutils
│   └── analyzer.py         # Analysis logic and algorithms
└── utils/                   # Utility functions
    ├── formatting.py       # Output formatting and rich tables
    └── validation.py       # Input validation and error checking
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Install Dependencies

```bash
cd scripts
pip install -r requirements.txt
```

### Verify Installation

```bash
python kicad-analyzer.py --help
```

## Usage

### Quick Start

```bash
# Analyze a PCB file
python kicad-analyzer.py pcb info layouts/main/main.kicad_pcb

# List all footprints
python kicad-analyzer.py pcb list layouts/main/main.kicad_pcb

# Check for collisions
python kicad-analyzer.py pcb collisions layouts/main/main.kicad_pcb --clearance 0.5

# Validate circular board fit
python kicad-analyzer.py pcb circular-fit layouts/main/main.kicad_pcb --radius 9.3
```

## Command Reference

### Global Options

```bash
python kicad-analyzer.py [COMMAND] --help   # Show command-specific help
python kicad-analyzer.py version            # Show version information
```

### Footprint Commands

#### `footprint info` - Display footprint information

```bash
python kicad-analyzer.py footprint info <footprint_file.kicad_mod> [OPTIONS]

Options:
  --verbose, -v    Show detailed pad information
  --json, -j       Output as JSON
```

**Example:**
```bash
python kicad-analyzer.py footprint info parts/HJ_N54L_SIP/footprint.kicad_mod --verbose
```

#### `footprint bbox` - Calculate bounding box

```bash
python kicad-analyzer.py footprint bbox <footprint_file.kicad_mod>
```

Shows minimum/maximum coordinates and overall dimensions.

#### `footprint pads` - List all pads

```bash
python kicad-analyzer.py footprint pads <footprint_file.kicad_mod> [OPTIONS]

Options:
  --type, -t TEXT  Filter by pad type (smd, thru_hole, np_thru_hole)
```

**Example:**
```bash
python kicad-analyzer.py footprint pads parts/MyPart/footprint.kicad_mod --type smd
```

### PCB Commands

#### `pcb info` - Display PCB information

```bash
python kicad-analyzer.py pcb info <pcb_file.kicad_pcb> [OPTIONS]

Options:
  --json, -j       Output as JSON
```

Shows PCB statistics, layer information, component counts, and density.

**Example:**
```bash
python kicad-analyzer.py pcb info layouts/main/main.kicad_pcb
```

#### `pcb list` - List all footprints

```bash
python kicad-analyzer.py pcb list <pcb_file.kicad_pcb> [OPTIONS]

Options:
  --layer, -l TEXT    Filter by layer (F.Cu, B.Cu, etc.)
  --sort, -s TEXT     Sort by: reference, size, area, x, y
```

**Examples:**
```bash
# List all footprints
python kicad-analyzer.py pcb list layouts/main/main.kicad_pcb

# Show only front copper components
python kicad-analyzer.py pcb list layouts/main/main.kicad_pcb --layer F.Cu

# Sort by component area
python kicad-analyzer.py pcb list layouts/main/main.kicad_pcb --sort area
```

#### `pcb collisions` - Check for component collisions

```bash
python kicad-analyzer.py pcb collisions <pcb_file.kicad_pcb> [OPTIONS]

Options:
  --clearance, -c FLOAT   Required clearance in mm (default: 0.0)
  --all, -a               Show all pairs, not just collisions
```

**Example:**
```bash
python kicad-analyzer.py pcb collisions layouts/main/main.kicad_pcb --clearance 0.5
```

#### `pcb circular-fit` - Validate circular board constraints

```bash
python kicad-analyzer.py pcb circular-fit <pcb_file.kicad_pcb> [OPTIONS]

Options:
  --radius, -r FLOAT      Board radius in mm (required)
  --cx FLOAT             Board center X coordinate (default: 0.0)
  --cy FLOAT             Board center Y coordinate (default: 0.0)
  --all, -a              Show all components, not just violations
```

**Example:**
```bash
# Check 18.6mm diameter circular board centered at origin
python kicad-analyzer.py pcb circular-fit layouts/main/main.kicad_pcb --radius 9.3

# Check with custom center point
python kicad-analyzer.py pcb circular-fit layouts/main/main.kicad_pcb -r 10 --cx 5 --cy 5
```

#### `pcb layers` - List PCB layers

```bash
python kicad-analyzer.py pcb layers <pcb_file.kicad_pcb>
```

Shows all layers and component distribution across layers.

### Placement Commands

#### `placement validate` - Validate placement CSV

```bash
python kicad-analyzer.py placement validate <csv_file> [OPTIONS]

Options:
  --circular           Validate for circular board
  --radius, -r FLOAT   Board radius in mm (required with --circular)
  --clearance, -c FLOAT Minimum clearance in mm
```

**Example:**
```bash
python kicad-analyzer.py placement validate planv7/placement_main_v1.csv --circular --radius 9.3
```

#### `placement apply` - Apply placements to PCB

```bash
python kicad-analyzer.py placement apply <pcb_file> <csv_file> [OPTIONS]

Options:
  --output, -o PATH        Output PCB file (default: overwrite input)
  --backup/--no-backup     Create backup (default: true)
  --dry-run                Show changes without applying
```

**Examples:**
```bash
# Apply with backup (default behavior)
python kicad-analyzer.py placement apply main.kicad_pcb placement.csv

# Preview changes without applying
python kicad-analyzer.py placement apply main.kicad_pcb placement.csv --dry-run

# Save to new file
python kicad-analyzer.py placement apply main.kicad_pcb placement.csv -o main_placed.kicad_pcb
```

#### `placement export` - Export current placements to CSV

```bash
python kicad-analyzer.py placement export <pcb_file> [OPTIONS]

Options:
  --output, -o PATH    Output CSV file
  --layer, -l TEXT     Export only specific layer
```

**Examples:**
```bash
# Export all placements
python kicad-analyzer.py placement export main.kicad_pcb

# Export only front copper
python kicad-analyzer.py placement export main.kicad_pcb --layer F.Cu -o front_placement.csv
```

## CSV Format

Placement CSV files must have the following columns:

```csv
Ref,X_mm,Y_mm,Rotation_deg,Side
U1,0.0,6.2,0,F.Cu
U2,3.6,-1.2,-90,F.Cu
U3,-4.0,-0.5,0,F.Cu
```

- **Ref**: Component reference designator (e.g., U1, R10, C5)
- **X_mm**: X coordinate in millimeters
- **Y_mm**: Y coordinate in millimeters
- **Rotation_deg**: Rotation angle in degrees (counter-clockwise)
- **Side**: Layer (F.Cu for front, B.Cu for back)

## Use Cases

### Project-Specific Analysis

For the hw-rec-hj-n54l project (circular Ø18.6mm board):

```bash
# Validate main board layout
python kicad-analyzer.py pcb info layouts/main/main.kicad_pcb

# Check circular fit (R=9.3mm)
python kicad-analyzer.py pcb circular-fit layouts/main/main.kicad_pcb --radius 9.3

# Check collisions with 0.3mm clearance
python kicad-analyzer.py pcb collisions layouts/main/main.kicad_pcb --clearance 0.3

# Apply placement from plan v7
python kicad-analyzer.py placement apply \
    layouts/main/main.kicad_pcb \
    planv7/placement_main_v1.csv \
    --dry-run
```

### Footprint Library Analysis

```bash
# Analyze all footprints in a directory
for file in parts/*/footprint.kicad_mod; do
    echo "=== $file ==="
    python kicad-analyzer.py footprint info "$file"
done

# Find largest footprints
python kicad-analyzer.py pcb list main.kicad_pcb --sort area | head -10
```

### Placement Workflow

1. **Export current placement:**
   ```bash
   python kicad-analyzer.py placement export main.kicad_pcb -o current.csv
   ```

2. **Modify CSV in your editor**

3. **Validate changes:**
   ```bash
   python kicad-analyzer.py placement validate modified.csv --circular --radius 9.3
   ```

4. **Preview application:**
   ```bash
   python kicad-analyzer.py placement apply main.kicad_pcb modified.csv --dry-run
   ```

5. **Apply placement:**
   ```bash
   python kicad-analyzer.py placement apply main.kicad_pcb modified.csv
   ```

## Python API

The package can also be used as a Python library:

```python
from pathlib import Path
from kicad_analyzer.core.analyzer import PCBAnalyzer, FootprintAnalyzer
from kicad_analyzer.core.geometry import Point

# Analyze a PCB
analyzer = PCBAnalyzer(Path("main.kicad_pcb"))
summary = analyzer.get_summary()
print(f"Found {summary['footprint_count']} components")

# Check circular fit
fit_reports = analyzer.check_circular_fit(radius=9.3, center=Point(0, 0))
violations = [r for r in fit_reports if not r.fits]

# Check collisions
collisions = analyzer.check_collisions(clearance=0.5)
critical = [c for c in collisions if c.severity == 'critical']

# Analyze a footprint
fp_analyzer = FootprintAnalyzer(Path("footprint.kicad_mod"))
bbox = fp_analyzer.get_bbox()
print(f"Footprint size: {bbox.width:.2f} × {bbox.height:.2f} mm")
```

## Troubleshooting

### kiutils ImportError

If you get an error about kiutils not being installed:

```bash
pip install kiutils
```

### Encoding Issues on Windows

If you see Unicode encoding errors on Windows, run with UTF-8 encoding:

```bash
chcp 65001
python kicad-analyzer.py pcb info main.kicad_pcb
```

### Permission Errors

If you can't write output files, check file permissions or use `--output` to specify a different location.

## Development

### Running Tests

```bash
# Install development dependencies
pip install pytest

# Run tests
pytest tests/
```

### Code Style

This project follows Python best practices:

- PEP 8 style guide
- Type hints for function signatures
- Comprehensive docstrings
- Modular architecture with clear separation of concerns

## License

Part of the hw-rec-hj-n54l project.

## Dependencies

- **kiutils** (>=1.4.0): KiCad file parsing
- **typer** (>=0.9.0): CLI framework
- **rich** (>=13.0.0): Terminal formatting

## Author

HW-REC Project

## Contributing

Improvements and bug fixes are welcome. Key areas for contribution:

- Additional analysis functions
- Support for more KiCad file types
- Export formats (JSON, Excel, etc.)
- Visualization capabilities
- Performance optimizations

## Changelog

### v0.1.0 (Initial Release)

- Core geometry primitives (Point, BoundingBox)
- KiCad file parsing with kiutils
- Footprint analysis commands
- PCB analysis commands
- Placement management commands
- Rich terminal output with tables
- Collision detection
- Circular board fit validation
