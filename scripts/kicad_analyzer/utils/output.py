"""
Output management utilities for organizing analysis results.

This module provides functions for creating timestamped output directories
and managing analysis artifacts.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional


class OutputManager:
    """
    Manages output directories for KiCad analysis runs.

    Creates timestamped directories under build/kicad_analysis/ for each run.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize output manager.

        Args:
            project_root: Root directory of the project. If None, will search upward
                         from current directory for build/ or ato.yaml
        """
        if project_root is None:
            project_root = self._find_project_root()

        self.project_root = project_root
        self.base_output_dir = project_root / "build" / "kicad_analysis"
        self.current_run_dir: Optional[Path] = None

    @staticmethod
    def _find_project_root() -> Path:
        """
        Find project root by searching for build/ directory or ato.yaml.

        Returns:
            Path to project root
        """
        current = Path.cwd()

        # Search upward for build/ or ato.yaml
        for parent in [current] + list(current.parents):
            if (parent / "build").exists() or (parent / "ato.yaml").exists():
                return parent

        # Default to current directory
        return current

    def create_run_directory(self, run_name: Optional[str] = None) -> Path:
        """
        Create a timestamped directory for the current analysis run.

        Args:
            run_name: Optional name to include in directory name

        Returns:
            Path to created run directory
        """
        # Generate timestamp (ISO format down to seconds)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

        # Build directory name
        if run_name:
            dir_name = f"{timestamp}_{run_name}"
        else:
            dir_name = timestamp

        # Create full path
        run_dir = self.base_output_dir / dir_name
        run_dir.mkdir(parents=True, exist_ok=True)

        self.current_run_dir = run_dir
        return run_dir

    def get_output_path(self, filename: str) -> Path:
        """
        Get full path for an output file in the current run directory.

        Args:
            filename: Name of the output file

        Returns:
            Full path to output file

        Raises:
            RuntimeError: If no run directory has been created
        """
        if self.current_run_dir is None:
            raise RuntimeError("No run directory created. Call create_run_directory() first.")

        return self.current_run_dir / filename

    def save_text(self, filename: str, content: str) -> Path:
        """
        Save text content to a file in the current run directory.

        Args:
            filename: Name of the output file
            content: Text content to save

        Returns:
            Path to saved file
        """
        output_path = self.get_output_path(filename)
        output_path.write_text(content, encoding='utf-8')
        return output_path

    def save_json(self, filename: str, data: dict) -> Path:
        """
        Save JSON data to a file in the current run directory.

        Args:
            filename: Name of the output file
            data: Dictionary to save as JSON

        Returns:
            Path to saved file
        """
        import json
        output_path = self.get_output_path(filename)
        output_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return output_path

    def save_csv(self, filename: str, rows: list, headers: Optional[list] = None) -> Path:
        """
        Save CSV data to a file in the current run directory.

        Args:
            filename: Name of the output file
            rows: List of rows (each row is a list or dict)
            headers: Optional list of header names

        Returns:
            Path to saved file
        """
        import csv
        output_path = self.get_output_path(filename)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            if rows and isinstance(rows[0], dict):
                # Dict rows
                writer = csv.DictWriter(f, fieldnames=headers or rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            else:
                # List rows
                writer = csv.writer(f)
                if headers:
                    writer.writerow(headers)
                writer.writerows(rows)

        return output_path

    def create_summary_file(self) -> Path:
        """
        Create a summary file with run metadata.

        Returns:
            Path to summary file
        """
        if self.current_run_dir is None:
            raise RuntimeError("No run directory created.")

        summary = [
            f"# Analysis Run Summary",
            f"",
            f"**Run Directory:** {self.current_run_dir.name}",
            f"**Timestamp:** {datetime.now().isoformat()}",
            f"**Project Root:** {self.project_root}",
            f"",
            f"## Files Generated",
            f"",
        ]

        # List all files in run directory
        for file in sorted(self.current_run_dir.iterdir()):
            if file.is_file():
                size_kb = file.stat().st_size / 1024
                summary.append(f"- `{file.name}` ({size_kb:.1f} KB)")

        summary_path = self.get_output_path("_run_summary.md")
        summary_path.write_text('\n'.join(summary), encoding='utf-8')
        return summary_path

    @staticmethod
    def get_latest_run(project_root: Optional[Path] = None) -> Optional[Path]:
        """
        Get the path to the most recent analysis run.

        Args:
            project_root: Project root directory

        Returns:
            Path to latest run directory, or None if no runs found
        """
        if project_root is None:
            project_root = OutputManager._find_project_root()

        analysis_dir = project_root / "build" / "kicad_analysis"
        if not analysis_dir.exists():
            return None

        # Get all subdirectories, sorted by name (which includes timestamp)
        runs = [d for d in analysis_dir.iterdir() if d.is_directory()]
        if not runs:
            return None

        return max(runs, key=lambda p: p.name)

    def __str__(self) -> str:
        """String representation."""
        if self.current_run_dir:
            return f"OutputManager(run_dir={self.current_run_dir})"
        return f"OutputManager(base={self.base_output_dir})"


def create_timestamped_output(run_name: Optional[str] = None) -> OutputManager:
    """
    Convenience function to create an output manager with a new run directory.

    Args:
        run_name: Optional name for this analysis run

    Returns:
        Configured OutputManager instance
    """
    manager = OutputManager()
    manager.create_run_directory(run_name)
    return manager
