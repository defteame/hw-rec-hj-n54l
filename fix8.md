Below is a deep, “design-review style” audit of what’s currently in your Atopile project (v7.zip) and the build artifacts/logs, plus a very opinionated plan to get you to a **layout‑ready, order‑ready** design for a **~19 mm round, ultra‑thin, one‑sided assembly** board using:

* **HJ‑N54L_SIP (nRF54L15 module)**
* **T5838 PDM mic (bottom port / hole on the “flat” side)**
* **CSNP64GCR01‑BOW SD NAND (SPI mode)**

I’m assuming the physical layout has not started (correct), and you want to **finish schematic/DFM decisions first**.

---

## 1) Executive verdict (what’s good, what’s not)

### What is already *fundamentally correct*

* **Power tree concept is solid**: nPM1300 generates **1.8 V** and **3.0 V** from VBAT/VBUS and you distribute those rails appropriately. The resistor‑strapped VSET scheme used is valid and matches the datasheet tables (47 kΩ → 1.8 V on VOUT1, 150 kΩ → 3.0 V on VOUT2).
* **Mic ↔ MCU level shifting is necessary and implemented**:
  The HJ module specifies input high threshold **VIH ≈ 0.7·VCC** (so with VCC≈3 V, “HIGH” is ~2.1 V).
  The T5838 runs at **~1.8 V** and its I/O must not be driven above its supply domain.
  So the translator is the right architectural choice.
* **SD NAND in SPI mode wiring is conceptually right**: pull‑ups on CMD/DAT lines and a small CLK series resistor are per vendor guidance.

### The biggest schematic/design problems you must fix *before layout*

1. **SHPHLD external pad is currently “almost guaranteed not to work”**
   In `main.ato` you placed **R_SHHPHLD = 10 kΩ in series** between the nPM1300 SHPHLD pin and the external pad.

   But **nPM1300 has an internal pull‑up ~50 kΩ** on SHPHLD and SHPHLD low must be below **0.4 V max** to be recognized as LOW in ship/hibernate context.
   With a series 10 kΩ and the internal 50 kΩ pull‑up to VBAT/VBUS, if you short the external pad to GND, the SHPHLD pin will sit at roughly:

   * **VBUS = 5.0 V** → 5·10/(10+50)= **0.83 V**
   * **VBAT = 4.2 V** → 4.2·10/(10+50)= **0.70 V**

   Both are **above 0.4 V**, i.e. **not a valid LOW** per the spec. This will break “button to GND” behavior, including waking from Ship/Hibernate (“push button to GND is required”).

   ✅ Fix: make that series element **0 Ω** (or remove it entirely). If you want protection, use something like **100 Ω–1 kΩ** max; 10 kΩ is too large given the internal pull‑up and VIL requirement.

2. **USB‑VBUS input current limit is effectively locked at 100 mA** (because CC1/CC2 are floating)
   nPM1300 explicitly states: leaving CC pins unconnected means CC detection assumes **100 mA**, and it limits input current accordingly.
   That might be OK if you only ever use VBUS as “light power / slow charge”, but it’s a **big functional constraint**.

   ✅ Decide now (before layout):

   * If you want **more than 100 mA from USB‑VBUS**, you must route **CC1/CC2** to *something* (pogo pads to the adapter board, or actual USB‑C connector on the main board).
   * If you accept **100 mA**, keep current design but treat it as a hard limitation.

3. **The main board BOM does not include the HJ‑N54L_SIP module**
   Your picker warnings confirm you don’t have a part selection for `U1` on main (`LCSC part not found for comp: U1`). That means PCBWay PCBA will not source it automatically.
   ✅ Fix: either:

   * Add a proper manufacturer/MPN/LCSC mapping for the module (if available), **or**
   * Mark it clearly as **“Do Not Source / Customer Supplied / Hand‑solder”** in the BOM/assembly notes.

4. **Your “3V3_SENSE” net name is misleading**
   The design sets VOUT2 = **3.0 V** (150 kΩ), not 3.3 V.
   ✅ Fix: rename to `VOUT2_SENSE` or `VCC_SENSE` to avoid human mistakes during bring‑up.

---

## 2) What’s in your Atopile design (main.ato) and whether it’s complete

### Power / PMIC: nPM1300 (U2) + passives

Your selection is aligned with Nordic’s typical usage:

* VSET1 resistor **47 kΩ → 1.8 V**
* VSET2 resistor **150 kΩ → 3.0 V**
* 2.2 µH inductors, 4.7 µF output caps on each buck, 10 µF battery bulk, and required input caps.
  nPM1300 expects **effective output capacitance ≥4 µF** and tight ESR, and buck current capability is ~200 mA class (spec table shows 200 mA max load for BUCK).

**Your chosen inductor (LCSC C2918667) looks compatible**: 2.2 µH, high current rating, and DCR well below the ≤400 mΩ guideline from Nordic.

✅ Verdict: **PMIC subsystem is complete**, but:

* Fix **SHPHLD series resistor** (critical).
* Make the **CC current limit decision** (critical).
* Consider adding **one extra bulk cap** on 3.0 V (like 10 µF) if you see load steps from radio + NAND writes; not strictly required but often worth it on tiny, thin boards.

Also: Nordic layout guidance explicitly notes **“No components on the bottom layer”** and recommends a **minimum 2‑layer PCB including a ground plane**—which matches your “one‑sided assembly + flat bottom” goal nicely.

---

### MCU module: HJ‑N54L_SIP

Key constraints you must respect in PCB layout:

* Module is **4.5 mm × 4.5 mm × 1.1 mm** and uses **LGA45**, supply **1.7–3.6 V**.
* It has built‑in antenna; vendor guidance says the **antenna section should be outside the board**, with **no copper/ground pour under antenna region on any layer**, and to keep metal/inductors away from antenna area.

Your schematic includes:

* SWDIO/SWDCLK to pogo.
* UART TX/RX to pogo.
* I2C SDA/SCL to PMIC and to pogo.
* PDM pins to mic via level shifter.
* SPI to NAND.

✅ Verdict: **MCU connectivity is complete**, but layout must honor antenna keepouts and “don’t put inductors near RF”.

---

### SD NAND: CSNP64GCR01‑BOW in SPI mode

Your schematic contains the essentials:

* Pull‑ups (10 kΩ) on CMD/DAT lines.
* Clock series resistor (you used 10 Ω; datasheet suggests 0–120 Ω range).
* VCC decoupling: you placed 100 nF + 2.2 µF, matching “at least 2.2 µF” guidance.

✅ Verdict: **NAND subsystem is complete**, assuming:

* The footprint is correct for the exact package variant you’ll buy.
* You route SPI tightly and keep CLK short (place Rclk very close to the driver pin).

---

### Mic: TDK T5838 PDM mic (bottom port)

Your schematic does the right things:

* Supply from 1.8 V.
* PDM clock into mic, data out.
* WAKE output to MCU (through translator).
* SELECT tied low (channel selection per datasheet text).

Critical electrical constraints you handled correctly:

* T5838 recommended VDD includes **1.8 V within 1.62–1.98 V** range.
* Absolute max on input pins is **VDD + 0.3 V** (so do not feed 3.0 V logic into it).
* Datasheet explicitly says **do not use pull‑ups/pull‑downs on PDM data** (so your “DNP pull‑up” is fine *as long as it stays DNP*).

Mechanical constraints you must implement:

* Mic sound port hole recommended **0.5–1.0 mm** diameter, and **performance is not affected by PCB thickness**.

✅ Verdict: **Mic subsystem is correct**, with one opinionated improvement:

* Add a “quiet” supply option: either a tiny ferrite bead or small series resistor for mic VDD (DNP by default). This is optional but can reduce buck ripple coupling into audio.

---

### Level shifter: SN74AXC4T774

Your direction control looks correct:

* Channels A1–A2: A→B (mic data/wake from 1.8 to 3.0)
* Channels B3–B4: B→A (clock + THSEL from 3.0 to 1.8)

That matches TI’s truth table for DIR/OE behavior (DIR=HIGH means A→B, DIR=LOW means B→A, OE low disables).

✅ Verdict: **Translator usage makes sense**.
One layout note: place the translator **near the mic** (short 1.8 V domain traces) unless routing forces it closer to MCU.

---

## 3) Atopile build artifacts / logs: what they’re telling you

From your archived logs:

* **Main BOM warning**: missing LCSC part for `U1` (the HJ module) + several pads and DNP caps.
  This is expected for “pads” and DNP parts, but **not** for your MCU module if you want PCBA to source it.
* **Main picker warning**: `U1` not found, plus pads missing, plus DNP.
  Again: the real issue is the module, not the pads.
* **Adapter**: the adapter uses an EBYTE module (`E73-2G4M04S1B`), and it is properly part‑picked; the rest are passives and Type‑C parts.

✅ Practical conclusion:

* Your Atopile automation is working.
* The remaining “picker noise” is fine **only if you intentionally plan to hand‑place** the module and/or treat pads as non‑BOM.

---

## 4) The *real* DFM constraints for your 19 mm ultra-thin board (PCBWay)

### Board thickness reality check

PCBWay lists overall board thickness range **0.2–3.2 mm**, but **4‑layer minimum thickness is 0.6 mm normally, 0.40 mm with “advanced” capability**.

So:

* If you want **0.2 mm**, you’re effectively in **1–2 layer** territory.
* If you want **4 layers**, your realistic floor at PCBWay is **0.4 mm** (advanced).

### Board size / panelization

PCBWay’s fabrication capability page states:

* **Minimum finished PCB size ≥ 20 mm × 20 mm**, and boards **10–20 mm require engineer review**, <10 mm must review too.
* Minimum panel size appears as **100 mm × 120 mm**.

Your board is **19 mm diameter**, so bounding box ≈ **19×19** → falls into the **10–20 mm “engineer review”** zone.

### Assembly capability

PCBWay EMS capability notes:

* Passive parts down to **01005** are processable (so 0402/0201 are fine),
* Minimum PCB size can be **10×10**, but “if smaller, it needs to be panelized.”

✅ Practical conclusion:

* You almost certainly want to order this as a **panel** (with rails + fiducials), even if you only need a few boards.
* Your 19 mm circle is manufacturable, but expect “DFM review” and panelization requirements.

---

## 5) My very opinionated “finish everything before layout” plan

This is the exact sequence I would follow to minimize redesign cycles.

### Step 0 — Freeze your hard requirements (no CAD yet)

Make these decisions now (because they change nets / pogo count / mechanical):

1. **VBUS current limit**:

   * Keep CC floating → accept **100 mA max from USB‑VBUS**
   * Or break out **CC1/CC2** (extra pogo pins) so the adapter can negotiate higher current.
2. **Do you need SHPHLD accessible externally?**
   If yes, you must fix the series resistor (next step).
3. **How will you program/debug?**
   Decide the final pogo map (main ↔ adapter). Right now, adapter has 12 pogo nets, main has 16+ nets (battery and NAND debug). If your jig won’t use NAND debug pins, drop them from main pogo.

---

### Step 1 — Fix schematic bugs / cleanup in Atopile (blocker items)

1. **Fix SHPHLD series resistor**

   * Change `r_shphld` from 10 kΩ to **0 Ω** or remove it.
   * Reason: internal pull‑up 50 kΩ + VIL max 0.4 V means 10 kΩ prevents a valid low.
2. **Rename “3V3_SENSE” → something truthful**

   * You are at **3.0 V** by design.
3. **Decide CC routing (or explicitly document the 100 mA limitation)**
4. **BOM sourcing decision for HJ‑N54L_SIP**

   * Either pick a sourcing entry, or add “Customer supplied / do not source” instructions.
5. **Explicit DNP control**

   * Ensure the following are *clearly* DNP in whatever PCBWay will consume:

     * RF shunt caps (`c_rf_dnp`, `c_rf_dnp2`)
     * Translator spare caps (`c_vcc_dnp`, `c_vcca_dnp`)
     * Mic data pull‑up (must remain DNP; datasheet says no pull).

---

### Step 2 — Footprint verification pass (you do this before placement)

This is “boring”, but it prevents 80% of first‑spin failures:

* **HJ‑N54L_SIP footprint**: verify pad size/spacing, orientation, and antenna “edge location” constraints from the manual (antenna outside board, no copper under antenna).
* **T5838 mic footprint**:

  * Bottom port hole diameter **0.5–1.0 mm**; pick a value and lock it.
  * Make sure your courtyard and keepouts exist so no paste/flux ends up in the port.
* **CSNP64GCR01‑BOW footprint**: confirm exact land pattern for your sourced package (this is a common gotcha).
* **nPM1300 QFN footprint**: ensure exposed pad thermal via strategy matches your “flat bottom” goal (see layout section below).

If any of these footprints are “unknown provenance”, stop and validate now.

---

### Step 3 — Decide PCB stackup that matches your “thin + RF + switching + flat bottom” needs

I strongly recommend one of these two:

#### Option A (recommended): **4‑layer, 0.4 mm “advanced”**

* Meets “ultra thin” while giving you:

  * Solid internal ground plane (Layer2)
  * A power plane / routing layer (Layer3)
  * Cleaner RF + switcher containment

PCBWay says 4‑layer minimum can be **0.40 mm** (advanced).

#### Option B (extreme): **2‑layer, 0.2 mm**

* Only do this if you accept higher EMI/noise risk and trickier routing.
* Still compatible with nPM1300 guidance (“minimum 2 layers incl. ground plane; no bottom components”).

Given you have **two switchers + RF + fast digital**, Option A is the safer first spin.

---

### Step 4 — Pre-layout constraints (define these before placing parts)

1. **Antenna keepout**

   * No copper under the antenna region on any layer; place module at edge with antenna outside board.
2. **Mic acoustic keepout**

   * Define a “no copper/no vias” ring around the mic port hole.
   * Decide whether the bottom side is allowed to have soldermask (usually yes) but no exposed copper.
3. **“Flat bottom” definition**

   * If you truly need *mechanically flat*, limit through‑vias in the mic area and consider tented vias elsewhere.
   * For QFN thermal pad vias, consider **filled/capped** (costly) or move vias away from exposed pad and use thermal spokes.

---

### Step 5 — Placement plan (what goes where on a 19 mm circle)

Here’s the placement strategy that minimizes RF + audio + switcher interference:

* Put the **HJ module at the board edge**, with antenna portion “hanging off” the edge per vendor guidance.
* Put **both inductors + nPM1300** as far from the antenna as possible (ideally opposite side of the circle).
* Put the **mic**:

  * Close to the center-ish location that best aligns with your enclosure port.
  * Far from inductors/switch node copper.
* Put the **level shifter** adjacent to mic (short 1.8 V domain), unless routing forces otherwise.
* Put the **NAND** close to the module pins you’re using for SPI; keep CLK shortest and place the series resistor near the driver.

---

### Step 6 — Routing plan (prioritized)

1. **Power first** (no exceptions)

   * nPM1300 loop areas tight: SW node copper minimal, inductor + output cap tight, ground returns short.
   * Respect inductor/cap specs from Nordic guidance (Isat >350 mA, Imax >200 mA, DCR ≤400 mΩ, Ceff ≥4 µF).
2. **RF second**

   * Keepout compliance and short RF interconnect between PIN23 and PIN24 via matching network.
3. **High‑speed digital**

   * NAND CLK: short, series resistor near MCU, continuous reference plane.
4. **PDM**

   * Keep CLK and DATA tidy, avoid running near SW nodes.
5. **I2C**

   * Short bus, pull‑ups close, avoid crossing noisy regions.

---

### Step 7 — PCBWay ordering/DFM package (prepare this before you ever click “Order”)

You will need (for PCBWay PCBA):

* Gerbers + drills + IPC‑356 netlist (if possible)
* BOM with explicit DNP and “do not source” flags
* Pick&Place
* Assembly drawing (top only)
* Panel drawing or clear instruction: 19 mm circle requires review and probably panelization (PCBWay notes min finished size ≥20 mm and 10–20 mm requires review).

Also: expect you’ll need a **panel with rails** for assembly anyway (PCBWay EMS also notes small boards need panelization; minimum board size can be 10×10 and smaller must be panelized).

---

### Step 8 — Bring-up plan (so you can prove the board works fast)

Order of operations once boards arrive:

1. Measure **VOUT1=1.8 V** and **VOUT2=3.0 V** at test pads (add these test pads now).
2. SWD program: confirm debug interface + reset behavior.
3. I2C: confirm PMIC comms.
4. Mic: feed PDM clock, verify DATA toggles; validate channel select.
5. NAND: read JEDEC/device ID, then do small read/write test.

---

## 6) Final “go/no-go” checklist before placement/routing

You are **NOT ready to place/rout** until these are true:

* [ ] **SHPHLD series resistor fixed** (0 Ω or removed).
* [ ] **CC decision made** (100 mA limit accepted, or CC pins routed out).
* [ ] **HJ module sourcing decision** made and documented (BOM/assembly).
* [ ] **Footprints verified** (HJ module, T5838, NAND, nPM1300).
* [ ] **Board stackup chosen** (recommend 4‑layer 0.4 mm advanced).
* [ ] **Antenna keepout defined on all layers** and placement constraints understood.
* [ ] **Mic hole diameter fixed** (0.5–1.0 mm) and keepout rules decided; thickness is OK for mic performance.
* [ ] **Pogo map consistent** between main and adapter (or you intentionally drop unused pogo signals).

---

## Bottom line

Your architecture is *very close* to a first‑spin‑worthy design, but two schematic issues are **true blockers**:

1. **SHPHLD series 10 kΩ is wrong** (it defeats logic‑low detection). Fix it.
2. Decide whether you accept **100 mA VBUS limit** (CC pins floating) or want to support higher current via CC routing.

Once those are fixed and footprints are validated, you’ll be in a good position to start placement/routing with a **clear, low‑risk** DFM plan for PCBWay and an actionable bring‑up checklist.

If you want, I can also propose a **specific 4‑layer 0.4 mm stackup + exact placement sketch** (where to put module/mic/PMIC on a 19 mm circle) based on the keepouts—but the two schematic blockers above should be resolved first because they can change pad count and board edge constraints.
