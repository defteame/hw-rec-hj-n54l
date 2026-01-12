# High-Level Requirements — Ultra-Compact BLE Audio Logger (Main Board + USB Adapter)

## 1) Summary / What we are building

We are building a **two-board system**:

* **Main board (device PCB)**: an **ultra-thin, ultra-compact** PCB that fits inside a **<19 mm diameter circle**, captures audio from a **TDK T5838 PDM microphone**, stores it to **soldered SD-NAND** (no microSD), and runs from a **single-cell LiPo** with integrated **charging + fuel gauging**.
* **Adapter board (USB accessory)**: a USB-C board used for **charging**, **debugging**, **UART access**, and (optionally) a future **mass-storage gateway**. Because the nRF54L15 platform has no USB peripheral, the adapter board uses an **nRF52840 module** as the USB controller.

---

## 2) Goals and priorities

### Primary goals

1. **Minimum assembled thickness** of the main board (battery excluded), while still meeting all other constraints.
2. Main board **must fit within <19 mm circle**.
3. **Manufacturable at JLCPCB** (PCB + PCBA), with documented constraints and ordering approach.
4. Hardware supports **high quality audio capture** (software/codec work is out of scope for this requirements doc).

### Secondary goals

* Robust debug and data access through the adapter board
* RF performance “good enough” for BLE connectivity in a small wearable form factor (final target defined in verification)

---

## 3) System architecture

### Main board (device PCB)

**Core components**

* MCU/radio: **HJ-N54L_SIP** module (nRF54L15-based SiP) with integrated RF subsystem
* Microphone: **TDK T5838** bottom-port PDM mic with AAD capability
* Storage: **MKDV64GCL-STP (64 Gbit / ~8 GB)** SD-NAND (soldered)
* Power: **nPM1300** PMIC (battery charging, regulation, fuel gauge, I²C control)
* UI: **1× RGB LED**
* Interconnect: **board-to-board pads** (preferred) for pogo-pin adapter interface

**Main board functional behaviors**

* Capture PDM audio and store to soldered NAND
* Operate from LiPo when disconnected
* Charge LiPo when external power present (via adapter or external pads)
* Expose SWD + UART + power through the board-to-board interface

### Adapter board (USB accessory)

**Core components**

* USB controller: **nRF52840 module** (to avoid discrete RF/crystal complexity)
* USB-C receptacle
* Power regulation for adapter board electronics
* Pogo pins (or board-to-board connector) to mate with main board pads

**Adapter functional behaviors**

* Provide USB-C power to main board for charging/power-path operation
* Provide CMSIS-DAP-style SWD debugging (firmware implementation later)
* Provide UART bridge(s) over USB (firmware later)
* Optional future: provide “mass storage mode” access path (hardware support now, firmware later)

---

## 4) Hard constraints (must not violate)

### 4.1 Main board mechanical

* **Board outline**: must fit inside **<19 mm diameter circle** (recommend design target ≤18.6 mm for margin).
* **Top-side only population**: all components must be on the **top**; **no components on bottom**.
* **Bottom**: may only include the **microphone acoustic hole** and (if needed) mechanical alignment holes/slots.
* **Battery attachment**: battery mounts above the PCB; **battery connection is via pads**, not a connector.

### 4.2 Main board electrical

* Must support:

  * **LiPo charge** from external power
  * **fuel gauge** reporting (I²C)
  * stable system rails for MCU + NAND + mic
* Storage must be **soldered** and sized **64–128 Gbit** (8–16 GB target), not removable media.

### 4.3 Main board RF

* Module antenna behavior must be preserved via strict **antenna keepout**, **edge placement**, and **grounding strategy** per module guidance (details in §7).

### 4.4 Adapter board

* Must provide:

  * USB-C input for power + data
  * nRF52840-based USB device functions (debug/UART gateway)
  * physical mating to main board (pogo preferred)
  * SWD access for both boards (adapter SWD header + SWD to main board)

---

## 5) Interfaces and exposed signals

### 5.1 Main ↔ Adapter interface (minimum set)

The interconnect MUST provide:

* **VBUS (5 V)**
* **GND** (multiple pins recommended)
* **SWDIO, SWDCLK, RESET**
* **UART TX/RX** (at minimum one UART)

### 5.2 Optional interface expansions (recommended)

* I²C (PMIC access via adapter if needed)
* Additional GPIOs for future sensors/buttons
* Optional SPI signals to enable future direct NAND access modes (tradeoff vs routing complexity)

---

## 6) Power and rails (high-level)

* PMIC must support:

  * LiPo charging from 5 V input
  * power-path or equivalent behavior (system can run while charging)
  * fuel gauge telemetry
* Rails:

  * **3.3 V domain** for NAND and module IO (unless module is run lower and level shifting is used—this is a design choice)
  * **1.8 V rail** for microphone supply and any 1.8 V logic

---

## 7) RF + layout grounding requirements (main board)

### 7.1 Antenna mode

* Default: use **module built-in antenna**.
* Board MUST include footprints to support:

  * built-in antenna coupling network (typically a 0 Ω + optional π-network pads), OR
  * optional external antenna mode (if enclosure forces it)

### 7.2 Placement requirements

* The HJ-N54L_SIP module MUST be placed at the **edge/corner** of the PCB with antenna region facing outward.
* No components may be placed in the antenna keepout region.
* No traces/vias/copper pours may be present in prohibited antenna keepout zones (all layers).

### 7.3 Ground pours / via stitching

* Use ground pours/planes on all layers **except where prohibited by antenna keepout**.
* Use dense via stitching around the module ground region, excluding antenna keepout.

### 7.4 Switching power isolation (if buck used)

* Switching loops (PMIC + inductor + caps) must be physically separated from antenna region.
* If needed, implement a “quiet RF ground” vs “power ground” strategy with a controlled tie point (net-tie / 0 Ω footprint).

---

## 8) Manufacturing and DFM requirements (JLCPCB focus)

### 8.1 Main board thickness target and constraints

* Target PCB thickness: **0.4 mm** (to minimize total assembled thickness).
* If 0.4 mm manufacturing/assembly constraints make the design infeasible, acceptable fallback thicknesses are **0.6 mm or 0.8 mm** with a documented rationale.

### 8.2 Surface finish and tolerance

* For 0.4 mm boards, only specific finishes may be acceptable and thickness tolerance must be accounted for in the mechanical stack.

### 8.3 Assembly process requirements

* Some parts may require:

  * **Standard PCBA only** (not Economic)
  * **PCB assembly fixtures**
  * **edge rails** and **fiducials**
* For circular boards, the panelization/rail strategy MUST be explicitly defined in the manufacturing package.

### 8.4 Deliverables for fabrication and assembly

The project MUST produce:

* Gerbers + drill files (including NPTH mic hole)
* BOM + CPL/PNP files compatible with JLC
* Assembly notes covering:

  * mic hole/paste keepout
  * antenna keepouts
  * edge rails/panelization approach
  * any fixture-required parts and handling notes

---

## 9) Verification / acceptance criteria (hardware)

* **Mechanical**

  * Main PCB fits within <19 mm circle
  * No bottom components; mic hole aligned and unobstructed
  * Total main PCB assembly thickness meets target (define numeric target per revision)
* **Power**

  * Charges LiPo from adapter USB-C power
  * Fuel gauge is readable via I²C
  * Stable rails under expected peak load
* **Storage**

  * NAND initializes and supports sustained read/write at required clock rate
* **Audio**

  * PDM clock/data integrity validated at the MCU input
* **Debug / adapter**

  * Adapter enumerates over USB
  * Main board SWD is accessible through adapter interface
  * UART bridge works reliably at target baud

---

## 10) Non-goals (explicitly out of scope)

* Opus encoding implementation details
* File system and host tooling
* Final enclosure mechanical design (only PCB-level keepouts/pad locations are covered)
* BLE firmware profile/UX

---

## 11) Open decisions / risks (must be resolved early)

* **PCBA strategy for small circular board** (edge rails vs panel vs fixture) while targeting **0.4 mm** thickness
* Whether HJ-N54L_SIP is available as a JLC “stock” part or must be customer-supplied
* Whether to support future **direct NAND access** from adapter (extra pins + bus isolation)
* Final antenna mode choice once enclosure + battery placement is known

---

## Validation sources used (so you can justify constraints)

* JLCPCB 0.4 mm constraints: ENIG only, no panelization, not available for 1-layer; thickness tolerance ±10%. ([JLCPCB][1])
* JLCPCB fabrication sizing: min single board 5×5 mm; V-cut panel min 70×70 mm. ([JLCPCB][2])
* Standard PCBA edge rails + fiducials guidance (rails ≥5 mm; fiducials ~1 mm, etc.). ([JLCPCB][3])
* Mouse-bite panelization guidance incl. circular board note. ([JLCPCB][4])
* SD-NAND (C7500180) requires fixture and is “Standard Only” for PCBA. ([JLCPCB][5])
* nPM1300 key features (charger, buck regulators, fuel gauge, I²C control, USB-C compatible). ([Nordic Semiconductor][6])
* T5838 official datasheet download page (versioned datasheet available). ([TDK InvenSense][7])

---

## Optional: link list to paste into your repo (raw URLs)

```text
JLCPCB PCB thickness FAQ:
https://jlcpcb.com/resources/pcb-thickness

JLCPCB PCB dimensions:
https://jlcpcb.com/help/article/pcb-dimensions

JLCPCB edge rails & fiducials for PCBA:
https://jlcpcb.com/help/article/How-to-add-edge-rails/fiducials-for-PCB-assembly-order

JLCPCB mouse-bite panelization guide:
https://jlcpcb.com/blog/mouse-bite-panelization-guide

JLCPCB part page (MKDV64GCL-STP / C7500180):
https://jlcpcb.com/partdetail/MK-MKDV64GCLSTP/C7500180

Nordic nPM1300 product page:
https://www.nordicsemi.com/Products/nPM1300

TDK/InvenSense T5838 datasheet download page:
https://invensense.tdk.com/download-pdf/t5838-datasheet/
```

[1]: https://jlcpcb.com/resources/pcb-thickness "Choose the Thickness of PCB"
[2]: https://jlcpcb.com/help/article/pcb-dimensions "PCB Dimensions"
[3]: https://jlcpcb.com/help/article/How-to-add-edge-rails/fiducials-for-PCB-assembly-order "How to add edge rails/fiducials for PCB assembly order"
[4]: https://jlcpcb.com/blog/mouse-bite-panelization-guide "Technical Guidance: Mouse Bite Panelization Guide"
[5]: https://jlcpcb.com/partdetail/MK-MKDV64GCLSTP/C7500180 "MKDV64GCL-STP | MK | NAND FLASH | JLCPCB"
[6]: https://www.nordicsemi.com/Products/nPM1300 "nPM1300 PMIC - nordicsemi.com"
[7]: https://invensense.tdk.com/download-pdf/t5838-datasheet/ "
T5838 Datasheet | TDK InvenSense"
