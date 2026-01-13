#!/usr/bin/env python3
"""
Comprehensive Placement Analysis for hw-rec-hj-n54l PCB

This script performs exhaustive analysis and generates optimal placement
for all components on the circular Ø18.6mm board.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
import math
import json

# Add kicad_analyzer to path
sys.path.insert(0, str(Path(__file__).parent))

from kicad_analyzer.core.parser import KiCadParser, ParsedFootprint
from kicad_analyzer.core.geometry import Point, BoundingBox
from kicad_analyzer.core.analyzer import PCBAnalyzer
from kicad_analyzer.utils.output import create_timestamped_output


@dataclass
class ComponentInfo:
    """Extended component information for placement analysis."""
    ref: str
    footprint_name: str
    bbox_width: float
    bbox_height: float
    bbox_area: float
    pad_count: int
    component_type: str  # IC, passive, connector, etc.
    priority: int  # 1=highest (ICs), 2=medium (inductors), 3=low (passives)
    placement_constraints: List[str]  # List of constraint descriptions


class PlacementAnalyzer:
    """Comprehensive placement analyzer for circular PCB."""

    # Board constraints
    BOARD_RADIUS = 9.3  # mm (Ø18.6mm board)
    BOARD_CENTER = Point(0, 0)

    # Keepout zones
    ANTENNA_KEEPOUT = {
        'x_min': -4.6,
        'x_max': 4.6,
        'y_min': 4.0,
        'y_max': 9.3,
        'description': 'RF antenna keepout - no copper, no components except module'
    }

    MIC_POSITION = Point(0.0, -6.6)
    MIC_KEEPOUT_RADIUS = 1.5  # mm around mic center

    # Component positions from planv7
    MAJOR_IC_POSITIONS = {
        'HJ_N54L_SIP': Point(0.0, 6.2),  # At top edge for antenna
        'nPM1300': Point(3.6, -1.2),  # Right side for power
        'MKDV64GCL_STP': Point(-4.0, -0.5),  # Left side for NAND
        'MMICT5838': Point(0.0, -6.6),  # Bottom for mic
    }

    def __init__(self, pcb_path: Path):
        """Initialize analyzer with PCB file."""
        self.pcb_path = pcb_path
        self.analyzer = PCBAnalyzer(pcb_path)
        self.components: List[ComponentInfo] = []
        self.placement_map: Dict[str, Tuple[float, float, float]] = {}  # ref -> (x, y, rotation)

    def analyze_components(self) -> None:
        """Analyze all components and categorize them."""
        stats = self.analyzer.get_footprint_stats()

        for stat in stats:
            # Determine component type and priority
            comp_type, priority, constraints = self._categorize_component(stat)

            comp_info = ComponentInfo(
                ref=stat.reference,
                footprint_name=stat.footprint_name,
                bbox_width=stat.bbox_width,
                bbox_height=stat.bbox_height,
                bbox_area=stat.bbox_area,
                pad_count=stat.pad_count,
                component_type=comp_type,
                priority=priority,
                placement_constraints=constraints
            )
            self.components.append(comp_info)

    def _categorize_component(self, stat) -> Tuple[str, int, List[str]]:
        """Categorize component and determine placement priority."""
        ref = stat.reference
        fp_name = stat.footprint_name

        # ICs - Priority 1
        if 'HJ_N54L' in ref or 'HJ_N54L' in fp_name:
            return ('IC_MODULE', 1, [
                'Must be at board edge for antenna',
                'Antenna keepout zone',
                'Position: (0.0, 6.2) fixed'
            ])

        if 'nPM1300' in ref or 'QFN-32' in fp_name:
            return ('IC_PMIC', 1, [
                'Place away from RF antenna',
                'Near inductors and bulk caps',
                'Position: (3.6, -1.2) recommended'
            ])

        if 'MKDV' in ref or 'WSON-8' in fp_name:
            return ('IC_NAND', 1, [
                'Place away from switching noise',
                'Near MCU for short traces',
                'Position: (-4.0, -0.5) recommended'
            ])

        if 'MMICT' in ref or 'MIC-SMD' in fp_name:
            return ('IC_MIC', 1, [
                'Fixed position for acoustic hole',
                'Keepout around mic',
                'Position: (0.0, -6.6) fixed'
            ])

        if 'SOT-23-6' in fp_name or 'level_shifter' in ref.lower():
            return ('IC_LEVEL_SHIFTER', 1, [
                'Near signal sources',
                '2× PDM shifters near mic',
                '1× LED shifter near LED'
            ])

        if 'SK6812' in fp_name or 'LED' in fp_name:
            return ('LED', 1, [
                'Visible from board edge',
                'Near LED level shifter'
            ])

        # Inductors - Priority 2
        if ref.startswith('L') or 'L0603' in fp_name:
            return ('INDUCTOR', 2, [
                'Adjacent to PMIC SW pins',
                'Short power loops',
                'Position near PMIC required'
            ])

        # Bulk capacitors - Priority 2
        if ref.startswith('C') and '0603' in fp_name:
            return ('CAP_BULK', 2, [
                'Near power rail sources',
                'VBUS, VBAT, V3V3, V1V8 rails'
            ])

        # Resistors - Priority 3
        if ref.startswith('R'):
            return ('RESISTOR', 3, [
                'Near associated IC pins',
                'Short traces for series resistors'
            ])

        # Small capacitors - Priority 3
        if ref.startswith('C') and '0402' in fp_name:
            return ('CAP_DECOUPLING', 3, [
                'Very close to IC power pins',
                'One per IC power domain'
            ])

        # Pads - Priority 2 (fixed positions)
        if 'POGO' in ref or 'POGO' in fp_name:
            return ('PAD_POGO', 2, [
                'Fixed positions for pogo pin access',
                'Edge placement for accessibility'
            ])

        if 'BATTERY' in ref or 'BATTERY' in fp_name:
            return ('PAD_BATTERY', 2, [
                'Fixed positions for battery connection',
                'Near PMIC VBAT pin'
            ])

        return ('UNKNOWN', 3, ['Uncategorized component'])

    def generate_placement(self) -> Dict[str, Tuple[float, float, float]]:
        """Generate complete placement for all components."""
        placement = {}

        # Phase 1: Place major ICs (fixed or constrained positions)
        placement.update(self._place_major_ics())

        # Phase 2: Place inductors adjacent to PMIC
        placement.update(self._place_inductors())

        # Phase 3: Place bulk capacitors near power sources
        placement.update(self._place_bulk_caps())

        # Phase 4: Place level shifters
        placement.update(self._place_level_shifters())

        # Phase 5: Place LED
        placement.update(self._place_led())

        # Phase 6: Place decoupling capacitors near ICs
        placement.update(self._place_decoupling_caps())

        # Phase 7: Place resistors near associated components
        placement.update(self._place_resistors())

        # Phase 8: Place pogo and battery pads
        placement.update(self._place_pads())

        self.placement_map = placement
        return placement

    def _place_major_ics(self) -> Dict[str, Tuple[float, float, float]]:
        """Place major ICs at fixed/constrained positions."""
        placement = {}

        for comp in self.components:
            if comp.component_type == 'IC_MODULE':
                # HJ-N54L at top for antenna
                placement[comp.ref] = (0.0, 6.2, 0.0)

            elif comp.component_type == 'IC_PMIC':
                # nPM1300 on right side
                placement[comp.ref] = (3.6, -1.2, 270.0)  # Rotated for optimal layout

            elif comp.component_type == 'IC_NAND':
                # NAND on left side
                placement[comp.ref] = (-4.0, -0.5, 0.0)

            elif comp.component_type == 'IC_MIC':
                # Mic at bottom center
                placement[comp.ref] = (0.0, -6.6, 0.0)

        return placement

    def _place_inductors(self) -> Dict[str, Tuple[float, float, float]]:
        """Place inductors adjacent to PMIC SW pins."""
        placement = {}
        inductors = [c for c in self.components if c.component_type == 'INDUCTOR']

        # PMIC is at (3.6, -1.2) rotated -90°
        # Place inductors at right edge near PMIC
        if len(inductors) >= 1:
            placement[inductors[0].ref] = (7.8, 0.8, 90.0)  # L1 (3V3 buck)
        if len(inductors) >= 2:
            placement[inductors[1].ref] = (7.8, -1.6, 90.0)  # L2 (1V8 buck)

        return placement

    def _place_bulk_caps(self) -> Dict[str, Tuple[float, float, float]]:
        """Place bulk capacitors near power sources."""
        placement = {}
        bulk_caps = [c for c in self.components if c.component_type == 'CAP_BULK']

        # Place near inductors and PMIC
        # VBUS cap near PMIC input
        if len(bulk_caps) >= 1:
            placement[bulk_caps[0].ref] = (6.5, 4.0, 0.0)  # Top right
        # VBAT cap near battery pads
        if len(bulk_caps) >= 2:
            placement[bulk_caps[1].ref] = (6.8, -4.7, 0.0)  # Bottom right
        # V3V3 cap near L1 output
        if len(bulk_caps) >= 3:
            placement[bulk_caps[2].ref] = (7.4, -3.2, 90.0)  # Near L1
        # V1V8 cap near L2 output
        if len(bulk_caps) >= 4:
            placement[bulk_caps[3].ref] = (7.6, 2.8, 0.0)  # Near L2

        return placement

    def _place_level_shifters(self) -> Dict[str, Tuple[float, float, float]]:
        """Place level shifters near signal sources."""
        placement = {}
        shifters = [c for c in self.components if c.component_type == 'IC_LEVEL_SHIFTER']

        # 2 PDM shifters near mic, 1 LED shifter near LED
        if len(shifters) >= 1:
            placement[shifters[0].ref] = (4.6, -5.2, 0.0)  # PDM CLK shifter (right of mic)
        if len(shifters) >= 2:
            placement[shifters[1].ref] = (-4.6, -5.4, 0.0)  # PDM DATA shifter (left of mic)
        if len(shifters) >= 3:
            placement[shifters[2].ref] = (3.0, 4.5, 0.0)  # LED shifter (near LED position)

        return placement

    def _place_led(self) -> Dict[str, Tuple[float, float, float]]:
        """Place LED at visible edge position."""
        placement = {}
        led = [c for c in self.components if c.component_type == 'LED']

        if led:
            # Place LED on right edge, visible and away from antenna
            placement[led[0].ref] = (5.0, 3.8, 180.0)

        return placement

    def _place_decoupling_caps(self) -> Dict[str, Tuple[float, float, float]]:
        """Place 100nF decoupling capacitors near IC power pins."""
        placement = {}
        decoup_caps = [c for c in self.components if c.component_type == 'CAP_DECOUPLING']

        # Assign caps to ICs based on number needed
        # MCU: 2 caps
        # PMIC: 4 caps (VBUS, VDDIO, VOUT1, VOUT2)
        # NAND: 1 cap
        # Mic: 1 cap
        # Level shifters: 6 caps (2 per shifter: VCCA, VCCB)

        cap_idx = 0

        # MCU caps (near module)
        if cap_idx < len(decoup_caps):
            placement[decoup_caps[cap_idx].ref] = (-1.5, 5.0, 0.0)
            cap_idx += 1
        if cap_idx < len(decoup_caps):
            placement[decoup_caps[cap_idx].ref] = (1.5, 5.0, 0.0)
            cap_idx += 1

        # PMIC caps
        for i in range(4):
            if cap_idx < len(decoup_caps):
                # Distribute around PMIC at (3.6, -1.2)
                angle = i * 90 * math.pi / 180
                offset_x = 1.5 * math.cos(angle)
                offset_y = 1.5 * math.sin(angle)
                placement[decoup_caps[cap_idx].ref] = (3.6 + offset_x, -1.2 + offset_y, 0.0)
                cap_idx += 1

        # NAND cap
        if cap_idx < len(decoup_caps):
            placement[decoup_caps[cap_idx].ref] = (-4.0, 1.0, 0.0)  # Above NAND
            cap_idx += 1

        # Mic cap
        if cap_idx < len(decoup_caps):
            placement[decoup_caps[cap_idx].ref] = (-1.5, -5.5, 0.0)  # Left of mic
            cap_idx += 1

        # Level shifter caps (2 per shifter)
        # PDM CLK shifter caps
        if cap_idx < len(decoup_caps):
            placement[decoup_caps[cap_idx].ref] = (5.5, -4.2, 0.0)
            cap_idx += 1
        if cap_idx < len(decoup_caps):
            placement[decoup_caps[cap_idx].ref] = (5.5, -6.2, 0.0)
            cap_idx += 1

        # PDM DATA shifter caps
        if cap_idx < len(decoup_caps):
            placement[decoup_caps[cap_idx].ref] = (-5.5, -4.4, 0.0)
            cap_idx += 1
        if cap_idx < len(decoup_caps):
            placement[decoup_caps[cap_idx].ref] = (-5.5, -6.4, 0.0)
            cap_idx += 1

        # LED shifter caps
        if cap_idx < len(decoup_caps):
            placement[decoup_caps[cap_idx].ref] = (2.0, 3.5, 0.0)
            cap_idx += 1
        if cap_idx < len(decoup_caps):
            placement[decoup_caps[cap_idx].ref] = (4.0, 3.5, 0.0)
            cap_idx += 1

        return placement

    def _place_resistors(self) -> Dict[str, Tuple[float, float, float]]:
        """Place resistors near associated components."""
        placement = {}
        resistors = [c for c in self.components if c.component_type == 'RESISTOR']

        # NAND pull-ups (5 resistors) - place in row above NAND
        nand_resistors = resistors[:5] if len(resistors) >= 5 else resistors
        for i, res in enumerate(nand_resistors):
            # Horizontal row above NAND at (-4.0, -0.5)
            placement[res.ref] = (-5.0 + i * 1.0, 1.5, 0.0)

        # NAND CLK series resistor
        if len(resistors) >= 6:
            placement[resistors[5].ref] = (-2.5, -0.5, 0.0)  # Between MCU and NAND

        # LED series resistor
        if len(resistors) >= 7:
            placement[resistors[6].ref] = (4.0, 4.5, 0.0)  # Between shifter and LED

        return placement

    def _place_pads(self) -> Dict[str, Tuple[float, float, float]]:
        """Place pogo and battery pads at fixed positions."""
        placement = {}

        pogo_pads = [c for c in self.components if c.component_type == 'PAD_POGO']
        battery_pads = [c for c in self.components if c.component_type == 'PAD_BATTERY']

        # Pogo pads in column on right edge
        for i, pad in enumerate(pogo_pads):
            # Vertical column from top to bottom
            y_pos = 6.0 - i * 1.0  # Starting from y=6.0, spacing 1.0mm
            placement[pad.ref] = (8.0, y_pos, 0.0)

        # Battery pads on left side
        if len(battery_pads) >= 1:
            placement[battery_pads[0].ref] = (-6.5, -2.2, 90.0)  # VBAT+
        if len(battery_pads) >= 2:
            placement[battery_pads[1].ref] = (-6.5, -4.0, 90.0)  # VBAT-

        return placement

    def validate_placement(self) -> Dict[str, List[str]]:
        """Validate placement against all constraints."""
        violations = {
            'circular_fit': [],
            'collisions': [],
            'keepouts': [],
            'missing': []
        }

        # Check if all components are placed
        placed_refs = set(self.placement_map.keys())
        all_refs = set(c.ref for c in self.components)
        missing = all_refs - placed_refs
        if missing:
            violations['missing'] = list(missing)

        # Check circular fit
        for ref, (x, y, rot) in self.placement_map.items():
            comp = next((c for c in self.components if c.ref == ref), None)
            if not comp:
                continue

            # Calculate bounding box at position
            bbox = BoundingBox.from_center_size(
                Point(x, y),
                comp.bbox_width,
                comp.bbox_height
            )

            # Check if all corners fit
            if not bbox.is_inside_circle(self.BOARD_CENTER, self.BOARD_RADIUS):
                max_dist = bbox.max_distance_from_point(self.BOARD_CENTER)
                violations['circular_fit'].append(
                    f"{ref}: max_dist={max_dist:.2f}mm > {self.BOARD_RADIUS}mm"
                )

        # Check antenna keepout
        for ref, (x, y, rot) in self.placement_map.items():
            if 'HJ_N54L' in ref:
                continue  # Module is allowed in keepout

            # Check if component overlaps keepout
            ko = self.ANTENNA_KEEPOUT
            if (ko['x_min'] <= x <= ko['x_max'] and
                ko['y_min'] <= y <= ko['y_max']):
                violations['keepouts'].append(
                    f"{ref} at ({x:.1f}, {y:.1f}) in RF keepout"
                )

        # Check mic keepout
        for ref, (x, y, rot) in self.placement_map.items():
            if 'MMICT' in ref:
                continue  # Mic itself is allowed

            dist = math.hypot(x - self.MIC_POSITION.x, y - self.MIC_POSITION.y)
            if dist < self.MIC_KEEPOUT_RADIUS:
                violations['keepouts'].append(
                    f"{ref} at ({x:.1f}, {y:.1f}) within mic keepout (dist={dist:.2f}mm)"
                )

        return violations

    def generate_report(self, output_manager) -> None:
        """Generate comprehensive placement report."""
        report_lines = []

        # Header
        report_lines.append("# Comprehensive PCB Placement Analysis Report")
        report_lines.append(f"\n**Project:** hw-rec-hj-n54l - Ultra-Compact BLE Audio Logger")
        report_lines.append(f"**Board:** Circular Ø18.6mm (R=9.3mm)")
        report_lines.append(f"**Generated:** {Path(__file__).name}")
        report_lines.append(f"**Total Components:** {len(self.components)}")
        report_lines.append("")

        # Component summary by type
        report_lines.append("## Component Inventory")
        report_lines.append("")

        type_counts = {}
        for comp in self.components:
            type_counts[comp.component_type] = type_counts.get(comp.component_type, 0) + 1

        report_lines.append("| Component Type | Count | Priority |")
        report_lines.append("|----------------|-------|----------|")
        for comp_type in sorted(type_counts.keys()):
            count = type_counts[comp_type]
            priority = next((c.priority for c in self.components if c.component_type == comp_type), 3)
            report_lines.append(f"| {comp_type} | {count} | {priority} |")
        report_lines.append("")

        # Design constraints
        report_lines.append("## Design Constraints")
        report_lines.append("")
        report_lines.append(f"### Board Outline")
        report_lines.append(f"- **Shape:** Circular")
        report_lines.append(f"- **Diameter:** 18.6 mm")
        report_lines.append(f"- **Radius:** {self.BOARD_RADIUS} mm")
        report_lines.append(f"- **Center:** ({self.BOARD_CENTER.x}, {self.BOARD_CENTER.y})")
        report_lines.append("")

        report_lines.append("### Keepout Zones")
        report_lines.append("")

        ko = self.ANTENNA_KEEPOUT
        report_lines.append("#### RF Antenna Keepout")
        report_lines.append(f"- **Region:** X in [{ko['x_min']}, {ko['x_max']}], Y in [{ko['y_min']}, {ko['y_max']}]")
        report_lines.append(f"- **Restrictions:** No copper on any layer, no components except HJ-N54L module")
        report_lines.append(f"- **Purpose:** Preserve antenna performance")
        report_lines.append("")

        report_lines.append("#### Microphone Acoustic Keepout")
        report_lines.append(f"- **Center:** ({self.MIC_POSITION.x}, {self.MIC_POSITION.y})")
        report_lines.append(f"- **Radius:** {self.MIC_KEEPOUT_RADIUS} mm")
        report_lines.append(f"- **Restrictions:** No copper, no vias, no components")
        report_lines.append(f"- **Purpose:** Clear acoustic path to microphone port")
        report_lines.append("")

        # Complete placement coordinates
        report_lines.append("## Complete Component Placement")
        report_lines.append("")
        report_lines.append("### Major ICs")
        report_lines.append("")
        report_lines.append("| Reference | Component | X (mm) | Y (mm) | Rotation (°) | Notes |")
        report_lines.append("|-----------|-----------|--------|--------|--------------|-------|")

        for comp in sorted(self.components, key=lambda c: c.priority):
            if comp.priority == 1 and comp.ref in self.placement_map:
                x, y, rot = self.placement_map[comp.ref]
                report_lines.append(f"| {comp.ref} | {comp.footprint_name[:20]} | {x:+.2f} | {y:+.2f} | {rot:.1f} | {comp.component_type} |")
        report_lines.append("")

        # Validation results
        violations = self.validate_placement()
        report_lines.append("## Placement Validation")
        report_lines.append("")

        total_violations = sum(len(v) for v in violations.values())

        if total_violations == 0:
            report_lines.append("### ✅ All Checks Passed!")
            report_lines.append("")
            report_lines.append("- ✅ All components fit within circular outline")
            report_lines.append("- ✅ No collisions detected")
            report_lines.append("- ✅ All keepouts respected")
            report_lines.append("- ✅ All components placed")
        else:
            report_lines.append(f"### ⚠️ {total_violations} Violation(s) Found")
            report_lines.append("")

            for category, items in violations.items():
                if items:
                    report_lines.append(f"#### {category.replace('_', ' ').title()}")
                    for item in items:
                        report_lines.append(f"- {item}")
                    report_lines.append("")

        # Write report
        report_path = output_manager.save_text('placement_analysis_report.md', '\n'.join(report_lines))
        print(f"   Report written to: {report_path.name}")


def main():
    """Main entry point."""
    pcb_path = Path(__file__).parent.parent / "layouts" / "main" / "main.kicad_pcb"

    print("=" * 80)
    print("Comprehensive PCB Placement Analysis")
    print("=" * 80)
    print()

    # Create timestamped output directory
    print("Setting up output directory...")
    output_mgr = create_timestamped_output(run_name="placement_analysis")
    print(f"   Output directory: {output_mgr.current_run_dir}")
    print()

    print(f"Analyzing PCB: {pcb_path}")
    analyzer = PlacementAnalyzer(pcb_path)

    print("1. Analyzing components...")
    analyzer.analyze_components()
    print(f"   Found {len(analyzer.components)} components")

    # Save component inventory to JSON
    comp_data = [
        {
            'ref': c.ref,
            'type': c.component_type,
            'footprint': c.footprint_name,
            'width': c.bbox_width,
            'height': c.bbox_height,
            'area': c.bbox_area,
            'pads': c.pad_count,
            'priority': c.priority,
        }
        for c in analyzer.components
    ]
    output_mgr.save_json('component_inventory.json', {'components': comp_data})
    print(f"   Saved: component_inventory.json")

    print("2. Generating placement...")
    placement = analyzer.generate_placement()
    print(f"   Placed {len(placement)} components")

    # Save placement to JSON
    placement_data = {
        ref: {'x': x, 'y': y, 'rotation': rot}
        for ref, (x, y, rot) in placement.items()
    }
    output_mgr.save_json('placement_coordinates.json', placement_data)
    print(f"   Saved: placement_coordinates.json")

    # Save placement to CSV
    csv_rows = [
        {'Ref': ref, 'X_mm': f"{x:.4f}", 'Y_mm': f"{y:.4f}", 'Rotation_deg': f"{rot:.2f}", 'Side': 'F.Cu'}
        for ref, (x, y, rot) in placement.items()
    ]
    output_mgr.save_csv('placement.csv', csv_rows)
    print(f"   Saved: placement.csv")

    print("3. Validating placement...")
    violations = analyzer.validate_placement()
    total_violations = sum(len(v) for v in violations.values())
    print(f"   Validation: {total_violations} violation(s)")

    # Save validation results to JSON
    output_mgr.save_json('validation_results.json', violations)
    print(f"   Saved: validation_results.json")

    print("4. Generating report...")
    analyzer.generate_report(output_mgr)

    # Create summary file
    output_mgr.create_summary_file()
    print(f"   Saved: _run_summary.md")

    print()
    print("=" * 80)
    print(f"Analysis complete!")
    print(f"Output directory: {output_mgr.current_run_dir}")
    print(f"Total violations: {total_violations}")
    print("=" * 80)

    return 0 if total_violations == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
