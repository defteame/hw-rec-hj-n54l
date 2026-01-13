#!/usr/bin/env python3
"""
Helper script to show the latest analysis results.

This script finds and displays information about the most recent
analysis run, making it easy to review results.
"""

import sys
from pathlib import Path

# Add kicad_analyzer to path
sys.path.insert(0, str(Path(__file__).parent))

from kicad_analyzer.utils.output import OutputManager


def main():
    """Main entry point."""
    print("=" * 80)
    print("Latest KiCad Analysis Results")
    print("=" * 80)
    print()

    # Find latest run
    latest_run = OutputManager.get_latest_run()

    if latest_run is None:
        print("No analysis runs found.")
        print()
        print("Run an analysis first:")
        print("  python comprehensive_placement_analysis.py")
        return 1

    print(f"Latest run directory: {latest_run}")
    print()

    # Read and display summary
    summary_file = latest_run / "_run_summary.md"
    if summary_file.exists():
        print(summary_file.read_text(encoding='utf-8'))
    else:
        print("Summary file not found.")
        print()
        print("Files in directory:")
        for file in sorted(latest_run.iterdir()):
            if file.is_file():
                size_kb = file.stat().st_size / 1024
                print(f"  - {file.name} ({size_kb:.1f} KB)")

    print()
    print("=" * 80)
    print(f"Full path: {latest_run}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
