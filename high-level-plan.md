# Plan - Ultra-Compact BLE Audio Logger (Main Board + USB Adapter)

**Document Version:** 2.4
**Date:** 2026-01-15
**Status:** Implementation Complete (fix6.md + fix7.md + fix8.md applied)

---

## 1) Summary / What we are building

A **two-board system**:

* **Main board (device PCB)**: Ultra-thin, ultra-compact PCB that fits inside **Ø18.6mm circle**, captures audio from a **TDK T5838 PDM microphone**, stores to **soldered SD-NAND**, runs from **single-cell LiPo** with integrated charging + fuel gauging via **nPM1300 PMIC**.

* **Adapter board (USB accessory)**: USB-C board for **charging**, **debugging**, **UART access**, and optional future **mass-storage gateway**. Uses **nRF52840 module** as USB controller (nRF54L15 has no USB peripheral).

---

## 2) Bill of Materials — Key Components

### Main Board

| Function | Part Number | Manufacturer | Package | LCSC |
|----------|-------------|--------------|---------|------|
| MCU/Radio | HJ-N54L_SIP | HJSIP | LGA45 4.5×4.5mm | Consigned |
| PMIC | nPM1300-QEAA-R7 | Nordic | QFN24 5×5mm | C5307841 |
| Storage | CSNP64GCR01-BOW | CS | LGA-8 8.5×7.0mm | C41380595 |
| Microphone | T5838 (MMICT5838-00-012) | TDK InvenSense | 3.5×2.65×0.98mm | C7230692 |
| Level Shifter (×1) | SN74AXC4T774RSVR | Texas Instruments | UQFN-16 1.8×2.6mm | C1849454 |

### Adapter Board

| Function | Part Number | Manufacturer | Package |
|----------|-------------|--------------|---------|
| USB Controller | E73-2G4M08S1C | Ebyte | Module |
| USB-C Connector | TYPE-C-31-M-12 | Korean Hroparts | SMD |
| LDO | ME6211C33M5G-N | Nanjing Micro One | SOT23-5 |

---

## 3) Power Architecture

### Power Rails

| Rail | Voltage | Source | Consumers |
|------|---------|--------|-----------|
| VBUS | 5V | USB-C input | PMIC input |
| VBAT | 3.0–4.2V | LiPo battery | PMIC input |
| VSYS | ~VBAT/VBUS | PMIC VSYS output | Buck inputs (PVDD) |
| V3V0 | 3.0V | PMIC Buck2 (VOUT2) | MCU, NAND, level shifter (VCCB) |
| V1V8 | 1.8V | PMIC Buck1 (VOUT1) | Microphone, level shifter (VCCA) |

### nPM1300 PMIC Configuration

**Critical Design Decisions:**

1. **VSYS/PVDD Topology**: PVDD fed from VSYS (not VBAT directly) per Nordic reference design
2. **VBUSOUT**: **LEFT UNCONNECTED** but **STILL DECOUPLED** with 1µF capacitor — per nPM1300 datasheet, VBUSOUT is "for host sensing" and "should not be used as a source". The capacitor is required per Nordic reference design. Do NOT tie to VSYS.
3. **Buck Assignment** (fix7.md: changed VOUT2 from 3.3V to 3.0V for better battery operation):
   - Buck1 (VOUT1) → 1.8V (VSET1 = 47kΩ to GND)
   - Buck2 (VOUT2) → 3.0V (VSET2 = 150kΩ to GND)
4. **VSET Resistors**: MANDATORY — floating VSET pins cause undefined behavior
5. **NTC**: Tied to GND via 0Ω (disable NTC function in firmware)
6. **SHPHLD**: Has internal pull-up; **EXPOSED VIA POGO PAD** for ship mode recovery
7. **CC1/CC2 (USB Type-C)**: **INTENTIONALLY NOT CONNECTED** — see section below

### CC Pin Decision (fix6.md, fix8.md APPROVED)

The nPM1300 CC1/CC2 pins are **intentionally left floating (NC)** — 100mA VBUS limit accepted:

- **Rationale**: Main board has no USB-C connector; VBUS arrives via pogo pads from adapter board which already handles CC termination
- **Consequence**: VBUS current limit defaults to 100mA until firmware configures higher
- **Solution**: Firmware must set current limit via I2C on VBUS detect (see Firmware section)
- **fix8.md Review**: Confirmed acceptable for this design — treat VBUS as generic 5V input

### SHPHLD Pin Exposure (fix6.md, fix8.md VERIFIED)

The SHPHLD pin is **exposed via pogo pad** on the main board with **direct connection** (no series resistor):

- **Purpose**: Provides physical recovery from ship/hibernate mode without requiring VBUS
- **Connection**: DIRECT (no series resistor) — VIL max is 0.4V, internal pull-up is ~50kΩ; any series resistor >1kΩ would prevent valid LOW detection
- **Behavior**:
  - Pull low > tshipToActive: wakes device and triggers internal reset
  - Long low > tRESETBUT (normal mode): causes power cycle
- **Adapter Implementation**: Add momentary button or shortable pad pair from SHPHLD to GND

### Decoupling Strategy

| Location | Capacitance | Package | Notes |
|----------|-------------|---------|-------|
| VBUS | 10µF + 100nF | 0603/0201 | Bulk + HF |
| VBAT | 10µF | 0603 | Bulk |
| VSYS | 10µF | 0603 | Required per nPM1300 ref |
| VDDIO | 1µF | 0402 | Per nPM1300 reference |
| V3V0 | 10µF + 100nF | 0603/0201 | Bulk + HF |
| V1V8 | 10µF + 100nF | 0603/0201 | Bulk + HF |
| MCU | 2× 100nF | 0201 | Per HJ-N54L guidance |
| NAND | 100nF + 2.2µF | 0201/0402 | HF + bulk |
| Level Shifter | 2× 100nF | 0201 | One per rail (VCCA, VCCB) — fix7.md reduced from 8 caps |

---

## 4) Storage Interface (SD-NAND)

### Part: CS CSNP64GCR01-BOW (64Gbit / 8GB)

**Interface Mode:** SPI (nRF54L15 lacks SDMMC peripheral)

**Pin Mapping:**

| Signal | NAND Pin | MCU Pin | Notes |
|--------|----------|---------|-------|
| SCLK | Pin 3 | P1_02 | Via 33Ω series resistor |
| CMD (MOSI) | Pin 5 | P1_03 | 10kΩ pull-up to V3V0 |
| SDDO (MISO/DAT0) | Pin 6 | P1_04 | 10kΩ pull-up to V3V0 |
| CD_SDD32 (CS/DAT3) | Pin 2 | P1_07 | 10kΩ pull-up + MCU control |
| SDD1 (DAT1) | Pin 7 | NC | 10kΩ pull-up to V3V0 |
| SDD2 (DAT2) | Pin 1 | NC | 10kΩ pull-up to V3V0 |
| VCC | Pin 8 | V3V0 | — |
| VSS | Pin 4 | GND | — |

**Design Notes:**
- All data lines require 10kΩ pull-ups per SD specification
- CLK uses 33Ω series resistor for edge rate control
- DAT3 (CD_SDD32) pulled low enters SPI mode; MCU controls as CS

---

## 5) Audio Subsystem

### Microphone: TDK T5838

**Key Specifications:**
- PDM digital output
- Operating voltage: 1.62V–3.6V (running at 1.8V)
- Bottom-port MEMS with acoustic wake-on-sound (AAD)

**Pin Configuration:**

| Signal | Pin | Connection | Notes |
|--------|-----|------------|-------|
| VDD | 7 | V1V8 | 100nF decoupling |
| GND | 31, 32 | GND | Dual ground pads |
| CLK | 6 | Level shifter A | PDM clock input (via 33Ω series R) |
| DATA | 1 | Level shifter A | PDM data output |
| SELECT | 2 | GND | L/R channel select (low = left) |
| THSEL | 5 | Level shifter A | AAD threshold config (1-wire serial) |
| WAKE | 4 | Level shifter A | AAD interrupt output |

**CRITICAL: All mic signals MUST be level shifted!**
- T5838 absolute max: VDD+0.3V = 2.1V (NOT 3.0V tolerant!)
- 3.0V directly on any pin will damage the mic
- 1.8V output (VOH ~1.26V) won't reliably trigger 3.0V MCU VIH (~2.1V)

**PDM DATA Warning:** T5838 datasheet explicitly warns: **NO pull-up/pull-down on DATA line**. A DNP bias resistor footprint is included for debug only.

### Level Shifting (SN74AXC4T774RSVR × 1) — fix7.md

Required because MCU runs at 3.0V, microphone at 1.8V. Single 4-bit translator with independent direction control per channel replaces 4× 1-bit translators (reduced BOM count, smaller footprint).

**SN74AXC4T774 Direction Control:**
- DIRx LOW = B→A (3.0V to 1.8V)
- DIRx HIGH = A→B (1.8V to 3.0V)
- **CRITICAL**: DIR pins powered by VCCA domain — use V1V8 for DIR=HIGH, NOT V3V0!
- nOE = active low (tie to GND to enable all channels)

**Note:** SN74AXC4T774 has weak internal pull-downs on data I/Os. T5838 datasheet warns against pull-ups/pull-downs on PDM DATA, but weak internal pulls are typically acceptable for single-mic designs.

**Channel Assignments:**

| Channel | Signal | Direction | DIRx | Path |
|---------|--------|-----------|------|------|
| 1 | CLK | MCU→Mic | GND (B→A) | B1 ← MCU P1_06, A1 → 33Ω → Mic CLK |
| 2 | DATA | Mic→MCU | V1V8 (A→B) | A2 ← Mic DATA, B2 → MCU P1_05 |
| 3 | THSEL | MCU→Mic | GND (B→A) | B3 ← MCU P2_00, A3 → Mic THSEL |
| 4 | WAKE | Mic→MCU | V1V8 (A→B) | A4 ← Mic WAKE, B4 → MCU P2_01 |

---

## 6) RF / Antenna

### HJ-N54L_SIP Module

- Built-in 2.4GHz antenna (BLE 6.0)
- Internal 32.768kHz crystal (P1_00/P1_01 reserved — do not connect)
- RF and BOARD_ANT pins for antenna matching

### PI Matching Network

**Topology:** RF → Shunt C1 → Series R/L → Shunt C2 → BOARD_ANT

**Default Configuration (DNP for tuning):**
- C1 (shunt, RF side): DNP footprint (0201)
- Series element: 0Ω jumper (0201)
- C2 (shunt, antenna side): DNP footprint (0201)

**DNP Implementation:** Custom `DNP_CAP_0201` footprint with `in_bom = no` — provides pads without BOM entry for post-assembly tuning.

---

## 7) Debug & External Interfaces

### Pogo Pad Interface (Main ↔ Adapter)

| Pad | Signal | MCU Pin | Notes |
|-----|--------|---------|-------|
| 1 | VBUS | — | 5V USB power |
| 2 | GND | — | Ground (multiple recommended) |
| 3 | SWDIO | Pin 2 | Debug data |
| 4 | SWDCLK | Pin 28 | Debug clock |
| 5 | NRESET | Pin 37 | Reset |
| 6 | UART_TX | P1_08 | Serial transmit |
| 7 | UART_RX | P1_10 | Serial receive |
| 8 | I2C_SDA | P0_03 | Shared with PMIC |
| 9 | I2C_SCL | P0_01 | Shared with PMIC |
| 10 | VOUT2_SENSE | — | 3.0V power rail monitor (fix8.md: renamed from V3V0_SENSE) |
| 11-14 | NAND_* | — | Direct NAND access (CLK, CMD, DAT0, CS) |
| 15 | SHPHLD | PMIC | Ship/hibernate wake (fix6.md) |

**SHPHLD Pad Usage (fix6.md):**
- Connect to momentary button to GND on adapter, or shortable pad pair
- Pull low > tshipToActive to wake from ship/hibernate mode
- Pull low > tRESETBUT to trigger power cycle in normal mode
- Provides physical recovery without requiring VBUS connection

### I2C Bus

- **Pull-ups:** 4.7kΩ to V3V0 on SDA and SCL
- **Devices:** nPM1300 PMIC (address configurable via firmware)

---

## 8) Mechanical Constraints

### Main Board

| Parameter | Value | Notes |
|-----------|-------|-------|
| Board outline | Ø18.6mm circle | Fits <19mm requirement |
| Component placement | Top-side only | Bottom reserved for mic hole |
| PCB thickness | 0.4mm | 4-layer |
| Layer count | 4 layers | Signal-GND-Power-Signal |

### Board Stackup Decision (fix8.md APPROVED)

**Chosen: 4-layer, 0.4mm at PCBWay**

**Rationale:**
- **RF + Switching + Digital**: Design has two buck converters + BLE radio + high-speed SPI — requires solid ground plane for EMI containment
- **Ground Plane**: Layer 2 provides continuous reference plane for RF and switching noise
- **Power Distribution**: Layer 3 provides power plane / routing flexibility
- **Ultra-thin**: 0.4mm meets "thin board" requirement while maintaining signal integrity
- **nPM1300 Guidance**: Nordic explicitly recommends "minimum 2-layer PCB including ground plane; no components on bottom layer" — 4-layer exceeds this

**Alternative Rejected:**
- 2-layer 0.2mm: Higher EMI/noise risk, trickier routing for this complexity level

**PCBWay Capability Notes:**
- 4-layer minimum thickness: 0.6mm standard, **0.4mm**
- Board size 19mm diameter falls in "10-20mm engineer review" zone — expect DFM review
- Panelization required for assembly (min panel size ~100×120mm)

### Component Placement Priority

1. MCU at board edge (antenna facing outward)
2. PMIC + inductors isolated from antenna
3. Mic centered with bottom acoustic port
4. NAND positioned for shortest SPI traces

---

## 9) Manufacturing (JLCPCB)

### Assembly Notes

| Component | Assembly Type | Notes |
|-----------|---------------|-------|
| HJ-N54L_SIP | Consigned | Customer-supplied |
| NAND (LGA-8) | Standard PCBA | May require fixture |
| 0201 passives | Standard PCBA | Dense placement |
| DNP caps | Exclude from BOM | `in_bom = no` |

### Panelization

- Circular board requires mouse-bite or tab routing
- Edge rails minimum 5mm
- Fiducials required for assembly

---

## 10) Firmware Configuration Notes

### nPM1300 Initialization

1. Disable NTC monitoring (BCHGDISABLESET register)
2. Configure fuel gauge parameters
3. Verify buck voltages via VOUT1/VOUT2 readback

### VBUS Current Limit Configuration (CRITICAL - fix6.md)

Since CC1/CC2 are not connected, VBUS current limit defaults to 100mA. Firmware **MUST** configure higher limit on VBUS detect:

**I2C Configuration:**
- Address: 0x6B (7-bit)
- VBUSIN register block base: 0x0200

**Initialization Sequence (run on every VBUS detect):**
```
1. Write register 0x0201 (VBUSINILIM0) = 0x00  // Set 500mA limit
2. Write register 0x0200 (TASKUPDATEILIMSW) = 0x01  // Apply limit
```

**Important Notes:**
- VBUS removal resets to VBUSINILIMSTARTUP (100mA default)
- Must re-run sequence after each VBUS replug
- Can poll VBUSINSTATUS (0x0207) to detect VBUS presence
- Consider implementing in both main MCU and adapter MCU for redundancy

### SD-NAND Access

1. Initialize SPI at low speed (400kHz)
2. Send CMD0 with CS low to enter SPI mode
3. Increase clock after initialization (up to 50MHz)

### PDM Audio

- Configure PDM peripheral on P1_05 (DATA) and P1_06 (CLK)
- Sample rate: typically 16kHz–48kHz
- Use EasyDMA for efficient capture

### AAD (Acoustic Activity Detection)

- THSEL (P2_00): Configure one-wire serial protocol for AAD threshold
- WAKE (P2_01): Configure as GPIO input with interrupt for AAD events
- Both signals level-shifted (3.0V MCU ↔ 1.8V mic domain)

---

## 11) Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-XX-XX | Initial requirements |
| 2.0 | 2026-01-14 | Updated to reflect implementation: new NAND (CS CSNP64GCR01-BOW), HJ-N54L_SIP module, T5838 mic with SnapEDA footprint, nPM1300 power topology fixes, level shifter DIR domain fix, DNP antenna caps, complete pin mapping |
| 2.1 | 2026-01-14 | Fixed VBUSOUT documentation (sensing only, not connected); NAND footprint corrected to 8-pin (removed erroneous pad 9); PDM DATA bias resistor marked DNP per T5838 datasheet guidance |
| 2.2 | 2026-01-15 | **fix6.md implementation**: Added SHPHLD pogo pad for ship mode recovery; documented CC1/CC2 as intentionally NC; added VBUS current limit firmware requirement (must set 500mA via I2C); added THSEL/WAKE level shifters for full AAD support; added HJ-N54L_SIP BOM metadata (consigned part); comprehensive design decision documentation |
| 2.3 | 2026-01-15 | **fix7.md implementation**: Changed VOUT2 from 3.3V to 3.0V (VSET2: 470kΩ→150kΩ) for better battery operation; consolidated 4× SN74LVC1T45DPKR into 1× SN74AXC4T774RSVR (4-bit translator with independent DIR per channel); reduced level shifter decoupling from 8 caps to 2; added BOM exploder script for PCBWay assembly |
| 2.4 | 2026-01-15 | **fix8.md implementation**: Verified SHPHLD direct connection (no series resistor - VIL 0.4V requirement); approved CC floating decision (100mA VBUS limit accepted); renamed V3V3/pad_3v3_sense → V3V0/pad_vout2_sense (signal name matches actual 3.0V voltage); verified DNP parts properly marked; updated all 3.3V references to 3.0V; documented board stackup decision (4-layer 0.4mm PCBWay) |

---

## 12) References

- [HJ-N54L_SIP Hardware Design Manual V1.1](docs/)
- [nPM1300 Product Specification](https://www.nordicsemi.com/Products/nPM1300)
- [T5838 Datasheet](https://invensense.tdk.com/download-pdf/t5838-datasheet/)
- [SN74AXC4T774 Datasheet](https://www.ti.com/product/SN74AXC4T774)
- [CS CSNP64GCR01-BOW (LCSC C41380595)](https://www.lcsc.com/product-detail/C41380595.html)
