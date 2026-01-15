# T5838 MEMS Microphone Design Validation Report

**Project:** HJ-N54L Ultra-Compact BLE Audio Logger
**Component:** TDK T5838 PDM Digital MEMS Microphone (MMICT5838-00-012)
**Datasheet Reference:** DS-000383 Rev 1.1 (April 21, 2023)
**Validation Date:** 2026-01-15
**Status:** PASS with Minor Documentation Corrections

---

## Executive Summary

The T5838 microphone subsystem design has been exhaustively validated against the TDK datasheet. The design is **electrically correct and safe**. All critical requirements are met, including voltage levels, level shifting, decoupling, and signal integrity. One documentation error was identified in the code comments regarding absolute maximum ratings.

| Category | Status | Notes |
|----------|--------|-------|
| Power Supply | PASS | 1.8V within spec |
| Absolute Maximum Ratings | PASS | Level shifting protects mic |
| Level Shifting | PASS | All 4 signals correctly shifted |
| Decoupling | PASS | 100nF per datasheet |
| Pin Configuration | PASS | All pins correctly connected |
| PDM Interface | PASS | No bias on DATA line |
| AAD Interface | PASS | THSEL/WAKE level shifted |
| Footprint/Pinout | PASS | SnapEDA footprint with acoustic port |

---

## 1. Power Supply Validation

### Datasheet Specification (Table 1, Page 5)
| Parameter | Min | Typ | Max | Unit |
|-----------|-----|-----|-----|------|
| Supply Voltage (VDD) | 1.62 | 1.8 | 1.98 | V |

### Design Implementation
```
mic.VDD ~ V1V8    (main.ato:466)
```

**Validation:** PASS
- V1V8 rail is 1.8V from PMIC Buck1
- VSET1 strap (47kΩ) configures Buck1 for 1.8V output
- Well within the 1.62V-1.98V operating range

---

## 2. Absolute Maximum Ratings Validation

### Datasheet Specification (Table 8, Page 9)
| Parameter | Rating |
|-----------|--------|
| Supply Voltage (VDD) | −0.3V to +1.98V |
| **Digital Pin Input Voltage** | **−0.3V to VDD + 0.3V or 1.98V, whichever is less** |

### Critical Analysis
With VDD = 1.8V:
- Calculated limit: VDD + 0.3V = 2.1V
- Datasheet ceiling: 1.98V
- **Actual absolute maximum: min(2.1V, 1.98V) = 1.98V**

### Documentation Correction Required

**Current Comment (main.ato:28):**
```
# T5838 absolute max is VDD+0.3V = 2.28V (NOT 3.3V tolerant!)
```

**Correct Statement:**
```
# T5838 absolute max is min(VDD+0.3V, 1.98V) = 1.98V (NOT 3.3V tolerant!)
```

**Impact:** None - the level shifting implementation is still correct. The design properly level-shifts all signals from 3.3V to 1.8V, which is well below the 1.98V limit.

**Validation:** PASS (implementation correct, comment needs update)

---

## 3. Level Shifting Validation

### Requirement Analysis
The MCU operates at 3.3V. The T5838 has:
- Absolute max input: 1.98V
- VOH (output high): 0.7 × VDD = 1.26V @ 1.8V

3.3V signals would exceed absolute max by **1.32V** (67% over limit).
1.26V mic outputs would not meet 3.3V MCU VIH (~2.31V).

**Level shifting is MANDATORY in both directions.**

### SN74LVC1T45 Direction Control (per TI datasheet)
| DIR Pin | Direction |
|---------|-----------|
| LOW (GND) | B → A (VCCB to VCCA) |
| HIGH (VCCA) | A → B (VCCA to VCCB) |

**Critical Note:** DIR pin is powered by VCCA domain. Driving DIR from VCCB when VCCA < VCCB causes back-powering issues.

### Signal-by-Signal Validation

#### 3.1 PDM Clock (MCU → Mic)
| Parameter | Required | Implemented | Status |
|-----------|----------|-------------|--------|
| Direction | 3.3V → 1.8V | B → A | PASS |
| VCCA | 1.8V | V1V8 | PASS |
| VCCB | 3.3V | V3V3 | PASS |
| DIR | LOW | GND | PASS |
| Series Resistor | Recommended | 33Ω | PASS |

```ato
level_shifter_clk.VCCA ~ V1V8
level_shifter_clk.VCCB ~ V3V3
level_shifter_clk.DIR ~ GND           # B→A direction
level_shifter_clk.B ~ mcu.P1_06       # MCU side (3.3V)
level_shifter_clk.A ~ r_pdm_clk.p1    # Mic side (1.8V)
r_pdm_clk.p2 ~ mic.CLK
```

#### 3.2 PDM Data (Mic → MCU)
| Parameter | Required | Implemented | Status |
|-----------|----------|-------------|--------|
| Direction | 1.8V → 3.3V | A → B | PASS |
| VCCA | 1.8V | V1V8 | PASS |
| VCCB | 3.3V | V3V3 | PASS |
| DIR | HIGH (VCCA domain) | V1V8 | PASS |

```ato
level_shifter_data.VCCA ~ V1V8
level_shifter_data.VCCB ~ V3V3
level_shifter_data.DIR ~ V1V8         # A→B direction (VCCA domain!)
level_shifter_data.A ~ mic.DATA       # Mic side (1.8V)
level_shifter_data.B ~ mcu.P1_05      # MCU side (3.3V)
```

#### 3.3 THSEL - AAD Configuration (MCU → Mic)
| Parameter | Required | Implemented | Status |
|-----------|----------|-------------|--------|
| Direction | 3.3V → 1.8V | B → A | PASS |
| DIR | LOW | GND | PASS |

```ato
level_shifter_thsel.DIR ~ GND         # B→A direction
level_shifter_thsel.B ~ mcu.P2_00     # MCU side (3.3V)
level_shifter_thsel.A ~ mic.THSEL     # Mic side (1.8V)
```

#### 3.4 WAKE - AAD Interrupt (Mic → MCU)
| Parameter | Required | Implemented | Status |
|-----------|----------|-------------|--------|
| Direction | 1.8V → 3.3V | A → B | PASS |
| DIR | HIGH (VCCA domain) | V1V8 | PASS |

```ato
level_shifter_wake.DIR ~ V1V8         # A→B direction (VCCA domain!)
level_shifter_wake.A ~ mic.WAKE       # Mic side (1.8V)
level_shifter_wake.B ~ mcu.P2_01      # MCU side (3.3V)
```

**Validation:** PASS - All level shifters correctly configured

---

## 4. Decoupling Capacitor Validation

### Datasheet Requirement (Page 11, Table 10)
> "For best performance and to avoid potential parasitic artifacts, place a 0.1 µF (100 nF) ceramic type X7R capacitor between Pin 7 (VDD) and ground. Place the capacitor as close to Pin 7 as possible."

### Design Implementation
```ato
c_mic = new Capacitor
c_mic.capacitance = 100nF +/- 20%
c_mic.package = "0201"

c_mic.p1 ~ V1V8; c_mic.p2 ~ GND
```

**Validation:** PASS
- 100nF matches datasheet specification
- 0201 package suitable for compact design
- Layout placement should be verified for proximity to VDD pin

---

## 5. Pin Configuration Validation

### Datasheet Pin Function (Table 10, Page 11)
| Pin | Name | Function | Design Connection | Status |
|-----|------|----------|-------------------|--------|
| 1 | DATA | PDM output | level_shifter_data.A | PASS |
| 2 | SELECT | Channel select | GND (Right/DATA1) | PASS |
| 3 | GND | Ground | (via 31/32) | PASS |
| 4 | WAKE | AAD interrupt | level_shifter_wake.A | PASS |
| 5 | THSEL | AAD config | level_shifter_thsel.A | PASS |
| 6 | CLK | Clock input | r_pdm_clk.p2 | PASS |
| 7 | VDD | Power | V1V8 | PASS |
| 31/32 | GND | Ground pads | GND | PASS |

### SELECT Pin Configuration
| SELECT State | Channel | Output |
|--------------|---------|--------|
| LOW (GND) | Right | DATA1 |
| HIGH (VDD) | Left | DATA2 |

Design uses `mic.SELECT ~ GND` for Right channel (DATA1).

**Validation:** PASS

### Ground Pad Note
The SnapEDA footprint uses pins 31 and 32 as split GND pads around the acoustic port, instead of pin 3. This is an acceptable footprint variation - the component definition correctly connects both:
```ato
signal GND ~ pin 31
GND ~ pin 32
```

---

## 6. PDM Data Line Validation

### Datasheet Warning (Page 31)
> "Do not use a pull-up or pull-down resistor on the PDM data signal line because it can pull the signal to an incorrect state during the period that the signal line is tristated."

### Design Implementation
```ato
# PDM DATA weak bias resistor (DNP by default - DO NOT POPULATE)
# T5838 datasheet explicitly warns against pull-up/down on PDM data line
# Keep footprint only for debug optionality
r_pdm_data_bias = new DNP_RES_0201_package

mic.DATA ~ r_pdm_data_bias.p1
r_pdm_data_bias.p2 ~ GND
```

**Validation:** PASS
- DNP (Do Not Populate) by default
- Comment correctly warns against population
- Footprint retained for debug only

---

## 7. Clock Specifications

### Datasheet Requirements (Table 7, Page 7)
| Mode | Clock Frequency | Current |
|------|-----------------|---------|
| Sleep | < 200 kHz | 9 µA (clk on) / 0.8 µA (clk off) |
| Low-Power | 400 - 800 kHz | 120 µA |
| High Quality | 2.0 - 3.7 MHz | 310 µA |
| Ultrasonic | 4.2 - 4.8 MHz | 500 µA |

| Timing Parameter | Min | Max | Unit |
|------------------|-----|-----|------|
| Clock Duty Cycle | 45 | 55 | % |
| Rise Time (10%-90%) | - | 25 | ns |
| Fall Time (90%-10%) | - | 25 | ns |

### Design Considerations
- Clock frequency is controlled by firmware (PDM peripheral configuration)
- 33Ω series resistor provides edge rate control
- Rise/fall time depends on trace capacitance + 33Ω RC constant

**Validation:** PASS (hardware provisions correct; firmware must configure appropriate frequency)

---

## 8. Digital I/O Characteristics

### Datasheet Specifications (Table 6, Page 7)
| Parameter | Condition | Value |
|-----------|-----------|-------|
| VIH (Input High) | - | 0.65 × VDD = 1.17V |
| VIL (Input Low) | - | 0.35 × VDD = 0.63V |
| VOH (Output High) | ILOAD = 0.5mA | 0.7 × VDD = 1.26V |
| VOL (Output Low) | ILOAD = 0.5mA | 0.3 × VDD = 0.54V |

### Level Shift Analysis

**CLK Input to Mic (after level shift):**
- SN74LVC1T45 with VCCA=1.8V outputs up to 1.8V
- 1.8V > VIH (1.17V) ✓
- 0V < VIL (0.63V) ✓

**DATA Output from Mic (before level shift):**
- VOH = 1.26V → level shifted to 3.3V domain
- VOL = 0.54V → level shifted to 0V domain

**Validation:** PASS

---

## 9. AAD (Acoustic Activity Detect) Interface

### Datasheet Guidance (Table 10, Page 11)
> THSEL: "For operation without AAD modes, this pin can be tied to Gnd or left as No Connect."
> WAKE: "For operation without AAD modes, this pin can be tied to Gnd or left as No Connect."

### Design Implementation
The design includes full AAD support with level-shifted THSEL and WAKE connections:
- THSEL allows MCU to configure AAD threshold via one-wire protocol
- WAKE provides interrupt output when acoustic activity exceeds threshold

**One-Wire Protocol Requirements (Page 17):**
- Requires CLK > 50 kHz for write operations
- THSEL pulse widths referenced to CLK cycles

**Validation:** PASS - Full AAD support correctly implemented

---

## 10. Footprint and Mechanical Validation

### Datasheet Specifications (Page 34, 36)
| Parameter | Value |
|-----------|-------|
| Package | 3.5 × 2.65 × 0.98 mm LGA |
| Sound Port | Bottom port, Ø0.375 mm min |
| PCB Hole | Ø0.5-1.0 mm recommended |

### Footprint Analysis
The SnapEDA footprint (MIC_T5838.kicad_mod) includes:
- Correct pad dimensions per datasheet Figure 32
- Non-plated through-hole (NPTH) for acoustic port: Ø0.5mm
- Split GND pads (31/32) around acoustic port
- Solder paste apertures per datasheet Figure 33

**Validation:** PASS

---

## 11. Summary of Findings

### Compliant Items (No Action Required)
| Item | Reference | Status |
|------|-----------|--------|
| Supply voltage 1.8V | DS Page 5 | COMPLIANT |
| 100nF decoupling capacitor | DS Page 11 | COMPLIANT |
| Level shifting (all 4 signals) | DS Page 9 | COMPLIANT |
| DIR pin powered by VCCA | TI datasheet | COMPLIANT |
| SELECT tied to GND | DS Page 11 | COMPLIANT |
| No pull-up/down on DATA | DS Page 31 | COMPLIANT |
| Series resistor on CLK | Best practice | COMPLIANT |
| Dual GND pads connected | Footprint | COMPLIANT |
| AAD pins level-shifted | DS Page 9 | COMPLIANT |
| Acoustic port in footprint | DS Page 34 | COMPLIANT |

### Items Requiring Attention

#### Documentation Correction (Non-Critical)
**File:** `main.ato` line 28
**Current:**
```
# T5838 absolute max is VDD+0.3V = 2.28V (NOT 3.3V tolerant!)
```
**Corrected:**
```
# T5838 absolute max is min(VDD+0.3V, 1.98V) = 1.98V (NOT 3.3V tolerant!)
```
**Impact:** Documentation only - hardware implementation is correct.

#### Layout Verification Recommended
- Verify decoupling capacitor (c_mic) is placed as close as possible to mic pin 7 (VDD)
- Verify acoustic port PCB hole is not obstructed
- Verify 33Ω series resistor placement doesn't add excessive trace length to CLK

---

## 12. Firmware Considerations

The following firmware requirements stem from this hardware design:

1. **Clock Frequency Selection:**
   - High Quality Mode: 2.0-3.7 MHz, 68 dBA SNR
   - Low-Power Mode: 400-800 kHz, 65 dBA SNR
   - Sleep Mode: < 200 kHz or OFF

2. **PDM Interface Configuration:**
   - MCU pins: P1_05 (DATA), P1_06 (CLK)
   - Standard PDM peripheral, Right channel (DATA1)

3. **AAD Configuration (if used):**
   - MCU pins: P2_00 (THSEL), P2_01 (WAKE)
   - One-wire protocol on THSEL requires CLK > 50 kHz
   - WAKE is interrupt output (active HIGH)

4. **Startup Timing:**
   - Power-on to stable output: ~6 ms
   - Wake from sleep: ~6 ms
   - Mode switching: ~3.5 ms

---

## 13. References

1. TDK T5838 Datasheet, DS-000383 Rev 1.1, April 21, 2023
2. Texas Instruments SN74LVC1T45 Datasheet
3. AN-000298: T583x MEMS Microphone Acoustic Activity Detect User Guide
4. AN-1003: Recommendations for Mounting and Connecting TDK Bottom-Ported MEMS Microphones

---

**Report Prepared By:** Claude (AI Assistant)
**Validation Methodology:** Line-by-line comparison of main.ato design against DS-000383 specifications
**Conclusion:** Design is compliant with T5838 datasheet requirements. Safe for fabrication.
