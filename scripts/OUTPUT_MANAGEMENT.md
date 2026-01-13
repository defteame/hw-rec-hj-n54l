# KiCad Analyzer - Output Management

## Overview

All analysis runs automatically save outputs to timestamped directories under:
```
build/kicad_analysis/<ISO_timestamp>_<run_name>/
```

## Directory Structure Example

```
build/kicad_analysis/
├── 2026-01-13T21-41-02_placement_analysis/
│   ├── _run_summary.md                    # Auto-generated summary
│   ├── component_inventory.json           # All components with properties
│   ├── placement.csv                      # Placement in CSV format
│   ├── placement_coordinates.json         # Placement in JSON format
│   ├── placement_analysis_report.md       # Detailed analysis report
│   └── validation_results.json            # Validation violations
├── 2026-01-13T21-45-15_placement_analysis/
│   └── ...
└── 2026-01-13T22-10-30_placement_analysis/
    └── ...
```

## Timestamp Format

Timestamps follow ISO 8601 format down to seconds:
```
YYYY-MM-DDTHH-MM-SS
```

Example: `2026-01-13T21-41-02`

This ensures:
- Chronological sorting
- No filename conflicts
- Easy to identify when analysis was run
- Cross-platform compatibility (no colons in filenames)

## Viewing Latest Results

### Quick View
```bash
python scripts/show_latest_analysis.py
```

This will:
- Find the most recent analysis run
- Display the summary
- Show the full path to the directory

### Manual Navigation
The latest run is always the directory with the newest timestamp:
```bash
cd build/kicad_analysis
ls -lt  # Shows newest first
```

## Output Files Explanation

### `_run_summary.md`
Auto-generated summary with:
- Run timestamp
- Project root
- List of all generated files with sizes

### `component_inventory.json`
Complete inventory of all components with:
```json
{
  "components": [
    {
      "ref": "U1",
      "type": "IC_MODULE",
      "footprint": "HJ_N54L_SIP",
      "width": 4.5,
      "height": 4.5,
      "area": 20.25,
      "pads": 45,
      "priority": 1
    },
    ...
  ]
}
```

### `placement.csv`
Standard CSV format for KiCad import:
```csv
Ref,X_mm,Y_mm,Rotation_deg,Side
U1,0.0000,6.2000,0.00,F.Cu
U2,3.6000,-1.2000,270.00,F.Cu
```

### `placement_coordinates.json`
Placement in JSON format:
```json
{
  "U1": {"x": 0.0, "y": 6.2, "rotation": 0.0},
  "U2": {"x": 3.6, "y": -1.2, "rotation": 270.0}
}
```

### `placement_analysis_report.md`
Detailed markdown report with:
- Component inventory by type
- Design constraints
- Complete placement coordinates
- Validation results
- Keepout zones

### `validation_results.json`
Validation violations organized by category:
```json
{
  "circular_fit": ["U5: max_dist=10.5mm > 9.3mm"],
  "collisions": [],
  "keepouts": ["R1 at (4.0, 4.5) in RF keepout"],
  "missing": ["U3", "U4"]
}
```

## Integration with Scripts

### Comprehensive Placement Analysis

```bash
python scripts/comprehensive_placement_analysis.py
```

Automatically creates timestamped output with all files.

### Using OutputManager in Your Scripts

```python
from kicad_analyzer.utils.output import create_timestamped_output

# Create output manager with timestamped directory
output_mgr = create_timestamped_output(run_name="my_analysis")

# Save text file
output_mgr.save_text('report.md', markdown_content)

# Save JSON
output_mgr.save_json('data.json', {'key': 'value'})

# Save CSV
output_mgr.save_csv('data.csv', rows, headers=['A', 'B', 'C'])

# Get path for manual file operations
path = output_mgr.get_output_path('custom_file.txt')

# Create summary at the end
output_mgr.create_summary_file()
```

## Benefits of This Approach

1. **No Overwriting**: Each run gets its own directory
2. **Version History**: Keep track of different analysis iterations
3. **Easy Comparison**: Compare placements across different runs
4. **Organized**: All related files grouped together
5. **Timestamped**: Know exactly when analysis was performed
6. **Automated**: No manual directory management needed

## Cleaning Up Old Runs

### Manual Cleanup
```bash
# Remove runs older than 7 days
cd build/kicad_analysis
find . -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;
```

### Keep Only Latest N Runs
```bash
cd build/kicad_analysis
ls -t | tail -n +11 | xargs rm -rf  # Keep only 10 newest
```

## Git Integration

The `build/` directory is typically gitignored, so analysis runs
won't clutter your repository. To save specific analysis results:

```bash
# Copy important results to a tracked location
cp build/kicad_analysis/2026-01-13T21-41-02_placement_analysis/placement.csv \
   docs/final_placement_v1.csv
```

## Best Practices

1. **Meaningful Run Names**: Use descriptive names for different types of analysis
   ```python
   create_timestamped_output(run_name="final_placement")
   create_timestamped_output(run_name="debug_antenna_keepout")
   create_timestamped_output(run_name="iteration_v3")
   ```

2. **Review Latest**: Always check the latest run after analysis
   ```bash
   python scripts/show_latest_analysis.py
   ```

3. **Keep Important Runs**: Copy significant results to tracked locations

4. **Clean Regularly**: Remove old analysis runs to save space

5. **Use JSON for Automation**: JSON files are easy to parse in scripts

## Troubleshooting

### "No analysis runs found"
Run an analysis first:
```bash
python scripts/comprehensive_placement_analysis.py
```

### Permission Errors
Ensure you have write permissions to the `build/` directory.

### Disk Space Issues
Remove old analysis runs you no longer need.

## Future Enhancements

Planned features:
- Comparison tool to diff two analysis runs
- Web viewer for interactive analysis results
- Automatic cleanup of old runs (configurable retention)
- Export to other formats (Excel, PDF, HTML)
