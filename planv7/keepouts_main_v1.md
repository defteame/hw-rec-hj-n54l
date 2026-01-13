# Main Board Keepouts & Zones (Current State)

## Board Outline
- Circular board
- Diameter: 18.6 mm
- Radius: 9.3 mm
- Origin (0,0) at center

## RF Antenna Keepout
- Applies to: All copper layers, vias, components
- Region:
    X ∈ [-4.6, +4.6] mm
    Y ∈ [+4.0, +9.3] mm
- Only allowed component: HJ-N54L_SIP module body
- No copper pour, no traces, no vias

## Microphone Acoustic Keepout
- Center: (0.0, -6.6) mm
- NPTH hole: Ø0.8 mm
- Clearance radius: 1.5 mm
- No copper, no vias, no solder paste

## Switching Regulator Keepout
- Around PMIC SW pins, inductors L1/L2
- No sensitive signals (PDM, RF, I2C) routed underneath

## Ground Strategy
- Solid GND plane on B.Cu
- GND pour on F.Cu except antenna keepout
- Via stitching around perimeter except antenna arc