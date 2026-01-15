# HJ-N54L_SIP MCU Module Design Validation Report

**Project:** Ultra-Compact BLE Audio Logger (hw-rec-hj-n54l)
**Date:** 2026-01-15
**Reference:** HJ-N54L_SIP Hardware Design Manual V1.1 (2025/10/09)

---

## Executive Summary

The HJ-N54L_SIP module implementation in `main.ato` has been exhaustively validated against the HJSIP Hardware Design Manual V1.1. The design is **COMPLIANT** with all critical requirements. No blocking issues were found.

| Category | Status |
|----------|--------|
| Power Supply Voltage | **PASS** |
| Crystal Oscillator Pin Handling | **PASS** |
| GPIO Pin Assignments | **PASS** |
| Antenna Configuration | **PASS** |
| Level Shifting (1.8V ↔ 3.3V) | **PASS** |
| Decoupling Capacitors | **PASS** |
| Hardware Layout Guidelines | **NOTED** |
| BOM/Assembly Notes | **PASS** |

---

## 1. Power Supply Configuration

### Datasheet Requirements (Table 4-2, page 11)

| Parameter | Min | Typ | Max | Unit |
|-----------|-----|-----|-----|------|
| VCC | 1.7 | 3.3 | 3.6 | V |
| VCC (extended temp) | 1.7 | 3.3 | 3.4 | V |

**Absolute Maximum (Table 4-1):**
- VCC max: 3.9V (3.7V for extended temperature)
- VI/O max: VCC + 0.3V (max 3.9V)

### Design Implementation (main.ato:316-317)

```ato
mcu.VDD ~ V3V3   # 3.3V from PMIC Buck2
mcu.GND ~ GND
```

### Validation Result: **PASS**

- Supply voltage: 3.3V (within 1.7V - 3.6V range)
- Well within absolute maximum of 3.9V
- Matches datasheet typical value exactly

---

## 2. Crystal Oscillator Pin Handling

### Datasheet Requirements (Table 2-2, page 7)

| Pin | Name | Description |
|-----|------|-------------|
| 12 | P1-01 | "An 32.768K crystal oscillator has been internally connected. **No other components can be connected to it**; otherwise, it will affect the oscillator's operation." |
| 34 | P1-00 | Same as above |

### Design Implementation (parts/HJ_N54L_SIP/HJ_N54L_SIP.ato:38-41)

```ato
# Note: P1_00 (pin 34) and P1_01 (pin 12) are connected to internal 32.768K crystal
# DO NOT CONNECT these pins externally - they are for internal LFXO only
signal P1_00_NC ~ pin 34
signal P1_01_NC ~ pin 12
```

### Validation Result: **PASS**

- Pins correctly marked as `_NC` (not connected)
- Comment explicitly documents the restriction
- No external connections to these pins in main.ato
- Design adheres to datasheet warning

---

## 3. GPIO Pin Assignment Verification

### Datasheet Pin Definition (Table 2-2, page 7)

| Pin | Datasheet Name | Part Definition | Used In Design | Function |
|-----|----------------|-----------------|----------------|----------|
| 1 | P0-00 | P0_00 | - | (unused) |
| 2 | SWDIO | SWDIO | pad_swdio | Debug data |
| 5 | P2-00 | P2_00 | level_shifter_thsel.B | AAD THSEL |
| 6 | P2-01 | P2_01 | level_shifter_wake.B | AAD WAKE |
| 7 | P1-07 | P1_07 | nand.CD_SDD32 | NAND CS |
| 8 | P1-02 | P1_02 | nand.SCLK (via R) | NAND CLK |
| 9 | P1-06 | P1_06 | level_shifter_clk.B | PDM CLK |
| 10 | P1-08 | P1_08 | pad_uart_tx | UART TX |
| 11 | P1-05 | P1_05 | level_shifter_data.B | PDM DATA |
| 18 | P1-10 | P1_10 | pad_uart_rx | UART RX |
| 23 | RF | RF | Antenna network | RF output |
| 24 | BOARD_ANT | BOARD_ANT | Antenna network | Built-in ANT |
| 26 | P0-03 | P0_03 | pmic.SDA, pad_i2c_sda | I2C SDA |
| 27 | P0-01 | P0_01 | pmic.SCL, pad_i2c_scl | I2C SCL |
| 28 | SWDCLK | SWDCLK | pad_swdclk | Debug clock |
| 30 | P1-03 | P1_03 | nand.CMD | NAND MOSI |
| 33 | P1-04 | P1_04 | nand.SDDO | NAND MISO |
| 37 | NRESET | NRESET | pad_reset | Reset |
| 42-45 | VDD_NRF | VDD | V3V3 | Power |
| 19,22,25,39 | GND | GND | GND | Ground |

### Validation Result: **PASS**

- All pin mappings match datasheet exactly
- Pin numbers correspond correctly to GPIO names
- Power and ground pins properly connected
- Debug interface (SWD) correctly routed
- No conflicts with reserved pins (P1_00, P1_01)

---

## 4. Antenna Configuration

### Datasheet Requirements (Section 3.2.1, page 9)

> "If using the build-in antenna, simply connect PIN23 and PIN24"
>
> "Depending on your product structure, to achieve the best antenna effect, an additional PI is required. Connect PIN23 to PIN24 through a π-type filter circuit."

**Figure 3.1 shows:** RF → Shunt C → Series element → Shunt C → BOARD_ANT

### Design Implementation (main.ato:301-338)

```ato
# PI topology: RF -> shunt C1 -> series R/L -> shunt C2 -> BOARD_ANT
# Default: shunt caps DNP (0pF), series element 0 ohm (pass-through)

# Shunt C1 to GND (RF side)
mcu.RF ~ c_ant_shunt1.p1
c_ant_shunt1.p2 ~ GND

# Series element (0 ohm default = direct connection)
mcu.RF ~ r_ant_series.p1
r_ant_series.p2 ~ mcu.BOARD_ANT

# Shunt C2 to GND (antenna side)
mcu.BOARD_ANT ~ c_ant_shunt2.p1
c_ant_shunt2.p2 ~ GND
```

**Components:**
- `c_ant_shunt1`: DNP_CAP_0201 (footprint only, no BOM)
- `r_ant_series`: 0Ω jumper (direct connection default)
- `c_ant_shunt2`: DNP_CAP_0201 (footprint only, no BOM)

### Validation Result: **PASS**

- PI matching network implemented per datasheet recommendation
- Default configuration: direct connection via 0Ω jumper
- DNP capacitor footprints available for post-assembly RF tuning
- Topology matches Figure 3.1 from datasheet
- Allows optimization without PCB respin

---

## 5. GPIO Voltage Level Analysis

### Datasheet Requirements (Table 4-3, page 11)

| Parameter | Threshold | At VCC=3.3V |
|-----------|-----------|-------------|
| Input Low (VIL) | 0 to 0.3×VCC | 0V to 0.99V |
| Input High (VIH) | 0.7×VCC to VCC | **2.31V to 3.3V** |
| Output Low (VOL) | 0 to 0.4V | 0V to 0.4V |
| Output High (VOH) | VCC-0.4V to VCC | 2.9V to 3.3V |

### Critical Analysis

**Problem:** The T5838 microphone operates at 1.8V. Its output high level is approximately:
- VOH ≈ 0.7 × 1.8V = **1.26V**

This is **below** the MCU's VIH threshold of **2.31V** (at 3.3V supply).

**Without level shifting, 1.8V signals would NOT reliably trigger 3.3V GPIO inputs.**

### Design Implementation

The design correctly implements bidirectional level shifters (SN74LVC1T45) for all mic signals:

| Signal | Direction | Level Shifter | MCU Pin | Status |
|--------|-----------|---------------|---------|--------|
| PDM CLK | MCU→Mic (3.3V→1.8V) | level_shifter_clk | P1_06 | **PASS** |
| PDM DATA | Mic→MCU (1.8V→3.3V) | level_shifter_data | P1_05 | **PASS** |
| THSEL | MCU→Mic (3.3V→1.8V) | level_shifter_thsel | P2_00 | **PASS** |
| WAKE | Mic→MCU (1.8V→3.3V) | level_shifter_wake | P2_01 | **PASS** |

### Validation Result: **PASS**

- Design correctly identifies voltage incompatibility (documented in main.ato:27-33)
- Level shifters properly translate between 1.8V and 3.3V domains
- Direction control correctly configured:
  - DIR=GND for B→A (3.3V to 1.8V): CLK, THSEL
  - DIR=V1V8 for A→B (1.8V to 3.3V): DATA, WAKE
- This implementation is **CRITICAL** and correctly handled

---

## 6. Decoupling Capacitors

### Datasheet Requirements (Section 5, page 12)

> "The filter capacitor at the power supply should be placed as close as possible to the power input pin of the module."
>
> "If it is capacitor-powered or space is limited, the filter capacitor at the power input can be removed as the module has an internal filter capacitor."

### Design Implementation (main.ato:146-152, 319-321)

```ato
# MCU decoupling
c_mcu_1 = new Capacitor
c_mcu_1.capacitance = 100nF +/- 20%
c_mcu_1.package = "0201"

c_mcu_2 = new Capacitor
c_mcu_2.capacitance = 100nF +/- 20%
c_mcu_2.package = "0201"

# MCU decoupling connections
c_mcu_1.p1 ~ V3V3; c_mcu_1.p2 ~ GND
c_mcu_2.p1 ~ V3V3; c_mcu_2.p2 ~ GND
```

### Validation Result: **PASS**

- Two 100nF decoupling capacitors provided
- Small 0201 package allows close placement to VDD pins
- Datasheet indicates internal capacitor exists, but external decoupling improves performance
- Design exceeds minimum requirement (datasheet allows omitting if space-limited)

---

## 7. Hardware Layout Guidelines

### Datasheet Requirements (Section 5, page 12)

| Guideline | Design Consideration |
|-----------|---------------------|
| "Module antenna should be placed at the edge of the circuit board, close to the main board edge or corner" | **LAYOUT NOTE** |
| "No other components should be placed near the antenna... or on its back, and no traces should be routed there" | **LAYOUT NOTE** |
| "Each layer of the circuit board should be fully covered with copper and connected to GND" | **LAYOUT NOTE** |
| "As many vias as possible should be drilled in the copper coverage area" | **LAYOUT NOTE** |
| "The module should not be placed in a metal shell" | **ENCLOSURE NOTE** |
| "Unused pins can be left floating" | **PASS** (design compliant) |
| "When the input power is not battery power... it is recommended to use a magnetic bead or inductor for filtering in series" | **N/A** (battery powered) |

### Validation Result: **NOTED**

These are PCB layout guidelines that must be verified during layout review:
1. MCU placed at board edge with antenna facing outward
2. Antenna area kept clear of components and traces
3. Solid ground plane under module (except antenna area)
4. Adequate via stitching around module

**Recommendation:** During layout review, verify compliance with Section 5 guidelines.

---

## 8. BOM and Assembly Notes

### Datasheet Context (page 4)

The HJ-N54L_SIP is available in three variants:
- SPPv2: Serial port transparent transmission
- CUSv2: Customized firmware
- **EMP: Customer development version** (for SDK development)

### Design Implementation (parts/HJ_N54L_SIP/HJ_N54L_SIP.ato:24-27)

```ato
# is_atomic_part provides manufacturer/partnumber for BOM identification
# Note: This is a CONSIGNED part - no LCSC number, customer must supply
# Assembly house: mark as "Customer Supplied" or "Consigned" in BOM notes
trait is_atomic_part<manufacturer="HJSIP", partnumber="HJ-N54L-SIP", ...>
```

### Validation Result: **PASS**

- Part correctly identified as consigned (customer-supplied)
- Manufacturer and part number documented for BOM
- Assembly notes indicate special handling required
- No LCSC number (not available in JLCPCB library - correct)

---

## 9. Interface Summary

### Used GPIO Pins

| Function | GPIO | Pin # | Interface | Notes |
|----------|------|-------|-----------|-------|
| I2C SDA | P0_03 | 26 | PMIC, Debug | 4.7kΩ pull-up to V3V3 |
| I2C SCL | P0_01 | 27 | PMIC, Debug | 4.7kΩ pull-up to V3V3 |
| NAND CLK | P1_02 | 8 | SD-NAND | Via 33Ω series R |
| NAND CMD | P1_03 | 30 | SD-NAND | 10kΩ pull-up |
| NAND DAT0 | P1_04 | 33 | SD-NAND | 10kΩ pull-up |
| PDM DATA | P1_05 | 11 | Mic | Via level shifter |
| PDM CLK | P1_06 | 9 | Mic | Via level shifter + 33Ω |
| NAND CS | P1_07 | 7 | SD-NAND | 10kΩ pull-up |
| UART TX | P1_08 | 10 | Debug | Direct |
| UART RX | P1_10 | 18 | Debug | Direct |
| AAD THSEL | P2_00 | 5 | Mic | Via level shifter |
| AAD WAKE | P2_01 | 6 | Mic | Via level shifter |

### Reserved Pins (NOT USED - Correct)

| GPIO | Pin # | Reason |
|------|-------|--------|
| P1_00 | 34 | Internal 32.768kHz crystal |
| P1_01 | 12 | Internal 32.768kHz crystal |

### Unused GPIO Pins (Available for Future Use)

P0_00, P0_02, P0_04, P1_09, P1_11, P1_12, P1_13, P1_14, P1_15, P2_02, P2_03, P2_04, P2_05, P2_06, P2_07, P2_08, P2_09, P2_10

---

## 10. Electrical Compatibility Matrix

| Interface | MCU Voltage | External Voltage | Level Shift | Status |
|-----------|-------------|------------------|-------------|--------|
| PMIC I2C | 3.3V | 3.3V (VDDIO) | No | **PASS** |
| SD-NAND | 3.3V | 3.3V | No | **PASS** |
| Microphone | 3.3V | 1.8V | Yes (4x LS) | **PASS** |
| Debug (SWD) | 3.3V | 3.3V | No | **PASS** |
| UART | 3.3V | 3.3V | No | **PASS** |

---

## Conclusion

The HJ-N54L_SIP module design is **fully compliant** with the HJSIP Hardware Design Manual V1.1:

### Compliance Summary

| Requirement | Status |
|-------------|--------|
| Supply voltage within 1.7-3.6V range | **COMPLIANT** (3.3V) |
| Crystal pins (P1_00/P1_01) not connected | **COMPLIANT** |
| Antenna PI network per datasheet | **COMPLIANT** |
| Level shifting for 1.8V mic interface | **COMPLIANT** |
| Decoupling capacitors present | **COMPLIANT** |
| Pin assignments match datasheet | **COMPLIANT** |
| Consigned part documentation | **COMPLIANT** |

### Layout Review Checklist

The following must be verified during PCB layout review:

- [ ] MCU positioned at board edge/corner with antenna outward
- [ ] No components or traces in antenna keepout area
- [ ] No components on PCB back under antenna area
- [ ] Solid GND copper pour (except antenna region)
- [ ] Via stitching around module perimeter
- [ ] Decoupling caps placed close to VDD pins (42-45)
- [ ] RF trace impedance controlled (50Ω)

**No hardware changes required.** The design correctly implements all datasheet requirements.

---

*Report generated from analysis of main.ato and parts/HJ_N54L_SIP/HJ_N54L_SIP.ato against HJ-N54L_SIP Hardware Design Manual V1.1*
