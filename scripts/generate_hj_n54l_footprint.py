#!/usr/bin/env python3
"""
Generate KiCad footprint for HJ-N54L_SIP module based on datasheet.

From datasheet "2.4 Pins distribution diagram" (BOTTOM VIEW):

         Col: 0   1   2   3   4   5   6   (7)
Row 0:        6   5   4   3   2   1   [PIN1 Mark]
Row 1:        7       29  28  27  26
Row 2:        8   30              41  25
Row 3:        9   31      43  42  40  24
Row 4:       10   32      44  45  39  23
Row 5:       11   33              38  22
Row 6:       12       34  35  36  37      21
Row 7:       13   14  15  16  17  18  19  20

Dimensions (from Figure 6.1):
- Package: 4.50 x 4.50 mm (NOM)
- Pad size: 0.35 x 0.35 mm (NOM)
- e1 = 0.55 mm (pitch)
- Grid span: 7 x e1 = 3.85mm width, ~7 x e1 height

For KiCad (TOP VIEW): mirror X axis from bottom view.
Pin 1 moves from right side to left side.
"""

# Datasheet parameters
PACKAGE_SIZE = 4.50  # mm
PAD_SIZE = 0.35      # mm
E1_PITCH = 0.55      # mm

# Grid: 7 columns (0-6) standard, row 7 has 8 positions
# Center the grid in the package
# Width: 6 intervals = 6 * 0.55 = 3.30mm, but row 7 needs 7 intervals = 3.85mm
# Height: 7 intervals = 7 * 0.55 = 3.85mm

# I'll use 7 columns (0-6) centered, plus column 7 for row 7 only
GRID_COLS = 7  # 0 to 6 standard
GRID_ROWS = 8  # 0 to 7

# Grid centered at package center
# X: columns 0-6, center at col 3
# Y: rows 0-7, center at row 3.5

def grid_to_bottom_view_mm(col, row):
    """Convert grid (col, row) to mm coordinates in BOTTOM VIEW.
    Col 0 = left, Col 6 = right (Col 7 for extended row)
    Row 0 = top, Row 7 = bottom
    Origin at center of grid.
    """
    x = (col - 3) * E1_PITCH      # Col 3 is center X
    y = (row - 3.5) * E1_PITCH    # Row 3.5 is center Y
    return (x, y)

def bottom_to_top_view(bx, by):
    """Convert bottom view coords to top view (mirror X)."""
    return (-bx, by)

def pin_position_top_view(col, row):
    """Get pin position in TOP VIEW (KiCad) coordinates."""
    bx, by = grid_to_bottom_view_mm(col, row)
    return bottom_to_top_view(bx, by)

# Pin positions in BOTTOM VIEW grid coordinates (col, row)
# From datasheet "2.4 Pins distribution diagram"
PIN_GRID = {
    # Row 0 (top of bottom view): pins 6,5,4,3,2,1 from left to right
    6: (0, 0),
    5: (1, 0),
    4: (2, 0),
    3: (3, 0),
    2: (4, 0),
    1: (5, 0),

    # Row 1
    7: (0, 1),
    29: (2, 1),
    28: (3, 1),
    27: (4, 1),
    26: (5, 1),

    # Row 2
    8: (0, 2),
    30: (1, 2),
    41: (5, 2),
    25: (6, 2),

    # Row 3
    9: (0, 3),
    31: (1, 3),
    43: (3, 3),
    42: (4, 3),
    40: (5, 3),
    24: (6, 3),

    # Row 4
    10: (0, 4),
    32: (1, 4),
    44: (3, 4),
    45: (4, 4),
    39: (5, 4),
    23: (6, 4),

    # Row 5
    11: (0, 5),
    33: (1, 5),
    38: (5, 5),
    22: (6, 5),

    # Row 6
    12: (0, 6),
    34: (2, 6),
    35: (3, 6),
    36: (4, 6),
    37: (5, 6),
    21: (6, 6),

    # Row 7 (bottom of bottom view): 8 pins
    13: (0, 7),
    14: (1, 7),
    15: (2, 7),
    16: (3, 7),
    17: (4, 7),
    18: (5, 7),
    19: (6, 7),
    20: (7, 7),  # Extended column
}

def generate_footprint():
    """Generate KiCad footprint file content."""

    pkg_half = PACKAGE_SIZE / 2   # 2.25mm
    silk_half = 2.35              # Silkscreen
    crtyd_half = 2.6              # Courtyard

    # Calculate pin positions in top view
    pins = {}
    for pin_num, (col, row) in PIN_GRID.items():
        x, y = pin_position_top_view(col, row)
        pins[pin_num] = (round(x, 3), round(y, 3))

    # Generate footprint
    lines = []
    lines.append('(footprint "HJ_N54L_SIP"')
    lines.append('  (version 20240108)')
    lines.append('  (generator "generate_hj_n54l_footprint.py")')
    lines.append('  (layer "F.Cu")')
    lines.append('  (descr "HJ-N54L_SIP LGA45 nRF54L15-based SiP module 4.5x4.5mm")')
    lines.append('  (attr smd)')

    # Reference and value text
    lines.append('  (fp_text reference "REF**" (at 0 -3.2) (layer "F.SilkS")')
    lines.append('    (effects (font (size 0.8 0.8) (thickness 0.12))))')
    lines.append('  (fp_text value "HJ_N54L_SIP" (at 0 3.2) (layer "F.Fab")')
    lines.append('    (effects (font (size 0.8 0.8) (thickness 0.12))))')

    # Silkscreen outline
    lines.append(f'  (fp_line (start -{silk_half} -{silk_half}) (end {silk_half} -{silk_half}) (layer "F.SilkS") (stroke (width 0.12) (type solid)))')
    lines.append(f'  (fp_line (start {silk_half} -{silk_half}) (end {silk_half} {silk_half}) (layer "F.SilkS") (stroke (width 0.12) (type solid)))')
    lines.append(f'  (fp_line (start {silk_half} {silk_half}) (end -{silk_half} {silk_half}) (layer "F.SilkS") (stroke (width 0.12) (type solid)))')
    lines.append(f'  (fp_line (start -{silk_half} {silk_half}) (end -{silk_half} -{silk_half}) (layer "F.SilkS") (stroke (width 0.12) (type solid)))')

    # Pin 1 marker - Pin 1 is at top-left in TOP VIEW after mirroring
    p1_x, p1_y = pins[1]
    marker_x = p1_x + 0.5  # To the right of pin 1 in top view
    marker_y = p1_y - 0.3  # Slightly above
    lines.append(f'  (fp_circle (center {marker_x} {marker_y}) (end {marker_x + 0.15} {marker_y}) (layer "F.SilkS") (stroke (width 0.12) (type solid)))')

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

    # Pads - sorted by pin number for readability
    for pin_num in sorted(pins.keys()):
        x, y = pins[pin_num]
        lines.append(f'  (pad "{pin_num}" smd rect (at {x} {y}) (size {PAD_SIZE} {PAD_SIZE}) (layers "F.Cu" "F.Paste" "F.Mask"))')

    lines.append(')')

    return '\n'.join(lines)


def print_pin_table():
    """Print pin positions for verification."""
    print("Pin positions in TOP VIEW (KiCad coordinates):")
    print("Pin\tX (mm)\tY (mm)\tGrid(col,row)")
    print("-" * 45)
    for pin_num in sorted(PIN_GRID.keys()):
        col, row = PIN_GRID[pin_num]
        x, y = pin_position_top_view(col, row)
        print(f"{pin_num}\t{x:.3f}\t{y:.3f}\t({col}, {row})")


if __name__ == '__main__':
    print_pin_table()
    print("\n" + "=" * 50 + "\n")

    footprint = generate_footprint()
    print(footprint)

    # Save to file
    output_path = r"C:\Projects\Personal\Hardware\hw-rec-hj-n54l\parts\HJ_N54L_SIP\HJ_N54L_SIP.kicad_mod"
    with open(output_path, 'w') as f:
        f.write(footprint)
    print(f"\n\nSaved to: {output_path}")
