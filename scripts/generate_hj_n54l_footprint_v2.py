#!/usr/bin/env python3
"""
Generate KiCad footprint for HJ-N54L_SIP module - Version 2

Based on datasheet Figure 6.1 with CORRECT spacing:
- e1 = 0.55mm (standard pitch)
- e2 = 0.45mm (tight pitch between certain columns)

Key insight: The right-side columns have e2 spacing:
- Column with pins 41,40,39,38 to column with pins 25,24,23,22 = e2 (0.45mm)

Package: 4.50 x 4.50 mm
Pad size: 0.35 x 0.35 mm
Total pads: 45
"""

E1 = 0.55  # Standard pitch (mm)
E2 = 0.45  # Tight pitch (mm)
PAD_SIZE = 0.35  # mm

# Define ABSOLUTE X positions for each column in BOTTOM VIEW
# Based on careful analysis of the datasheet bottom view diagram
# The grid is NOT uniform - right side uses e2 spacing

# Column positions in BOTTOM VIEW (X coordinates in mm)
# Centered so that the center columns are at X=0
# Left side: columns 0-5 use e1 spacing
# Right side: column 6 is e2 from column 5, column 7 is e1 from column 6

# Analyzing the bottom view:
# - 7xe1 annotation shows total width = 7 * 0.55 = 3.85mm
# - But with e2 on the right side, actual positions differ

# Let me define column X positions based on the diagram:
# The pads span from left edge to right edge
# Center at column position that makes the pattern symmetric

COL_X = {
    0: -1.65,   # Leftmost (pins 6,7,8,9,10,11,12,13)
    1: -1.10,   # Second from left (pins 5, 30,31,32,33, 14)
    2: -0.55,   # Third (pins 4, 29, 34, 15)
    3: 0.00,    # Center-left (pins 3, 28, 43,44, 35, 16)
    4: 0.55,    # Center-right (pins 2, 27, 42,45, 36, 17)
    5: 1.10,    # Second from right (pins 1, 26, 40,39,38, 37, 18)
    # Right edge uses e2 spacing from column 5
    6: 1.10 + E2,  # = 1.55mm (pins 41, 25,24,23,22, 19)
    7: 1.10 + E2 + E1,  # = 2.10mm (pin 20, and pin 21 shares row 6)
}

# Row Y positions in BOTTOM VIEW (all use e1 spacing)
# Row 0 is at top, Row 7 is at bottom
# Centered so center is between rows 3 and 4

ROW_Y = {
    0: -1.925,  # Top row (pins 6,5,4,3,2,1)
    1: -1.375,  # Row 1 (pins 7, 29,28,27,26)
    2: -0.825,  # Row 2 (pins 8,30, 41,25)
    3: -0.275,  # Row 3 (pins 9,31, 43,42, 40,24)
    4: 0.275,   # Row 4 (pins 10,32, 44,45, 39,23)
    5: 0.825,   # Row 5 (pins 11,33, 38,22)
    6: 1.375,   # Row 6 (pins 12, 34,35,36,37, 21)
    7: 1.925,   # Bottom row (pins 13,14,15,16,17,18,19,20)
}

# Pin positions in BOTTOM VIEW (column, row)
# Based on datasheet "2.4 Pins distribution diagram"
PIN_GRID_BOTTOM = {
    # Row 0 (top): 6 pins, cols 0-5
    6: (0, 0), 5: (1, 0), 4: (2, 0), 3: (3, 0), 2: (4, 0), 1: (5, 0),

    # Row 1: 5 pins
    7: (0, 1), 29: (2, 1), 28: (3, 1), 27: (4, 1), 26: (5, 1),

    # Row 2: 4 pins (note: 41 and 25 are at cols 6, not 5!)
    8: (0, 2), 30: (1, 2), 41: (6, 2), 25: (6, 2),  # Wait, can't have two pins at same position

    # Let me re-examine the layout...
}

# Actually, looking at the bottom view diagram more carefully:
# The pins on the right side (25,24,23,22,21) are at a DIFFERENT column than pins (41,40,39,38)
# They are e2 apart, but both visible in the same "column area"

# Let me redefine based on ACTUAL pad positions from the diagram:
# I'll use explicit coordinates for each pin

def get_pin_positions_bottom_view():
    """
    Return pin positions in BOTTOM VIEW coordinates.
    Based on careful analysis of datasheet Figure 6.1.
    """
    positions = {}

    # === ROW 0 (Y = -1.925mm): Pins 6,5,4,3,2,1 ===
    # These are on a regular e1 grid from col 0 to col 5
    positions[6] = (-1.65, -1.925)
    positions[5] = (-1.10, -1.925)
    positions[4] = (-0.55, -1.925)
    positions[3] = (0.00, -1.925)
    positions[2] = (0.55, -1.925)
    positions[1] = (1.10, -1.925)

    # === ROW 1 (Y = -1.375mm): Pins 7, 29,28,27,26 ===
    positions[7] = (-1.65, -1.375)
    positions[29] = (-0.55, -1.375)
    positions[28] = (0.00, -1.375)
    positions[27] = (0.55, -1.375)
    positions[26] = (1.10, -1.375)

    # === ROW 2 (Y = -0.825mm): Pins 8,30, 41,25 ===
    positions[8] = (-1.65, -0.825)
    positions[30] = (-1.10, -0.825)
    positions[41] = (1.10, -0.825)  # Inner right column
    positions[25] = (1.10 + E2, -0.825)  # Outer right column (e2 spacing)

    # === ROW 3 (Y = -0.275mm): Pins 9,31, 43,42, 40,24 ===
    positions[9] = (-1.65, -0.275)
    positions[31] = (-1.10, -0.275)
    positions[43] = (0.00, -0.275)  # Center-left VDD
    positions[42] = (0.55, -0.275)  # Center-right VDD
    positions[40] = (1.10, -0.275)  # Inner right
    positions[24] = (1.10 + E2, -0.275)  # Outer right

    # === ROW 4 (Y = 0.275mm): Pins 10,32, 44,45, 39,23 ===
    positions[10] = (-1.65, 0.275)
    positions[32] = (-1.10, 0.275)
    positions[44] = (0.00, 0.275)  # Center-left VDD
    positions[45] = (0.55, 0.275)  # Center-right VDD
    positions[39] = (1.10, 0.275)  # Inner right
    positions[23] = (1.10 + E2, 0.275)  # Outer right

    # === ROW 5 (Y = 0.825mm): Pins 11,33, 38,22 ===
    positions[11] = (-1.65, 0.825)
    positions[33] = (-1.10, 0.825)
    positions[38] = (1.10, 0.825)  # Inner right
    positions[22] = (1.10 + E2, 0.825)  # Outer right

    # === ROW 6 (Y = 1.375mm): Pins 12, 34,35,36,37, 21 ===
    positions[12] = (-1.65, 1.375)
    positions[34] = (-0.55, 1.375)
    positions[35] = (0.00, 1.375)
    positions[36] = (0.55, 1.375)
    positions[37] = (1.10, 1.375)
    positions[21] = (1.10 + E2, 1.375)  # Outer right

    # === ROW 7 (Y = 1.925mm): Pins 13,14,15,16,17,18,19,20 ===
    # This row extends further right to include pin 20
    positions[13] = (-1.65, 1.925)
    positions[14] = (-1.10, 1.925)
    positions[15] = (-0.55, 1.925)
    positions[16] = (0.00, 1.925)
    positions[17] = (0.55, 1.925)
    positions[18] = (1.10, 1.925)
    positions[19] = (1.10 + E2, 1.925)  # Same X as pin 25,24,23,22,21
    positions[20] = (1.10 + E2 + E1, 1.925)  # Extended position

    return positions


def bottom_to_top_view(bx, by):
    """Convert bottom view coordinates to top view (mirror X)."""
    return (-bx, by)


def generate_footprint():
    """Generate KiCad footprint."""

    # Get bottom view positions
    bottom_positions = get_pin_positions_bottom_view()

    # Convert to top view (mirror X)
    top_positions = {}
    for pin, (bx, by) in bottom_positions.items():
        tx, ty = bottom_to_top_view(bx, by)
        top_positions[pin] = (round(tx, 3), round(ty, 3))

    # Package dimensions
    pkg_half = 2.25
    silk_half = 2.35
    crtyd_half = 2.6

    lines = []
    lines.append('(footprint "HJ_N54L_SIP"')
    lines.append('  (version 20240108)')
    lines.append('  (generator "generate_hj_n54l_footprint_v2.py")')
    lines.append('  (layer "F.Cu")')
    lines.append('  (descr "HJ-N54L_SIP LGA45 nRF54L15-based SiP module 4.5x4.5mm")')
    lines.append('  (attr smd)')

    # Text
    lines.append('  (fp_text reference "REF**" (at 0 -3.2) (layer "F.SilkS")')
    lines.append('    (effects (font (size 0.8 0.8) (thickness 0.12))))')
    lines.append('  (fp_text value "HJ_N54L_SIP" (at 0 3.2) (layer "F.Fab")')
    lines.append('    (effects (font (size 0.8 0.8) (thickness 0.12))))')

    # Silkscreen outline
    lines.append(f'  (fp_line (start -{silk_half} -{silk_half}) (end {silk_half} -{silk_half}) (layer "F.SilkS") (stroke (width 0.12) (type solid)))')
    lines.append(f'  (fp_line (start {silk_half} -{silk_half}) (end {silk_half} {silk_half}) (layer "F.SilkS") (stroke (width 0.12) (type solid)))')
    lines.append(f'  (fp_line (start {silk_half} {silk_half}) (end -{silk_half} {silk_half}) (layer "F.SilkS") (stroke (width 0.12) (type solid)))')
    lines.append(f'  (fp_line (start -{silk_half} {silk_half}) (end -{silk_half} -{silk_half}) (layer "F.SilkS") (stroke (width 0.12) (type solid)))')

    # Pin 1 marker
    p1x, p1y = top_positions[1]
    lines.append(f'  (fp_circle (center {p1x - 0.4} {p1y - 0.3}) (end {p1x - 0.25} {p1y - 0.3}) (layer "F.SilkS") (stroke (width 0.12) (type solid)))')

    # Fab outline
    lines.append(f'  (fp_line (start -{pkg_half} -{pkg_half}) (end {pkg_half} -{pkg_half}) (layer "F.Fab") (stroke (width 0.1) (type solid)))')
    lines.append(f'  (fp_line (start {pkg_half} -{pkg_half}) (end {pkg_half} {pkg_half}) (layer "F.Fab") (stroke (width 0.1) (type solid)))')
    lines.append(f'  (fp_line (start {pkg_half} {pkg_half}) (end -{pkg_half} {pkg_half}) (layer "F.Fab") (stroke (width 0.1) (type solid)))')
    lines.append(f'  (fp_line (start -{pkg_half} {pkg_half}) (end -{pkg_half} -{pkg_half}) (layer "F.Fab") (stroke (width 0.1) (type solid)))')

    # Courtyard
    lines.append(f'  (fp_line (start -{crtyd_half} -{crtyd_half}) (end {crtyd_half} -{crtyd_half}) (layer "F.CrtYd") (stroke (width 0.05) (type solid)))')
    lines.append(f'  (fp_line (start {crtyd_half} -{crtyd_half}) (end {crtyd_half} {crtyd_half}) (layer "F.CrtYd") (stroke (width 0.05) (type solid)))')
    lines.append(f'  (fp_line (start {crtyd_half} {crtyd_half}) (end -{crtyd_half} {crtyd_half}) (layer "F.CrtYd") (stroke (width 0.05) (type solid)))')
    lines.append(f'  (fp_line (start -{crtyd_half} {crtyd_half}) (end -{crtyd_half} -{crtyd_half}) (layer "F.CrtYd") (stroke (width 0.05) (type solid)))')

    # Pads
    for pin in sorted(top_positions.keys()):
        x, y = top_positions[pin]
        lines.append(f'  (pad "{pin}" smd rect (at {x} {y}) (size {PAD_SIZE} {PAD_SIZE}) (layers "F.Cu" "F.Paste" "F.Mask"))')

    lines.append(')')
    return '\n'.join(lines)


def print_comparison():
    """Print pin positions for verification."""
    bottom = get_pin_positions_bottom_view()

    print("PIN POSITIONS (Top View / KiCad coordinates)")
    print("=" * 60)
    print(f"{'Pin':>3} | {'X (mm)':>8} | {'Y (mm)':>8} | Notes")
    print("-" * 60)

    for pin in sorted(bottom.keys()):
        bx, by = bottom[pin]
        tx, ty = bottom_to_top_view(bx, by)
        notes = ""
        if pin in [42, 43, 44, 45]:
            notes = "VDD"
        elif pin in [19, 22, 25, 39]:
            notes = "GND"
        print(f"{pin:>3} | {tx:>8.3f} | {ty:>8.3f} | {notes}")


if __name__ == '__main__':
    print_comparison()
    print("\n")

    footprint = generate_footprint()
    print(footprint)

    # Save
    output = r"C:\Projects\Personal\Hardware\hw-rec-hj-n54l\parts\HJ_N54L_SIP\HJ_N54L_SIP.kicad_mod"
    with open(output, 'w') as f:
        f.write(footprint)
    print(f"\n\nSaved to: {output}")
