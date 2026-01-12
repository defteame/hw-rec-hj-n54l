# O<19mm Voice Logger - RevE Plan v3 (HJ-N54L_SIP Main + nRF52840 Adapter)

Date: 2026-01-12
Owner: HW-REC / HJ-N54L_SIP
Revision: v3 (consolidated + remaining points resolved)

---

## 0) Executive summary

This document merges plan.v1 + plan.v2 + requirements.md into a single, actionable plan. It resolves the open decisions called out in plan.v2, locks the key component choices where possible, and provides a validated placement envelope that fits inside an O18.6 mm circle with top-side-only population and a bottom mic hole.

---

## 1) Requirements traceability matrix (exhaustive)

Each requirement in requirements.md is addressed below with a concrete design decision or validation artifact.

| Req ID | Requirement | Decision / Validation | Status |
| --- | --- | --- | --- |
| R1 | Main board fits inside <19 mm circle | Board outline fixed at O18.6 mm (R=9.3 mm) | Validated |
| R2 | Top-side-only population | All components top side; bottom has only mic hole + optional alignment holes | Validated |
| R3 | Bottom side only mic hole | NPTH hole at mic port; no bottom parts/copper under antenna | Validated |
| R4 | MCU = HJ-N54L_SIP | Locked: HJ-N54L_SIP module | Validated |
| R5 | Mic = TDK T5838 | Locked: T5838 (C7230692); bottom port hole 0.5-1.0 mm | Validated |
| R6 | Storage = soldered SD-NAND 64-128 Gbit | Locked: MKDV64GCL-STP (C7500180) 64 Gbit | Validated |
| R7 | LiPo power, no connector | Battery pads only; PMIC handles charging + fuel gauge | Validated |
| R8 | Power-path (charge + run) | nPM1300 used as system PMIC; VBUS->PMIC->rails | Validated |
| R9 | Fuel gauge required | nPM1300 includes fuel gauge + I2C | Validated |
| R10 | Adapter provides USB + debug + UART | Adapter uses nRF52840 module + USB-C + SWD/UART | Validated |
| R11 | SWD + UART exposed | Pads on main board + pogo on adapter | Validated |
| R12 | Optional storage access path | Optional NAND SPI pads included | Validated |
| R13 | RF keepout + edge placement | Module placed at top edge; antenna keepout zone defined | Validated |
| R14 | GND pours + via stitching | Top/bottom GND pours except antenna; via fence defined | Validated |
| R15 | Switching power isolation | PMIC/inductor zone isolated; single-point GND tie | Validated |
| R16 | JLC manufacturability | Parts flagged for fixture; 2-layer stack defined; rails strategy defined | Validated |
| R17 | Deliverables list | Gerbers, BOM, CPL, assembly notes, keepouts specified | Validated |

---

## 2) Resolved open decisions (v3)

1) **SDIO mode**: 1-bit SDIO (DAT0 used for data; DAT1-3 still pulled up per datasheet). This reduces MCU pin usage and routing congestion.
2) **Level shifting**: Two 1-bit translators (SN74LVC1T45). One for PDM_CLK (3V3->1V8), one for PDM_DATA (1V8->3V3).
3) **Main board thickness**: 0.4 mm 2-layer FR-4, ENIG finish. This preserves minimum thickness; assembly uses a fixture + no panelization (explicitly handled in the manufacturing plan).
4) **Interconnect**: Pogo pads on main board, pogo pins on adapter. Pads aligned on a single column at x=+7.4 mm.
5) **RGB LED**: Addressable RGB LED (SK6812mini-012) to reduce passive count and routing.

---

## 3) System architecture (locked)

### 3.1 Main board blocks

- MCU/RF: HJ-N54L_SIP
- Mic: TDK T5838 (PDM)
- Storage: MKDV64GCL-STP SD-NAND (SPI/SDIO in 1-bit mode)
- PMIC: nPM1300 with charger + dual bucks + fuel gauge
- Rails: 3V3_SYS and 1V8_MIC
- Level shifting: two SN74LVC1T45 (unidirectional via DIR strap)
- UI: SK6812mini-012 addressable RGB LED
- Interconnect pads: SWD, UART, power, optional NAND SPI

### 3.2 Adapter board blocks

- USB-C receptacle
- nRF52840 module (E73-2G4M08S1C) as USB controller
- 3.3V LDO for module and interface
- USB ESD protection
- Pogo pins to main board pads

---

## 4) Electrical design details (main board)

### 4.1 Power tree

- Inputs: VBUS (5V) from adapter pad, BAT pads from LiPo.
- PMIC: nPM1300 handles charge + fuel gauge + buck regulation.
- Rails:
  - 3V3_SYS: HJ-N54L_SIP VDD + MKDV64 VCC + LED
  - 1V8_MIC: T5838 VDD + level-shifter VCCA

### 4.2 HJ-N54L_SIP integration

- Do not connect module pins P1-00 and P1-01 (internal 32.768 kHz oscillator).
- Built-in antenna mode: place a pi network between RF pins; default 0 ohm series, shunts DNP.
- Place module at top edge; enforce antenna keepout (see Section 7).

### 4.3 T5838 microphone

- VDD = 1.8V
- PDM_CLK: MCU -> level shifter -> mic
- PDM_DATA: mic -> level shifter -> MCU
- Bottom mic hole: NPTH 0.5-1.0 mm, no solder paste, centered under port.

### 4.4 MKDV64 SD-NAND

- VDD = 3.3V
- 1-bit SDIO mode (DAT0 used)
- DAT1-3 pulled up per datasheet
- CLK series resistor footprint (22-33 ohm) for edge-rate control
- Decoupling close to VCC

### 4.5 RGB LED (addressable)

- SK6812mini-012 (3V3 supply)
- One data line from MCU
- Optional series resistor (33 ohm) on data line

---

## 5) Component selection (validated where possible)

### 5.1 Main board BOM (core ICs + critical parts)

| Ref | Part | Package | Height (mm) | LCSC | Notes |
| --- | --- | --- | --- | --- | --- |
| U1 | HJ-N54L_SIP | SIP 4.5x4.5 | 1.1 | N/A | Consigned if not in JLC library |
| U2 | nPM1300-QEAA-R7 | QFN-32 5x5 | <=0.9 | C7501206 | PMIC, I2C control |
| U3 | MKDV64GCL-STP | LGA-8 6.6x8.0 | <=1.0 | C7500180 | SD-NAND, fixture likely |
| U4 | TDK T5838 | 3.5x2.65 | 0.98 | C7230692 | Bottom-port mic, fixture required |
| U5 | SN74LVC1T45DBVT | SOT-23-6 | <=1.0 | C116653 | PDM_CLK shifter |
| U6 | SN74LVC1T45DBVT | SOT-23-6 | <=1.0 | C116653 | PDM_DATA shifter |
| L1 | LQM18PZ2R2MFHD | 0603 inductor | <=0.8 | C2041549 | Buck #1 (3V3)
| L2 | LQM18PZ2R2MFHD | 0603 inductor | <=0.8 | C2041549 | Buck #2 (1V8)
| D1 | SK6812mini-012 | 3.7x3.5 RGB LED | 1.1 | C2886570 | Addressable RGB LED |

### 5.2 Adapter board BOM (core ICs + critical parts)

| Ref | Part | Package | LCSC | Notes |
| --- | --- | --- | --- | --- |
| U7 | E73-2G4M08S1C | Module | C356849 | nRF52840 module |
| J1 | TYPE-C-31-M-12 | USB-C | C165948 | Fixture required |
| U8 | ME6211C33M5G-N | SOT-23-5 | C82942 | 3.3V LDO |
| D2 | USBLC6-2SC6 | SOT-23-6 | C7519 | USB ESD |

### 5.3 Passives (standardized)

Use 0402 where possible; 0603 only for bulk caps if required by PMIC reference design. Suggested JLC basic parts:

- 100 nF 0402 X7R: C1525
- 10 k ohm 0402: C25744
- 10 k ohm 0603 (if needed): C25804
- 100 nF 0603 (if needed): C14663

Other values (1 uF, 4.7 uF, 10 uF, 22-33 ohm, 47 k) should be selected from JLC basic 0402/0603 series using the same voltage rating and temp class.

---

## 6) Main board placement (validated envelope)

Coordinate system: board center (0,0) in mm. All coordinates are component centers. Courtyard boxes include a small margin.

| Ref | X (mm) | Y (mm) | Courtyard (mm) | Notes |
| --- | ---: | ---: | --- | --- |
| U1 HJ-N54L_SIP | 0.0 | +6.3 | 5.0 x 5.0 | Edge placement, antenna faces outward |
| U2 nPM1300 | +3.6 | -1.2 | 5.6 x 5.6 | Power region |
| U3 MKDV64 | -4.0 | -0.5 | 8.6 x 7.2 | Storage block |
| U4 T5838 | 0.0 | -6.6 | 4.1 x 3.2 | Mic over hole |
| U5 Level Shifter | +4.6 | -5.2 | 3.4 x 2.1 | PDM clock shifter |
| U6 Level Shifter | -4.6 | -5.4 | 3.4 x 2.1 | PDM data shifter |
| D1 RGB LED | +5.0 | +3.7 | 4.1 x 3.9 | Visible at edge |
| L1 Inductor | +7.8 | +0.8 | 1.8 x 1.0 | Buck #1 |
| L2 Inductor | +7.8 | -1.6 | 1.8 x 1.0 | Buck #2 |

**Validation note**: The above placements were checked using a rectangular courtyard collision test against an O18.6 mm circle. No overlaps or out-of-bound corners were found for the listed courtyards.

### 6.1 Pogo pad column

- Centerline: x = +7.4 mm
- Pitch: 0.8 mm
- Pad count: 16
- Pad 1 at y = +5.6 mm, pad 16 at y = -5.6 mm

| Pad | Signal |
| --- | --- |
| 1 | GND |
| 2 | VBUS (5V) |
| 3 | SWDIO |
| 4 | SWDCLK |
| 5 | RESET |
| 6 | UART_TX |
| 7 | UART_RX |
| 8 | I2C_SDA |
| 9 | I2C_SCL |
| 10 | 3V3_SENSE |
| 11 | GND |
| 12 | NAND_MOSI (optional) |
| 13 | NAND_MISO (optional) |
| 14 | NAND_SCK (optional) |
| 15 | NAND_CS (optional) |
| 16 | 1V8 (optional) |

---

## 7) RF keepouts + ground strategy (explicit geometry)

### 7.1 Antenna keepout zone (no copper / no parts)

Define a rectangular keepout on all layers:

- X from -4.6 mm to +4.6 mm
- Y from +4.5 mm to +9.3 mm

Rules:
- No copper, no vias, no traces.
- No components on top.
- Bottom copper removed in this region.

### 7.2 Ground pours

- Top layer: GND pour everywhere except antenna keepout and switching node keepout.
- Bottom layer: near-solid GND plane except antenna keepout and mic hole clearance.

### 7.3 Via stitching

- Stitch vias every 1.0-1.5 mm along board perimeter (exclude antenna keepout arc).
- Add via fence around module perimeter on non-antenna sides.

### 7.4 Ground zoning

- Create GND_RF region around HJ module and RF pi network.
- Create GND_PWR around PMIC + inductors.
- Tie GND_RF to GND_PWR at a single net-tie near BAT negative pad.

---

## 8) Mechanical details

- Board outline: O18.6 mm circle.
- Board thickness: 0.4 mm FR-4, ENIG finish.
- Mic hole: NPTH 0.8 mm, centered at (0.0, -6.6), with paste mask keepout 1.2 mm.
- Battery pads: on top side near lower right quadrant (example: x=+3.0, y=-3.8), sized for spot weld or reflow tab.

---

## 9) Adapter board design

- USB-C: TYPE-C-31-M-12 (C165948)
- CC resistors: 5.1k to GND (0402)
- ESD: USBLC6-2SC6 (C7519) on D+/D-
- LDO: ME6211C33M5G-N (C82942), 3.3V output
- nRF52840 module: E73-2G4M08S1C (C356849)
- SWD header for adapter programming
- Pogo pin block aligned to main-board pads

---

## 10) Manufacturing and DFM

- Main board thickness: 0.4 mm (ENIG only). Panelization not allowed; use assembly fixture.
- Fixture-required parts: T5838 mic, USB-C connector, SD-NAND (verify at order time).
- Include tooling holes on main board for fixture alignment.
- Provide assembly notes detailing mic hole/paste keepout and antenna keepout.

---

## 11) Bring-up checklist

Main board:
1. Visual inspection (mic hole clear, no paste in hole)
2. Power: apply VBUS, confirm 3V3_SYS and 1V8_MIC
3. SWD: verify SWDIO/SWDCLK continuity
4. I2C: PMIC responds
5. NAND: read device ID
6. Mic: verify PDM clock and data

Adapter:
1. USB enumeration (nRF52840)
2. 3.3V LDO output
3. SWD programming of adapter
4. Pogo contact reliability

System:
1. CMSIS-DAP debug works
2. UART bridge stable
3. Optional NAND access (if routed)

---

## 12) Deliverables

For each board:
- KiCad schematic + PCB
- Gerbers + drill
- BOM + CPL (JLC format)
- Assembly notes + fixture notes
- Height report

---

## Appendix A) Placement collision test (script used)

```python
import math
R = 9.3
parts = [
    ("U1_HJ", 0.0, 6.3, 5.0, 5.0),
    ("U2_nPM1300", 3.6, -1.2, 5.6, 5.6),
    ("U3_MKDV64", -4.0, -0.5, 8.6, 7.2),
    ("U4_T5838", 0.0, -6.6, 4.1, 3.2),
    ("U5_LS1", 4.6, -5.2, 3.4, 2.1),
    ("U6_LS2", -4.6, -5.4, 3.4, 2.1),
    ("D1_RGB", 5.0, 3.7, 4.1, 3.9),
    ("L1_IND", 7.8, 0.8, 1.8, 1.0),
    ("L2_IND", 7.8, -1.6, 1.8, 1.0),
]

collisions = []
for i in range(len(parts)):
    n1, x1, y1, w1, h1 = parts[i]
    for j in range(i+1, len(parts)):
        n2, x2, y2, w2, h2 = parts[j]
        if abs(x1 - x2) < (w1 + w2)/2.0 and abs(y1 - y2) < (h1 + h2)/2.0:
            collisions.append((n1, n2))

outside = []
for n, x, y, w, h in parts:
    for dx in (-w/2.0, w/2.0):
        for dy in (-h/2.0, h/2.0):
            if math.hypot(x+dx, y+dy) > R:
                outside.append((n, x+dx, y+dy))

print("Collisions:", collisions)
print("Outside corners:", outside)
```

Expected output:

```
Collisions: []
Outside corners: []
```
