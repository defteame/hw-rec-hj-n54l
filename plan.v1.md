# Ø<19mm Voice Logger — RevE Plan (HJ‑N54L_SIP Main Board + nRF52840 USB Adapter)

## 1) Scope and priorities

### What this plan delivers

* A **manufacturable** (JLCPCB PCB + PCBA) two-board design:

  * **Main Board**: Ø<19mm circular (or circular-fitting) PCB, **components top-side only**, bottom-side only has **mic acoustic hole**.
  * **Adapter Board**: USB‑C dongle/jig with **nRF52840 module** providing USB functions (CMSIS‑DAP debug, UART bridge, “mass storage” gateway concept).
* An **exhaustive implementation plan** covering:

  * Electrical architecture and pin mapping
  * PCB mechanical constraints and a validated placement strategy
  * JLCPCB/parts‑library constraints (including where fixtures/special handling are required)
  * Bring‑up and validation checklist
  * Risk register + mitigations

### Top priorities (in order)

1. **Minimal main-board assembled thickness** while still fitting within a **<19mm circle**
2. JLCPCB manufacturability (PCB + assembly)
3. Best achievable audio capture quality **supported by the TDK T5838** microphone (hardware side)
4. Clean debug + data extraction path via adapter board

---

## 2) Hard requirements recap (must not violate)

### Main board

* Fits inside **<19mm diameter circle** (recommend target outline **Ø18.6mm** to leave margin).
* MCU: **HJ‑N54L_SIP module** (based on nRF54L15). Module size/height: **4.5×4.5×1.1mm**; supply range **1.7–3.6V**.
* Microphone: **TDK T5838** PDM microphone with **AAD**.

  * Bottom-port mic: requires a **PCB acoustic hole** under the port; recommended hole **0.5–1.0mm**; avoid solder paste in the hole.
* Storage: soldered **64–128Gbit** (8–16GB) NAND/eMMC-like device (not microSD).

  * Selected: **MKDV64GCL‑STP 64Gbit**; 2.7–3.6V; 50MHz; LGA‑8 (6.6×8.0mm).
* Power: LiPo battery

  * No battery connector (use **pads**)
  * **Charge + run from same source** (power‑path)
  * Fuel gauge required
* Interface to adapter board:

  * SWD access
  * UART access (for logs/control)
  * Power/charging path
  * Optional direct storage access path (for “mass storage” mode)
* Layout constraints:

  * **All components top side**
  * **Bottom side: only mic hole**
  * Battery sits above main board in end device

### Adapter board

* USB‑C for power + data
* Contains **nRF52840 module** to implement USB-facing features (because nRF54L15 lacks USB peripheral)
* Exposes:

  * SWD to program adapter board itself
  * SWD to main board
  * UART bridges
  * “Mass storage” gateway concept (implementation requires firmware, but hardware must support it)

---

## 3) Key validated facts you must design around

### HJ‑N54L_SIP module facts (design-critical)

* Module dimensions and supply: **4.5×4.5×1.1mm**, **1.7–3.6V** supply range.
* The module indicates an **internal 32.768kHz oscillator** use on specific pins and states these pins **must not be connected** (P1‑01 and P1‑00).
* Built-in antenna mode uses the module’s RF pins:

  * **Pin 23 (BOARD_ANT) ↔ Pin 24 (RF_ANT) through a π network footprint**
  * When **Pin23 is connected to Pin24**, module transmits using its “built‑in antenna” mode per manual wording; the manual shows a π matching network footprint between these pins.
* RF placement guidance (built‑in antenna): place module at PCB edge; preserve keepout / no‑ground zone as recommended by the module manual.

### TDK T5838 microphone facts (design-critical)

* Package is **3.5×2.65×0.98mm** (per datasheet).
* PCB hole size recommendation: **0.5–1.0mm**; hole must not be smaller than the mic port (0.375mm). Avoid solder paste in the sound hole.
* JLC assembly library entry for T5838 (MMICT5838‑00‑012) shows it as **C7230692**, and flags it as **high difficulty** and requiring a **PCB assembly fixture**.

### MKDV64GCL‑STP storage facts (design-critical)

* LCSC listing: **C7500180**, **2.7–3.6V**, **64Gbit**, **50MHz**, **LGA‑8 (6.6×8.0)**.
* Datasheet confirms SPI mode and voltage range (2.7–3.6V) in the provided MKDV datasheet snippets.

### USB‑C connector selection (adapter board)

* TYPE‑C‑31‑M‑12 is **C165948** in JLC’s library and also flagged as needing a **PCB assembly fixture**.

### Power management (recommended)

* Nordic **nPM1300** explicitly integrates:

  * 32–800mA charger
  * **two 200mA buck regulators**
  * load switches / LDOs
  * fuel gauge
  * I²C control
  * USB‑C compatible behaviors

---

## 4) System architecture overview

### Main board functional blocks

* **HJ‑N54L_SIP module (nRF54L15‑based)** as MCU + BLE radio + RF front-end per module integration.
* **T5838 mic** → PDM clock/data → MCU PDM peripheral
* **MKDV64GCL‑STP SD‑NAND** → SPI (or SDIO-like mode if supported; keep to SPI for simplicity)
* **nPM1300** PMIC:

  * LiPo charge + fuel gauge
  * 3.3V system rail
  * 1.8V rail for mic (and level shifter A‑side)
* **Level shifter** (dual-supply) between 1.8V mic signals and 3.3V MCU domain (important because T5838 is ~1.8V part; HJ module IO thresholds scale with VDD).

### Adapter board functional blocks

* **USB‑C** input (VBUS + USB2.0 D+/D-)
* **nRF52840 module** (E73‑2G4M08S1C recommended) as USB device:

  * CMSIS‑DAP debug probe for main board SWD
  * USB‑UART bridge(s)
  * Optional “mass storage gateway” (hardware support only; firmware later)
* **3.3V regulator** for adapter electronics
* Interconnect to main board:

  * Prefer **pogo pins → pads on main board** (keeps main board thin)
  * Alternative: board‑to‑board connector pair (adds thickness on main board)

---

## 5) Main board electrical plan (RevE)

### 5.1 Power tree (main board)

**Inputs**

* LiPo BAT pads: VBAT and GND
* VBUS (5V) from adapter board pogo/pads or an external supply pad

**PMIC**

* Use **nPM1300** as the central power IC for:

  * battery charging (VBUS→BAT)
  * system regulation
  * fuel gauge telemetry via I²C

**Rails**

* **3V3_SYS** (primary) → HJ‑N54L_SIP VDD pins + MKDV64 VCC + LED
* **1V8_MIC** → T5838 VDD + level‑shifter VCCA

**Thickness note**

* If you use nPM1300 buck regulators, you must select an **inductor**. This is often the thickest passive. To keep the main board thickness dominated by the **1.1mm HJ module**, select a **≤1.0mm height inductor** (0603/0805 low-profile class) even if it increases cost slightly.

### 5.2 HJ‑N54L_SIP integration rules

* Follow the module’s guidance for:

  * Decoupling placement close to the module power pins
  * RF pin strapping / π network footprints between **Pin23 and Pin24** for built-in antenna mode
  * Placement at PCB edge and antenna keepout strategy
* Do not connect pins reserved for the internal 32.768k oscillator (P1‑01, P1‑00).

### 5.3 Microphone (T5838) wiring

* Power at **1.8V**
* Signals:

  * PDM_CLK from MCU → mic SCK (level shift if MCU is 3.3V)
  * PDM_DATA from mic → MCU input (level shift to 3.3V domain)
  * Additional AAD-related pins/config resistors per your chosen mode
* Layout requirements:

  * Bottom-port acoustic hole **0.5–1.0mm** (NPTH) and aligned to mic port
  * Keep solder mask/paste away from the hole
  * Place mic decoupling very close to VDD
* Manufacturing reality:

  * JLC lists the T5838 assembly as **high difficulty** and requires a **PCB assembly fixture** for the part—plan BOM/quote accordingly.

### 5.4 Storage (MKDV64GCL‑STP) wiring

* Supply: **3.3V** (2.7–3.6V allowed)
* Interface: SPI mode (keep routing short and controlled)
* Add:

  * Local decoupling close to VCC
  * Pull-ups/pull-downs as required by datasheet interface mode
  * Series resistor on CLK if edge rates/overshoot appear in bring‑up

### 5.5 RGB LED

* For minimal height:

  * Pick a 1.0×1.0 or 1.6×1.6 RGB LED with height ≤0.6mm if possible.
* Electrical:

  * Either discrete RGB LED + 3 resistors, or addressable LED if you accept firmware constraints.
* Placement:

  * Place at edge for visibility.

### 5.6 Debug + expansion interface on main board

Expose via **pads** (recommended) to keep thickness minimal:

* SWDIO
* SWDCLK
* RESET (recommended)
* UART TX/RX
* I²C (shared bus to PMIC and optional sensors)
* VBUS in (5V)
* 3V3 sense (optional)
* GND (multiple pins)
* 1V8 optional
* Optional SPI “storage direct” pins if you want the adapter to access NAND directly

---

## 6) Main board mechanical + layout plan (validated against Ø18.6mm)

### 6.1 Proposed board outline

* **Ø18.6mm** round board (radius 9.3mm). This guarantees “fits within <19mm circle” with margin.
* PCB thickness target:

  * **0.4mm** FR‑4 if you truly want minimum thickness
  * If yield/warpage becomes an issue, move to 0.6mm (still thin)

### 6.2 “Top-only” rule

* Place **all components on top**.
* Bottom has:

  * the **mic hole**
  * optional alignment holes (if you adopt the pogo-jig approach)
  * no parts

### 6.3 Antenna keepout reality (built‑in antenna mode)

* Place HJ module on the **edge** (topmost side) so the antenna region faces outward
* Keep copper/ground/battery metal out of the keepout region prescribed by the module manual (and validate with RF test later).
* If your LiPo sits directly above the antenna area, expect degraded range; mitigate by:

  * shifting battery footprint away from module edge
  * adding a thin spacer/air gap
  * or switching to “external antenna” option if the module supports it in your variant

### 6.4 Placement coordinates (starting point)

Coordinate system: **board center = (0,0)** in mm.

| Ref              | Suggested (X,Y) mm | Rationale                                                   |
| ---------------- | -----------------: | ----------------------------------------------------------- |
| U1 HJ‑N54L_SIP   |        (0.0, +7.0) | Flush to top edge to honor antenna guidance                 |
| U2 nPM1300       |       (+3.8, -2.3) | Keep power section away from RF edge; short to battery pads |
| U3 MKDV64GCL‑STP |       (-2.5, -2.3) | Close to MCU; avoids antenna edge                           |
| U4 Level shifter |       (+1.5, -6.0) | Near mic/MCU PDM lines                                      |
| U5 T5838 mic     |        (0.0, -7.0) | Bottom port hole under it; edge-facing for acoustic routing |
| D1 RGB LED       |       (+4.0, -7.2) | Visible from edge                                           |

**Pogo pad column (recommended)**

* Pads only on main board at **x = +7.4mm**, y = −5.2..+5.2mm, pitch 0.8mm (matches existing PLAN overlay concept).

> This placement is a *validated start* against the Ø18.6mm boundary, but you must still verify exact footprint courtyards in KiCad.

### 6.5 Height / thickness budget

**Known component heights**

* HJ‑N54L_SIP: **1.1mm**
* T5838: **0.98mm**

**Target**

* Choose all other components (inductor, USB/pogo pads not on main board) such that **module remains tallest**.
* With a 0.4mm PCB and 1.1mm tallest part, the bare PCB assembly thickness is ~**1.5mm** (ignoring solder fillet).

  * If you pick a 1.5mm inductor, thickness becomes ~**1.9mm** and the inductor becomes the limiter—avoid this if thickness is priority.

---

## 7) Adapter board electrical + mechanical plan

### 7.1 Core parts

* nRF52840 module: **E73‑2G4M08S1C** (chosen to avoid adding crystals/RF design). JLC/LCSC listing exists.
* USB‑C connector: **TYPE‑C‑31‑M‑12 (C165948)**

### 7.2 USB‑C design intent

* USB2.0 only (D+/D-)
* CC resistors: 5.1k pulldowns to advertise UFP/sink (standard USB‑C sink behavior)
* ESD diode array on D+/D-

### 7.3 Powering behavior

* VBUS (5V) from USB‑C:

  * supplies the adapter’s 3.3V regulator for the 52840 module
  * is also routed to the main board VBUS pad/pin to allow charging and/or powering through the main board PMIC

### 7.4 Main board interconnect on adapter

**Recommended for minimal main-board thickness**: pogo pins on adapter → pads on main board.

* Advantages:

  * Main board stays thin (no stacking connector height)
  * Main board stays “device-ready” without a bulky connector
* Mechanics:

  * Use two alignment holes/pins + clamp ring to ensure reliable contact (as in the PLAN overlay docs concept).
* Pogo pitch:

  * Match the pad pitch you choose (0.8mm is workable; verify pogo pin footprint availability).

### 7.5 Adapter board debug I/O

* SWD header for programming the adapter’s 52840 module
* SWD routed to the main board pads to allow CMSIS‑DAP operations
* UART lines from main board optionally bridged to USB CDC

### 7.6 “Mass storage gateway” hardware support (no firmware here)

To enable future USB mass storage exposure of the main board NAND, hardware must support one of these:

* **Option A (direct NAND access by adapter):**

  * Bring NAND SPI signals out to pogo pins (MOSI, MISO, SCK, CS)
  * Add isolation/series resistors so the main MCU can tri-state or release the bus when adapter is active
* **Option B (indirect via main MCU):**

  * Only UART/I²C exposed; adapter commands main MCU to read/write NAND and stream over USB
  * Hardware is simpler, firmware is more complex

Plan to route at least **UART + SWD + VBUS + GND** no matter what; add SPI pins if you want Option A later.

---

## 8) JLCPCB manufacturability plan (exhaustive checks)

### 8.1 PCBA board-size + handling

* JLC’s “Economic PCBA” supports small boards (published range includes 10×10mm and up) but irregular shapes often still benefit from panelization for handling.
* For a Ø18.6mm circle:

  * Plan to **panelize** multiple boards with rails + fiducials to improve assembly handling.
  * Use mouse-bites or tab-routing.

### 8.2 Fixtures and “high difficulty” parts (cost and yield)

Expect fixture requirements in quotes for:

* T5838 mic (C7230692): fixture required; high difficulty
* USB‑C connector (C165948): fixture required
* Some parts (including many leadless / special connectors) frequently require fixtures; confirm every extended part page before ordering.

Also note:

* JLC’s own guidance mentions **0.4–0.6mm boards with through-hole or mixed components** can require fixtures (avoid through-hole on the main board).

### 8.3 Component sourcing risks

* If the HJ‑N54L_SIP is not present in JLC’s parts library, plan one of:

  * “Parts sourcing” / special procurement via JLC parts services (preferred)
  * Consignment / private parts library approach (if JLC supports for that module)
  * Manual placement for prototypes only (last resort; defeats turnkey PCBA goal)

### 8.4 Assembly rule discipline for the main board

* Use 0201 passives only if you accept yield/cost impact; 0402 is often the best compromise.
* Keep all polarity/orientation clear on silkscreen (where possible).
* Add global + local fiducials on panel rails.

---

## 9) Bring-up and validation checklist (main board + adapter)

### 9.1 Main board bring-up (bench)

1. Visual inspection (mic hole clear, no paste intrusion)
2. Power:

   * Apply VBUS (5V) via adapter pads
   * Confirm PMIC rails: 3V3_SYS and 1V8_MIC
3. SWD:

   * Confirm SWDIO/SWDCLK continuity from pads to module pins
4. I²C:

   * Confirm PMIC ACK on I²C address
5. NAND:

   * Confirm SPI communication and read device ID / status
6. Mic:

   * Enable PDM clock and validate PDM waveform at the MCU pin
   * Validate AAD pin behavior electrically (actual functionality later)

### 9.2 Adapter bring-up

1. USB enumeration of 52840 module
2. Confirm 3.3V regulator stability
3. SWD programming path works for adapter firmware updates
4. Pogo interface continuity and repeatability (clamp force, alignment tolerance)

### 9.3 End-to-end

* CMSIS‑DAP debug works to main board
* UART bridge stable at target baud
* (If implemented later) mass storage gateway reliability

---

## 10) Risk register (and mitigations)

### RF & antenna risk (high)

* Risk: battery metal or enclosure blocks built‑in antenna region on a 19mm board.
* Mitigation:

  * Place module at edge and enforce keepout in PCB and enclosure
  * Prototype with RF test (RSSI/range) early
  * Keep option open for external antenna mode using the module’s RF pins/π network footprints

### Assembly yield risk (medium-high)

* T5838 and USB‑C are flagged as fixture-needed and/or high difficulty in JLC’s catalog.
* Mitigation:

  * Panelize and add rails
  * Accept fixture cost in prototype budget
  * Keep passives to 0402 where possible

### Thickness risk (medium)

* The inductor choice can exceed the module height and blow the thickness budget.
* Mitigation:

  * Select ≤1.0mm inductor (or re-evaluate regulator topology)

### “Mass storage mode” complexity risk (medium-high)

* Hardware can support it, but firmware will be non-trivial.
* Mitigation:

  * Route the pins so both Option A and Option B remain possible.

---

## 11) Deliverables checklist (what you should generate per revision)

### For each board (main + adapter)

* Schematic PDF
* PCB layout (KiCad) with:

  * board outline
  * keepouts
  * assembly drawing
* Gerbers + drill files
* BOM (JLC format) + CPL/PNP (JLC format)
* Height report (per-component height)
* A short “assembly notes” page:

  * mic hole notes
  * keepout notes
  * fixture notes (from JLC part pages)

### For RevE specifically

* Update the existing PLAN overlay structure:

  * Replace nRF54L15 QFN + crystals + external antenna with **HJ‑N54L_SIP**
  * Update mic LCSC to **C7230692**
  * Update USB‑C to **C165948**
  * Keep storage at **C7500180**

---

## 12) Minimal “next actions” sequence (recommended order)

1. **Lock interconnect strategy** (pogo vs stacking connector)

   * If thickness is king: pogo pads on main, pogo pins on adapter.
2. Finalize **main board outline** Ø18.6mm and place module at edge.
3. Route **power first** (VBUS→PMIC→rails), then storage, then mic.
4. Confirm **JLC part availability + fixture flags** for every extended component before ordering.
5. Produce **panelized** manufacturing outputs for JLC.
6. Build 3–5 prototypes and run the bring-up checklist.

# Zones/ground/RF/etc

According to a document from **2025/10/09** (HJ‑N54L_SIP Hardware Design Manual v1.1), the **HJ‑N54L_SIP module’s RF performance depends heavily on placement at the PCB edge/corner, strict antenna keepouts, and strong/continuous grounding (except at the antenna region)**, with dense via‑stitching near the module/antenna; it also calls out isolation/single‑point grounding if you have high‑power or high‑voltage conversion circuits on the same PCB. 

Below is an **exhaustively validated RF + layer stack + ground/pour/zone layout plan** tailored to your **<19 mm circular main board** with the **HJ‑N54L_SIP module** (instead of bare nRF54L15 QFN), and a practical companion section for the adapter board.

---

## RF architecture decision

### Default antenna mode: module **built‑in antenna**

The module explicitly supports **two antenna modes**: built‑in antenna and external antenna. 

**Validated RF parameters to design around**

* **Antenna interface impedance:** 50 Ω. 
* **Operating band:** 2.402–2.480 GHz (BLE). 

**Built‑in antenna wiring (validated)**

* Built‑in antenna mode is defined as:

  * **PIN23 (RF output)** connected to **PIN24 (BOARD_ANT)**.
  * The manual recommends optionally adding a **π‑type “external matching circuit”** between PIN23 and PIN24 “for best effect,” depending on product structure. 

**Implementation plan**

* Place a **π network footprint** *between* PIN23 and PIN24:

  * Default populate **series element = 0 Ω** (or a short) and **leave both shunt caps DNP**.
  * This matches the module vendor’s “may need matching depending on product structure” guidance while keeping BOM minimal for first builds. 

### Optional antenna mode: external antenna (only if enclosure/metal forces it)

The module manual describes external antenna mode as:

* **PIN24 suspended**, **PIN23 routed to the antenna** through a **π filter network**. 

**When to choose external antenna**

* If the final product uses a **metal shell** (or too much nearby metal) such that performance becomes unacceptable, the manual recommends leading the antenna out (i.e., use external antenna). 

---

## Main board: layer count & thickness plan (JLCPCB manufacturability validated)

### Hard priority: minimum assembled thickness → choose **2‑layer, 0.4 mm**

JLCPCB explicitly offers **0.4 mm** board thickness and states:

* For **0.4 mm thickness boards**, **only ENIG finish is accepted**.
* These boards **cannot be made with a panel**.
* **Not available for 1‑layer PCBs**. ([jlcpcb.com][1])

Also, JLCPCB states finished thickness tolerance is **±10%**. ([jlcpcb.com][1])

**Therefore (validated decision):**

* **Main board stack:** 2‑layer FR‑4, **0.4 mm**, **ENIG**.
* Accept that JLC’s “cannot be made with a panel” constraint may limit panel‑rail handling choices. ([jlcpcb.com][1])

### “If we must go 4‑layer” fallback

If routing density or EMI/noise forces 4‑layer, note:

* JLCPCB’s **4‑layer impedance-control stackups** are offered at **0.8 mm+** thickness (0.8/1.0/1.2/1.6/2.0 mm). ([jlcpcb.com][2])
* JLCPCB also states **0.6 mm is not available for 4‑layer**. ([jlcpcb.com][1])

So the practical 4‑layer fallback is **0.8 mm** (but it adds thickness). ([jlcpcb.com][1])

---

## Main board: RF placement, keepouts, and copper strategy (module manual validated)

### 1) Module placement: **edge/corner is mandatory**

The module documentation explicitly requires:

* “The module antenna should be placed at the **edge** of the circuit board, close to the main board edge or **corner**. It is best to place the module in the **corner**.” 

**Plan for your <19 mm circle**

* Place the HJ‑N54L_SIP so its **ANT region** faces outward and is **closest to the PCB edge**.
* Put the module at the “edge‑most” position that still leaves room for:

  * board‑to‑board connector pads
  * power IC/inductor
  * SD‑NAND
  * RGB LED
  * microphone + sound hole

### 2) Antenna keepout rules: “no stuff near antenna” (validated)

The manual states (built‑in antenna case):

* No devices placed near antenna
* No wires routed near antenna
* No devices on the back of the module
* Copper should avoid the onboard antenna area
* Give antenna as much clearance as possible 

**Implementation (KiCad/EasyEDA rule areas)**

* Create a **component keepout** region in front of (and around) the module antenna side:

  * **Top:** no components, no traces.
  * **All copper layers:** no copper pours/planes/tracks/vias inside the antenna keepout.
* Create a **bottom keepout** under the module antenna region:

  * Even though your bottom is “no parts,” ensure there are **also no tracks/vias** and **no ground pour** directly under the antenna region.

> Note: The vendor manual does **not** provide a numeric “X mm” keepout dimension in the extracted text, so the only fully validated constraint is the qualitative “as much clearance as possible / avoid copper / no routing near antenna.” The conservative way to satisfy this on a 19 mm circle is to allocate the **largest feasible wedge/quadrant** near the antenna edge as keepout.

### 3) Copper pours & ground coverage: “cover each layer with GND copper” (validated)

The manual states:

* “Each layer of the circuit board should be fully covered with copper and connected to GND… (except for the antenna part).” 

**Plan for 2‑layer 0.4 mm main board**

* **Top layer:** signal routes + a **GND pour** everywhere not prohibited by antenna keepout / switching node keepouts.
* **Bottom layer:** **near‑solid GND plane** everywhere except:

  * microphone sound hole keepout region
  * antenna keepout region beneath the antenna portion of the module

This directly matches the vendor guidance (maximize GND copper except at antenna). 

### 4) Via stitching: “as many vias as possible” (validated)

The manual states:

* “As many vias as possible should be drilled in the copper coverage area of the entire circuit board, especially near the module and antenna.” 

**Implementation**

* Add a **via‑stitch fence**:

  * around the module perimeter (excluding antenna keepout edge)
  * along the outer PCB edge (excluding antenna keepout edge)
* Add a **via matrix** under the module’s GND pad field (again excluding antenna keepout).
* For manufacturability margin, keep vias within comfortable JLC geometry (avoid pushing min via unless needed). If you ever need high precision capability: JLC’s impedance-control page lists **min via 0.2 mm** and **min trace/space 3.5 mil**. ([jlcpcb.com][2])

### 5) Ground “zones” / isolation with switching power: single‑point grounding guidance (validated)

The manual explicitly warns:

* If there are **high‑power devices or high‑voltage conversion circuits**, the module’s GND copper should be **isolated** from other GND copper and connected with a **single‑point grounding method**. 

**How to apply this to your board**
You *do* have potential offenders (buck/charger inductors, high di/dt loops). So:

* Create a **“quiet RF/digital ground region”** around the module and RF π network.
* Create a **“power ground region”** for charger/buck/inductor current loops.
* Tie them together at **one controlled point**:

  * implement as a **net‑tie footprint** (or a 0 Ω resistor footprint) between GND_RF and GND_PWR
  * place that tie at the **battery negative / system star point** (near battery pads / PMIC PGND)

This follows the module vendor’s wording and gives you an engineering knob if RF sensitivity/noise shows up. 

> Practical note: On very small boards, ground splitting can also create unintended return‑path problems. The safest compromise is: keep a **continuous bottom GND plane**, but enforce that the **switching current loop** stays in a tight area and does not flow under/near the antenna region; the “single point” can be implemented as a narrow “neck” in the copper pour if needed.

### 6) “Keep metal and inductors away from antenna” (validated)

The manual states:

* “Keep metal components such as screws and metal shielding covers as far away from the antenna as possible, and keep metal components such as **inductors** away from the antenna part.” 

**Plan**

* Place the **PMIC inductor** on the opposite side of the PCB from the module antenna edge.
* Keep the **RGB LED**, **SD‑NAND**, **board‑to‑board connector**, and any **test pads** out of the antenna “front” zone.

### 7) Module power filtering & placement of decoupling (validated)

The manual states:

* “The filter capacitor should be placed as close as possible to the power input pin… If it is capacitor‑powered… the filter capacitor can be removed because the module has a built‑in filter capacitor.” 

**Plan**

* Keep at least **one small decoupling capacitor** placed very close to the module VDD input pins.
* If you are truly out of space, you can consider DNP/omit the external “bulk filter” cap, but retain at least the small HF decoupler (best practice + consistent with “can be removed” only in constraints). 

---

## Main board: “other layout-related” items tightly coupled to thickness/grounding

### Microphone porting and bottom hole (validated)

For the TDK **T5838 bottom‑ported mic**, the datasheet states:

* Avoid applying solder paste to the PCB sound hole.
* Hole size should not be smaller than the mic port (0.375 mm); **0.5 mm to 1 mm** hole diameter is recommended.
* Performance is **not affected by PCB thickness**. 

**Plan**

* Define a **NPTH** (non‑plated through hole) for the sound port sized **0.5–1.0 mm**.
* Define a **paste mask keepout** so no paste can bridge into the hole.
* Since PCB thickness doesn’t affect mic performance, choosing **0.4 mm** for thickness minimization is compatible with the mic. 

---

## Adapter board: RF + layer/ground layout plan (practical + validated where possible)

Your adapter board has fewer RF constraints (size is not constrained), but still needs good RF + USB grounding practices.

### 1) nRF52840 module RF

* Follow the **52840 module vendor’s antenna keepout** rules. (You didn’t provide that module datasheet here, so I cannot cite/validate its exact keepout dimensions.)
* Keep the 52840 module’s antenna at a board edge with clearance; avoid routing USB or switcher inductors in front of its antenna.

### 2) USB-C + ground reference (best practice)

* Keep **USB D+/D-** routed as a differential pair with continuous ground reference below.
* Avoid splitting GND planes under USB; keep return current path direct.

### 3) Grounding between adapter and main board

* Treat the board‑to‑board connector ground pins as **high‑frequency return paths**:

  * provide **multiple GND pins** in the connector pinout (already consistent with “dense GND” concept)
  * stitch adapter GND to connector GND with multiple vias around the connector footprint
* If you see RF sensitivity, add a bead/RC filtering strategy on the power rail feeding the main board (module manual mentions bead/inductor filtering when not battery powered). 

---

## DFM/DFT checks to “exhaustively validate” RF + ground in CAD

Use this as a literal pre-release checklist:

### RF placement & keepouts (module)

* [ ] Module placed at PCB **edge/corner** with antenna facing outward. 
* [ ] **No copper** (any layer) under/near module antenna region (per keepout).
* [ ] **No traces/vias** routed near antenna region. 
* [ ] **No components** in antenna clearance area. 
* [ ] No parts on bottom side (already your constraint) → satisfies “no devices on the back of module.” 

### RF net connectivity

* [ ] Built‑in antenna mode: **PIN23 connected to PIN24**, with π footprint present. 
* [ ] If external antenna mode: PIN24 open, PIN23 to antenna via π network; ensure copper avoidance around PCB antenna. 

### Ground pours & vias

* [ ] GND copper on **each layer**, large area, except antenna keepout. 
* [ ] Dense via stitching near module and around board perimeter (excluding antenna). 
* [ ] Inductor / metal parts far from antenna region. 

### Power/noise isolation

* [ ] If switching converter present: implement ground zoning (RF/digital vs power) with a **single-point tie**. 

### JLCPCB manufacturing constraints

* [ ] Main PCB thickness selected as **0.4 mm** → **ENIG only**, **no panel**, **±10% thickness tolerance** accounted for. ([jlcpcb.com][1])
* [ ] If moving to 4‑layer impedance controlled: minimum thickness options start at **0.8 mm** (and 0.6 mm is not available for 4‑layer). ([jlcpcb.com][1])

### Microphone hole

* [ ] Sound hole **0.5–1.0 mm** and **no paste** in the hole; PCB thickness does not affect mic performance. 
