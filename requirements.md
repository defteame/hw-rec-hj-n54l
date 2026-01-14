# Requirements v2 — Ultra-Compact BLE Audio Logger (Main Board + USB Adapter)

**Document Version:** 2.0
**Date:** 2026-01-14
**Status:** Implementation Complete

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
| Level Shifter (×2) | SN74LVC1T45DPKR | Texas Instruments | X2SON-6 1×1mm | C2878065 |

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
| V3V3 | 3.3V | PMIC Buck2 (VOUT2) | MCU, NAND, level shifters (VCCB) |
| V1V8 | 1.8V | PMIC Buck1 (VOUT1) | Microphone, level shifters (VCCA) |

### nPM1300 PMIC Configuration

**Critical Design Decisions:**

1. **VSYS/PVDD Topology**: PVDD fed from VSYS (not VBAT directly) per Nordic reference design
2. **VBUSOUT**: **LEFT UNCONNECTED** but **STILL DECOUPLED** with 1µF capacitor — per nPM1300 datasheet, VBUSOUT is "for host sensing" and "should not be used as a source". The capacitor is required per Nordic reference design. Do NOT tie to VSYS.
3. **Buck Assignment**:
   - Buck1 (VOUT1) → 1.8V (VSET1 = 47kΩ to GND)
   - Buck2 (VOUT2) → 3.3V (VSET2 = 470kΩ to GND)
4. **VSET Resistors**: MANDATORY — floating VSET pins cause undefined behavior
5. **NTC**: Tied to GND via 0Ω (disable NTC function in firmware)
6. **SHPHLD**: Left floating (internal pull-up) — do NOT tie to V3V3

### Decoupling Strategy

| Location | Capacitance | Package | Notes |
|----------|-------------|---------|-------|
| VBUS | 10µF + 100nF | 0603/0201 | Bulk + HF |
| VBAT | 10µF | 0603 | Bulk |
| VSYS | 10µF | 0603 | Required per nPM1300 ref |
| VDDIO | 1µF | 0402 | Per nPM1300 reference |
| V3V3 | 10µF + 100nF | 0603/0201 | Bulk + HF |
| V1V8 | 10µF + 100nF | 0603/0201 | Bulk + HF |
| MCU | 2× 100nF | 0201 | Per HJ-N54L guidance |
| NAND | 100nF + 2.2µF | 0201/0402 | HF + bulk |

---

## 4) Storage Interface (SD-NAND)

### Part: CS CSNP64GCR01-BOW (64Gbit / 8GB)

**Interface Mode:** SPI (nRF54L15 lacks SDMMC peripheral)

**Pin Mapping:**

| Signal | NAND Pin | MCU Pin | Notes |
|--------|----------|---------|-------|
| SCLK | Pin 3 | P1_02 | Via 33Ω series resistor |
| CMD (MOSI) | Pin 5 | P1_03 | 10kΩ pull-up to V3V3 |
| SDDO (MISO/DAT0) | Pin 6 | P1_04 | 10kΩ pull-up to V3V3 |
| CD_SDD32 (CS/DAT3) | Pin 2 | P1_07 | 10kΩ pull-up + MCU control |
| SDD1 (DAT1) | Pin 7 | NC | 10kΩ pull-up to V3V3 |
| SDD2 (DAT2) | Pin 1 | NC | 10kΩ pull-up to V3V3 |
| VCC | Pin 8 | V3V3 | — |
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
| CLK | 6 | Level shifter A | PDM clock input |
| DATA | 1 | Level shifter A | PDM data output |
| SELECT | 2 | GND | L/R channel select (low = left) |
| THSEL | 5 | GND | Threshold select (low = lower) |
| WAKE | 4 | NC | **Leave unconnected** — output pin |

**WAKE Pin Warning:** WAKE is an OUTPUT that drives high during wake events. Tying to GND or VDD causes shorts.

### Level Shifting (SN74LVC1T45DPKR)

Required because MCU runs at 3.3V, microphone at 1.8V.

**CLK Path (MCU → Mic):**
- VCCA = 1.8V, VCCB = 3.3V
- DIR = GND (B→A direction)
- B ← MCU P1_06, A → Mic CLK

**DATA Path (Mic → MCU):**
- VCCA = 1.8V, VCCB = 3.3V
- DIR = V1V8 (A→B direction) — **MUST be VCCA domain, not VCCB**
- A ← Mic DATA, B → MCU P1_05

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
| 10 | V3V3_SENSE | — | Power rail monitor |
| 11-14 | NAND_* | — | Direct NAND access (CLK, CMD, DAT0, CS) |

### I2C Bus

- **Pull-ups:** 4.7kΩ to V3V3 on SDA and SCL
- **Devices:** nPM1300 PMIC (address configurable via firmware)

---

## 8) Mechanical Constraints

### Main Board

| Parameter | Value | Notes |
|-----------|-------|-------|
| Board outline | Ø18.6mm circle | Fits <19mm requirement |
| Component placement | Top-side only | Bottom reserved for mic hole |
| PCB thickness | 0.4mm target | 0.6/0.8mm fallback if needed |
| Layer count | 4 layers | Signal-GND-GND-Signal |

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

### SD-NAND Access

1. Initialize SPI at low speed (400kHz)
2. Send CMD0 with CS low to enter SPI mode
3. Increase clock after initialization (up to 50MHz)

### PDM Audio

- Configure PDM peripheral on P1_05 (DATA) and P1_06 (CLK)
- Sample rate: typically 16kHz–48kHz
- Use EasyDMA for efficient capture

---

## 11) Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-XX-XX | Initial requirements |
| 2.0 | 2026-01-14 | Updated to reflect implementation: new NAND (CS CSNP64GCR01-BOW), HJ-N54L_SIP module, T5838 mic with SnapEDA footprint, nPM1300 power topology fixes, level shifter DIR domain fix, DNP antenna caps, complete pin mapping |
| 2.1 | 2026-01-14 | Fixed VBUSOUT documentation (sensing only, not connected); NAND footprint corrected to 8-pin (removed erroneous pad 9); PDM DATA bias resistor marked DNP per T5838 datasheet guidance |

---

## 12) References

- [HJ-N54L_SIP Hardware Design Manual V1.1](docs/)
- [nPM1300 Product Specification](https://www.nordicsemi.com/Products/nPM1300)
- [T5838 Datasheet](https://invensense.tdk.com/download-pdf/t5838-datasheet/)
- [SN74LVC1T45 Datasheet](https://www.ti.com/product/SN74LVC1T45)
- [CS CSNP64GCR01-BOW (LCSC C41380595)](https://www.lcsc.com/product-detail/C41380595.html)
