# KiCad Analyzer - Quick Start Guide

## Installation

1. **Install Python dependencies:**

```bash
cd scripts
pip install -r requirements.txt
```

Alternatively, install just the required packages:

```bash
pip install kiutils typer rich
```

2. **Verify installation:**

```bash
python kicad-analyzer.py --help
```

You should see the main help menu.

## First Analysis

### Analyze the main PCB

```bash
# Show PCB information
python kicad-analyzer.py pcb info ../layouts/main/main.kicad_pcb

# List all components
python kicad-analyzer.py pcb list ../layouts/main/main.kicad_pcb

# Check for collisions
python kicad-analyzer.py pcb collisions ../layouts/main/main.kicad_pcb --clearance 0.3

# Validate circular fit (Ø18.6mm board = 9.3mm radius)
python kicad-analyzer.py pcb circular-fit ../layouts/main/main.kicad_pcb --radius 9.3
```

### Analyze a specific footprint

```bash
# Show footprint info
python kicad-analyzer.py footprint info ../parts/HJ_N54L_SIP/footprint.kicad_mod

# Calculate bounding box
python kicad-analyzer.py footprint bbox ../parts/HJ_N54L_SIP/footprint.kicad_mod

# List all pads
python kicad-analyzer.py footprint pads ../parts/HJ_N54L_SIP/footprint.kicad_mod
```

### Work with placements

```bash
# Export current placements
python kicad-analyzer.py placement export ../layouts/main/main.kicad_pcb -o current_placement.csv

# Validate a placement CSV
python kicad-analyzer.py placement validate ../planv7/placement_main_v1.csv --circular --radius 9.3

# Apply placement (dry run first)
python kicad-analyzer.py placement apply ../layouts/main/main.kicad_pcb ../planv7/placement_main_v1.csv --dry-run

# Apply for real
python kicad-analyzer.py placement apply ../layouts/main/main.kicad_pcb ../planv7/placement_main_v1.csv
```

## Project-Specific Examples

For the hw-rec-hj-n54l project (circular Ø18.6mm board):

### Complete PCB validation workflow

```bash
# 1. Analyze current state
python kicad-analyzer.py pcb info ../layouts/main/main.kicad_pcb

# 2. Check circular fit
python kicad-analyzer.py pcb circular-fit ../layouts/main/main.kicad_pcb --radius 9.3 > fit_report.txt

# 3. Check collisions
python kicad-analyzer.py pcb collisions ../layouts/main/main.kicad_pcb --clearance 0.3 > collision_report.txt

# 4. List components by size
python kicad-analyzer.py pcb list ../layouts/main/main.kicad_pcb --sort area

# 5. Show layer distribution
python kicad-analyzer.py pcb layers ../layouts/main/main.kicad_pcb
```

### Placement workflow

```bash
# 1. Validate placement CSV
python kicad-analyzer.py placement validate ../planv7/placement_main_v1.csv \
    --circular --radius 9.3

# 2. Preview what would change
python kicad-analyzer.py placement apply \
    ../layouts/main/main.kicad_pcb \
    ../planv7/placement_main_v1.csv \
    --dry-run

# 3. Apply with backup (default)
python kicad-analyzer.py placement apply \
    ../layouts/main/main.kicad_pcb \
    ../planv7/placement_main_v1.csv

# 4. Verify result
python kicad-analyzer.py pcb circular-fit ../layouts/main/main.kicad_pcb --radius 9.3
```

### Footprint library analysis

```bash
# Analyze all footprints
for file in ../parts/*/footprint.kicad_mod; do
    echo "=== $(basename $(dirname $file)) ==="
    python kicad-analyzer.py footprint bbox "$file"
    echo ""
done

# Find footprints with specific pad types
python kicad-analyzer.py footprint pads ../parts/*/footprint.kicad_mod --type smd
```

## Common Issues

### Missing dependencies

If you see `ModuleNotFoundError: No module named 'kiutils'`:

```bash
pip install kiutils typer rich
```

### File not found errors

Make sure you're running from the `scripts/` directory or use full paths:

```bash
cd D:\Projects\Personal\Repos\hw-rec-hj-n54l\scripts
python kicad-analyzer.py pcb info ../layouts/main/main.kicad_pcb
```

### Unicode errors on Windows

If you see encoding errors, set UTF-8:

```powershell
chcp 65001
python kicad-analyzer.py pcb info ../layouts/main/main.kicad_pcb
```

## Tips

1. **Use `--help` on any command** to see all options:
   ```bash
   python kicad-analyzer.py pcb --help
   python kicad-analyzer.py pcb collisions --help
   ```

2. **JSON output** for scripting:
   ```bash
   python kicad-analyzer.py pcb info main.kicad_pcb --json > pcb_data.json
   ```

3. **Pipe output** to files:
   ```bash
   python kicad-analyzer.py pcb list main.kicad_pcb > component_list.txt
   ```

4. **Chain commands** in scripts:
   ```bash
   python kicad-analyzer.py pcb circular-fit main.kicad_pcb -r 9.3 && \
   python kicad-analyzer.py pcb collisions main.kicad_pcb -c 0.3 && \
   echo "All checks passed!"
   ```

## Next Steps

- Read the full [README.md](README.md) for complete documentation
- Explore all available commands with `--help`
- Check the Python API section for programmatic usage
- Customize the CSV placement files for your layout needs

## Getting Help

```bash
# Main help
python kicad-analyzer.py --help

# Command-specific help
python kicad-analyzer.py footprint --help
python kicad-analyzer.py pcb --help
python kicad-analyzer.py placement --help

# Subcommand help
python kicad-analyzer.py pcb circular-fit --help
```
