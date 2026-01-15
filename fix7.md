# Preface

Below is an “end-to-end” review of what you have **right now** (atopile sources + build artifacts), what is **correct**, what is **risky / wrong / missing**, and an **opinionated final checklist** to get you from this repo state to a manufacturable 19 mm ultra-thin PCBWay build.

I’m going to separate this into:

1. What the design currently is (as-built by atopile)
2. Electrical correctness + “are we missing anything critical?”
3. Part picking/BOM/logs issues (what WILL bite you at order time)
4. Thin round PCB constraints (PCBWay + layout rules you must follow)
5. A complete “next steps” plan (no hand-waving)

---

## 1) What you currently have (from `main.ato` + build outputs)

### Core architecture (confirmed)

* **U5: HJ‑N54L_SIP (nRF54L15 module)** powered from a “3V3” rail (in the KiCad netlist this ends up named **VCCB**, but functionally it is your 3.3 V rail).
* **U7: nPM1300** generates:

  * **BUCK1 ≈ 1.8 V** (netlist names this **VCCA**) used for the T5838 mic + the low-side of level shifters.
  * **BUCK2 ≈ 3.3 V** (netlist names this **VCCB**) used for the nRF54 module + SD NAND + high-side of level shifters.
* **U6: CSNP64GCR01‑BOW (SD NAND)** wired as **SPI mode** (CLK/CMD/DAT0/CS(DAT3)) with the right style of pull-ups and a series resistor on CLK.
* **MK1: T5838 PDM mic** powered at **1.8 V**, with:

  * PDM CLK and host control lines level shifted **3.3 → 1.8**
  * PDM DATA and WAKE level shifted **1.8 → 3.3**
* **4× SN74LVC1T45** used as single-bit translators (CLK, DATA, THSEL, WAKE).

### Single-sided population requirement (confirmed)

Your generated KiCad PCB has **all footprints on F.Cu** (front/top). No footprints placed on bottom. That satisfies the “components on one side” constraint.

### But: layout is not actually “a 19 mm board” yet

Your `layouts/main/main.kicad_pcb` currently contains:

* footprints staged in a column (auto-placement staging),
* **no board outline**,
* **no routing**,
* **no zones/ground pours**,
* **no antenna keepout drawings**,
* **no panelization**.

So electrically the netlist is coherent, but **this is not yet a manufacturable PCB**.

---

## 2) Electrical validation: “did we pick all required parts?” and “are connections correct?”

### 2.1 nPM1300 power tree: correct, but with firmware/boot assumptions

#### VSET resistors (required, and you did it correctly)

nPM1300 BUCK outputs require the **VSET1/VSET2** resistor-to-GND straps; leaving them floating is explicitly disallowed, and the datasheet provides a resistor table including **47 kΩ for 1.8 V** and **470 kΩ for 3.3 V**.

Your design:

* R13 = **47 kΩ** on VSET1 (BUCK1 → 1.8 V) ✅
* R14 = **470 kΩ** on VSET2 (BUCK2 → 3.3 V) ✅

#### CC1/CC2 left unconnected: allowed, but know the consequence

You intentionally leave **CC1/CC2** floating. Datasheet explicitly says that if USB‑C current detection isn’t used, **CC pins can be left floating or tied to GND**, and that without CC detection the **default VBUS current limit remains at 100 mA** until configured by the host.

✅ Electrically acceptable.
⚠️ System-level implication: if you rely on “fast charge” or high load on VBUS, you must configure current limit over TWI when the MCU is alive.

#### NTC tied to GND: allowed, and you followed the recommended “no thermistor” approach

The nPM1300 datasheet states that if a thermistor is not used, **NTC must be tied to GND** (directly or through a resistor) and the NTC function disabled via register.

You implemented: **R10 = 0 Ω from NTC to GND** ✅

⚠️ Firmware requirement: your early boot must disable NTC function, otherwise the PMIC may interpret “NTC=GND” as extreme temperature and block charging behavior depending on configuration.

#### SHPHLD: electrically OK to leave as a pad (internal pull-up exists)

nPM1300 has an **internal pull-up (≈50 kΩ)** on SHPHLD to VBAT/VBUS (whichever is higher). ([download.mikroe.com][1])
So leaving it only on a pogo/test pad is not “floating undefined”. ✅

⚠️ Product feature question: if you ever enable Ship mode, you must have a real way to pull SHPHLD low for the required time to exit Ship/Hibernate. You currently only have a pogo pad to do that (fine for development; questionable for “final product” unless the enclosure/fixture supports it).

#### Decoupling network: broadly correct and matches guidance

You have:

* VBUS: 10 µF + 100 nF
* VBAT: 10 µF
* VSYS: 10 µF
* PVDD: 1 µF + 100 nF
* VOUT1 (1.8): 10 µF + 100 nF
* VOUT2 (3.3): 10 µF + 100 nF
* VDDIO: 1 µF + 100 nF

nPM1300 reference guidance recommends at least a 2-layer PCB with GND plane, and gives typical inductor/cap specs for the bucks (2.2 µH inductors, ceramic caps). 

✅ Your passive choices are consistent with that.

**Opinionated tweak**: add one dedicated bulk cap **near the HJ module VDD pins** (e.g., 4.7–10 µF 0402/0603) even if the rail already has bulk elsewhere. The radio’s burst current is local; you want local bulk.

---

### 2.2 HJ‑N54L_SIP module: pin usage + antenna approach is sensible

#### Power range and IO thresholds

Module VDD range is **1.7–3.6 V**, so a 3.3 V rail is valid. 
The manual also states a digital input high threshold like **VIH ≈ 0.7×VDD**, which is why a ~1.26 V high from the mic would not reliably read as high when the MCU is at 3.3 V. 

✅ This justifies your level shifting on mic DATA/WAKE.

#### Reserved pins P1.00/P1.01 (you correctly avoided)

Manual warns P1.00/P1.01 are connected to a 32.768 kHz oscillator circuit and generally not recommended as GPIO unless you know what you’re doing. 
✅ You left them NC.

#### RF / antenna matching network

The module doc describes connecting RF/BOARD_ANT with a matching circuit and keeping antenna area free of copper/components/traces around and on the back side.
✅ Your PI network footprint approach (series 0 Ω + DNP shunts) is the correct “prototype/tune” pattern.

**BUT**: the antenna keepout is a **layout** requirement. Right now you have no keepout in KiCad, so this is only “correct on paper”.

---

### 2.3 CSNP64GCR01‑BOW SD NAND: interface + passives match datasheet/reference

Key requirements from the SD NAND family reference design:

* Pull-ups on **CMD and DAT0–DAT3** (10 k–100 k typical)
* A **series resistor on CLK** (0–120 Ω)
* A **2.2 µF** local VCC cap recommended
  Your chip’s own datasheet also shows similar guidance and a supply range around **2.7–3.6 V**.

Your design:

* 10 k pull-ups on CMD/DAT0/DAT3 ✅
* DAT1/DAT2 pulled up ✅
* 33 Ω CLK series resistor ✅
* 100 nF + 2.2 µF on VCC ✅

Also, “all DAT lines pulled up even if unused” is a common SD requirement and is documented in platform guidance too.

✅ Electrically coherent.

**Opinionated tweak**: keep the 33 Ω CLK resistor physically **at the MCU clock source** (not at the NAND). That’s how you get the damping benefit.

---

### 2.4 T5838 mic: supply/logic levels + “no pull-up on DATA” handled correctly

From the T5838 datasheet:

* Operating VDD is **~1.62–1.98 V**, so it must be on your 1.8 V rail, not 3.3 V.
* The **PDM DATA line should not have pull-up or pull-down resistors**, because the mic tri-states half cycles.
* A **clock termination resistor** may be used to reduce ringing; your series resistor aligns with that.
* PCB thickness doesn’t materially affect mic performance; port hole sizing guidance exists (0.5–1.0 mm typical).

Your design:

* Mic VDD = 1.8 ✅
* No pull-up on DATA (DNP bias resistor) ✅
* Series resistor on CLK ✅
* Footprint includes a ~0.5 mm NPTH acoustic hole ✅

**One subtlety**: you hard-tied SELECT to GND, so you’re forcing “Right channel” behavior. That’s fine, but your firmware must sample the correct edge/channel.

---

### 2.5 Level shifting: direction logic is correct (and you avoided a classic mistake)

TI’s SN74LVC1T45 DIR pin is powered/referenced to **VCCA**, not VCCB.
You correctly drive DIR from **GND or V1V8**, never from 3.3 V. ✅

Direction usage:

* CLK, THSEL: 3.3 → 1.8, DIR=0 ✅
* DATA, WAKE: 1.8 → 3.3, DIR=1 ✅

**Opinionated alternative** (worth considering for area + BOM):

* Replace four 1-bit translators with one **multi-bit dual-supply translator** (e.g., 4-bit). This saves area and decoupling caps, and routing becomes cleaner. The current approach is electrically fine, but it’s not “minimum-area/parts”.

---

## 3) Atopile build outputs/logs/BOM: the things that are objectively broken today

### 3.1 The generated main BOM is incomplete for real manufacturing

Your `build/builds/main/main.bom.csv` includes nPM1300, SD NAND, mic, translators, passives, inductors — but **does not include the HJ‑N54L_SIP module**.

Reason: atopile has “no picker” for that module, so it isn’t a sourced/selected part and gets dropped from the BOM.

✅ Electrically OK (the netlist still contains it)
❌ Manufacturing-terrible: PCBWay assembly BOM must list it as either:

* sourced part (if they can buy), or
* **customer-supplied / consigned** part (and still included in BOM + CPL).

**Action**: make sure your manufacturing BOM includes U5 with:

* manufacturer, MPN, description
* “do not place” = false (i.e., it should be placed)
* sourcing = “customer supplied”

### 3.2 BOM designators are “compressed/truncated”

Rows like `C1,C2,C24,C25,C...` and `C3,C4,C5,C6,C...` are not safe for assembly workflows.
You want a BOM with explicit full designator lists.

**Action**: generate a proper KiCad BOM (or post-process atopile BOM) for PCBWay.

### 3.3 Part-locking bug: your inductor “lcsc” assignment is ignored

You tried:

```ato
l1.lcsc = "C2886804"
l2.lcsc = "C2886804"
```

atopile warns that `Inductor` has no attribute `lcsc`, so **your intended lock did not apply**.

That means the inductor chosen by pickers could change if constraints shift.

**Action** (pick one):

* define a specific “Inductor_2u2_0603_C2886804” atomic part, or
* use a part-picking trait supported by your library, or
* accept picker choice but freeze the BOM after first successful pick and stop re-picking.

### 3.4 “No pickers” warnings: which ones matter?

* **mcu|HJ_N54L_SIP_package**: matters (must be in final BOM as consigned)
* DNP parts: fine
* pogo/battery pads: fine (not real components)
* Some pads show “missing fields” warnings: harmless, but you should keep them out of assembly BOM/CPL

---

## 4) Thin 19 mm PCB + PCBWay realities you must design for

### 4.1 PCBWay can do 0.2 mm / 0.4 mm, but 0.2 mm changes the game

PCBWay’s capability info indicates finished thickness options include **0.2 mm** (and typical tolerance ±0.1 mm for <1 mm boards). ([pcbway.com][2])

**Opinionated recommendation**:

* Prototype **0.4 mm first**.
* Only go 0.2 mm after you validate:

  * RF/antenna performance
  * assembly warpage and soldering yield
  * mechanical handling and panelization strategy

0.2 mm is possible, but it’s a “DFM hard mode” setting.

### 4.2 PCBWay assembly requires panelization for a 19 mm disc

PCBWay assembly capabilities list a **minimum board size** (e.g., 50×100 mm) for assembly. ([m.pcbway.com][3])
A 19 mm round PCB must be **panelized** with rails, fiducials, and tooling holes.

**Action**: design a panel (or ask PCBWay to panelize) with:

* at least 2–3 global fiducials
* tooling holes
* mouse-bites or tabs (for round boards)
* keep your “real board” bottom surface clean, but allow panel rails to carry fiducials/handling features

### 4.3 0201 assembly is supported, but comes with procurement rules

PCBWay supports very small passives (they claim down to 01005 / 0201), but their assembly notes include special handling requirements and extra quantity expectations for tiny passives. ([pcbway.com][4])

**Opinionated advice**:

* If you want smooth assembly + rework: consider bumping many passives to **0402** unless the area truly forces 0201.
* If you keep 0201: be ready for higher cost and stricter “extra component” requirements.

### 4.4 “Bottom side empty/flat” is mostly a layout discipline problem

You can keep the bottom flat if you:

* Place **no footprints** on bottom (already true)
* Use **tented vias** (no exposed bottom copper)
* Keep **all silkscreen off bottom**
* Ensure only the mic port NPTH is open

But be aware:

* RF and power integrity often want **ground stitching vias**. You can still do that — just tent them.

---

## 5) The big missing piece: your KiCad PCB is not routed/placed yet

This is the most important point:

✅ The atopile **electrical netlist** is coherent.
❌ You do not yet have a **layout** that meets:

* 19 mm circle outline
* antenna keepout
* mic keepout
* routing
* copper pours / return paths
* DRC
* manufacturability

So the “next steps” are 80% layout + DFM, not more atopile code.

---

## 6) Opinionated, complete “next steps” plan

### Phase A — Freeze the electrical design (do this before any serious layout)

1. **Decide if BUCK2 must be “true 3.3 V” at all battery levels**

   * nPM1300 bucks are step-down; if VSYS drops low, BUCK2 can’t boost.
   * Your loads are tolerant (HJ module accepts down to 1.7 V; NAND needs ~2.7 V).
   * So it’s probably fine to call it “3V3 nominal”, but make firmware enforce a battery cutoff above NAND minimum.

2. **Confirm your firmware plan for the two critical PMIC settings**

   * Disable NTC (because you tied it to GND).
   * Raise VBUS input current limit if desired (because CC pins are not used).
     Write these down in a bring-up checklist and do them in the first 10–50 ms of boot.

3. **Keep the DNP mic data bias resistor as DNP**

   * Datasheet explicitly warns not to add pull-ups/pull-downs on DATA.
     Don’t “helpfully populate it” during assembly.

4. **Add a local bulk cap at the HJ module**

   * Add 4.7–10 µF near U5 VDD pins.
     This is cheap insurance and helps RF TX burst stability.

5. **Decide whether you really need THSEL and WAKE**

   * If AAD wake/threshold functionality is core, keep them.
   * If not, you can delete two shifters + pads + routing complexity.

---

### Phase B — Fix BOM/manufacturing metadata (so PCBWay assembly isn’t painful)

6. **Add the HJ module to the BOM as consigned**

   * Even if it can’t be sourced via LCSC, it must be listed.
   * Ensure it appears in the CPL (pick&place) so PCBWay places it.

7. **Stop relying on the current `main.bom.csv`**

   * Create a “PCBWay BOM” and “PCBWay CPL” from KiCad once placement is final.
   * Ensure designators are explicit (no truncation).

8. **Lock the inductor choice**

   * Replace the ignored `l1.lcsc = ...` with an actual atomic part definition / fixed picker constraint.

---

### Phase C — Real PCB layout work (this is the main event)

9. **Create the 19 mm outline in KiCad**

   * Center at origin.
   * Add a reference cross / center marker on *top silkscreen only* (or no silkscreen at all).

10. **Place U5 (HJ module) first, by RF rules**

* Put antenna edge at the PCB edge as recommended. 
* Implement the antenna keepout:

  * No copper under/around antenna region (both layers)
  * No traces in that region
  * No components on top in keepout
  * Bottom side already empty, but you must also clear copper pour there

11. **Place RF matching PI network immediately at the RF pins**

* Keep series element and shunts tight and symmetric.
* Leave DNP shunts as footprints only.

12. **Place PMIC + inductors + caps as a tight power “island” away from antenna and mic**

* Minimize SW node copper (SW1/SW2) area.
* Put input/output caps *right at the pins*.
* Keep inductors away from the mic (EMI + mechanical).

13. **Place SD NAND close to MCU pins**

* Route CLK with series resistor near MCU.
* Keep CMD/DAT traces short and with solid return reference.

14. **Place mic where the enclosure wants it, then keep it “quiet”**

* Keep it away from inductors and SW nodes.
* Put its decoupling caps right next to VDD pin.
* Ensure the NPTH port is the only bottom opening.

15. **Decide the layer strategy (strong recommendation)**

* **2-layer** board:

  * Top: signals + power routing
  * Bottom: mostly solid GND plane (with antenna keepout void)
* Tent all vias on bottom to keep “flat”.

16. **Route with these priorities**

* Power loops (PMIC → inductor → output cap) first
* Ground returns next (stitch around PMIC, around NAND, around module)
* High-speed/edge-rate lines:

  * NAND CLK (short, source-terminated)
  * PDM CLK (short, source-terminated)
* I2C last (slow, tolerant)

17. **Do not ignore the nPM1300 exposed pad paste pattern**

* Review pad 33 paste coverage; consider windowing/relief apertures to avoid “float”.
* This matters more on thin boards.

---

### Phase D — DRC/DFM + PCBWay submission readiness

18. **Run full KiCad DRC**

* Add no-connect flags for intentionally unused pins (CC1/CC2, GPIOs, etc.)
* Ensure NPTH mic port has proper mask clearance and no copper slivers.

19. **Panelization plan (mandatory for assembly)**

* Since PCBWay assembly has minimum board size guidance, panelize multiple discs with rails. ([m.pcbway.com][3])
* Put fiducials + tooling holes on rails (not on your “clean” board surface).

20. **Generate manufacturing outputs**

* Gerbers + drill
* IPC-356 netlist if you want
* BOM + CPL for PCBWay (cleaned: DNP excluded, pads excluded, U5 included as consigned)

21. **Assembly notes to include**

* Board thickness target (0.4 first; 0.2 later)
* “Bottom side no components; only mic port NPTH open”
* Tented vias on bottom
* DNP parts not placed (antenna shunts, mic data bias)
* Center-pad paste strategy for nPM1300

---

### Phase E — Firmware bring-up checklist (so you don’t misdiagnose hardware)

22. First power-on on bench supply:

* Verify VOUT2 ~3.3 V, VOUT1 ~1.8 V
* Verify ripple isn’t insane at idle/load
* Verify PMIC I2C responds

23. Earliest firmware init (must-do):

* Disable NTC function (since tied to GND).
* If VBUS present, configure VBUS current limit above default 100 mA if needed.

24. Validate peripherals:

* PDM clock rate vs mic spec; confirm channel selection matches your SELECT strap.
* SD NAND SPI init + read CID/CSD + write test; confirm pull-ups not fighting.

---

## Bottom line verdict

### Electrically: **mostly correct**

* Power tree and required passives for nPM1300: ✅ (and aligns with datasheet requirements) ([download.mikroe.com][1])
* SD NAND SPI wiring + pull-ups + CLK series + decoupling: ✅
* Mic rail + “no DATA pull resistors” + clock termination option + hole size: ✅
* Level shifting direction correctness: ✅

### Project readiness: **not ready to manufacture**

The blocker is **layout/DFM**, not the netlist:

* No 19 mm outline
* No placement strategy
* No routing/planes
* No antenna keepout implemented
* BOM missing the main module (U5) and not PCBWay-ready

### PCBWay constraints: feasible, but panelization mandatory

* 0.2 mm thickness is within stated capability ranges, and 0201 assembly is possible. ([pcbway.com][2])
* But your disc must be panelized for assembly. ([m.pcbway.com][3])

---

If you want, I can also produce a **placement + routing blueprint** for a 19 mm disc (component-by-component placement order, keepout drawings, suggested zone strategy, and a routing priority map) based directly on your exact footprints—i.e., a “do this in KiCad” map that you can follow step-by-step.

[1]: https://download.mikroe.com/documents/datasheets/nPM1300_datasheet.pdf "nPM1300"
[2]: https://www.pcbway.com/capabilities.html "PCB Capabilities - Custom PCB Prototype the Easy Way - PCBWay"
[3]: https://m.pcbway.com/assembly-capabilities.html "PCB Assembly Capabilities - Custom PCB Prototype the Easy Way - PCBway"
[4]: https://www.pcbway.com/assembly-capabilities.html "Printed Circuit Board (PCB) Assembly Services - PCBWay"


# Actions

Below is a **very opinionated, “do-this-next”** plan that resolves each of the specific remaining issues you listed, with **exact Atopile edits**, **validated LCSC parts**, and what to do before you move on to placement/routing.

---

## 1) Replace 4× 1‑bit translators with 1× multi‑bit translator (validated, tiny)

### Best “one-chip” candidate

Use **TI SN74AXC4T774RSVR** (4‑bit dual‑supply translator, **independent DIR per bit**, tiny package).

* **Why this one works for your mixed-direction signals (CLK/THSEL down, DATA/WAKE up)**
  It has **DIR1..DIR4**, so you can set **each channel’s direction independently** (unlike 4T245-style parts where DIR applies to all bits).
* **Package / size:** **UQFN‑16 (RSV)** ~ **1.8 × 2.6 mm** (no big thermal pad to fight on an ultra-thin PCB).
* **Validated LCSC part:** **C1849454** (MPN: **SN74AXC4T774RSVR**)

### One important caveat (mic datasheet vs translator)

SN74AXC4T774 includes **weak pull‑downs on data I/Os**.
The TDK T5838 datasheet explicitly says **don’t add pull-up/pull-down resistors on PDM_DATA** (because the line is tri-stated at times).
In practice, with a **single mic** and **very weak** pull-downs, this is *often fine*, but it is a real spec conflict you should be aware of.

If you want to be *strict* about the mic guidance, the safest alternative is **two 2‑bit translators** (one fixed each direction). But since you asked specifically for “one multi-bit,” the SN74AXC4T774 is the cleanest single-chip solution.

You should keep the T5838 datasheet handy while you decide this: 

---

### EXACT Atopile changes for the single‑chip translator

#### (A) Add the new part to `parts/`

Use atopile’s built-in part fetcher:

1. In your project root:

```bash
ato create part
```

2. When prompted for a search term, enter:

```text
C1849454
```

This is exactly what `ato create part` is for: it creates the part definition with pinout/footprint and adds `has_part_picked`. ([docs.atopile.io][1])

It should generate something like:

```
parts/Texas_Instruments_SN74AXC4T774RSVR/Texas_Instruments_SN74AXC4T774RSVR.ato
```

(If the folder name differs slightly, adjust the import path in the next step.)

---

#### (B) Edit `main.ato`: replace the 4 translators + 8 decouplers with 1 + 2

**1) Replace the import at the top**

In `main.ato`, replace:

```ato
from "parts/Texas_Instruments_SN74LVC1T45DPKR/Texas_Instruments_SN74LVC1T45DPKR.ato" import Texas_Instruments_SN74LVC1T45DPKR_package
```

with:

```ato
from "parts/Texas_Instruments_SN74AXC4T774RSVR/Texas_Instruments_SN74AXC4T774RSVR.ato" import Texas_Instruments_SN74AXC4T774RSVR_package
```

---

**2) Replace the whole “Microphone level shifting” block**

You currently have:

* `level_shifter_clk/data/thsel/wake` (4 parts)
* `c_ls_*_vcca` and `c_ls_*_vccb` (8 caps)

Replace that whole section with **this** (drop-in block):

```ato
    ## Microphone level shifting (single 4-bit translator)
    ## TI SN74AXC4T774: DIRx=1 => Ax→Bx, DIRx=0 => Bx→Ax when OE=0 (enabled)
    ## OE=1 => Hi-Z on all I/Os
    ## Control pins referenced to VCCA (we use VCCA=1.8V domain) 

    level_shifter_pdm = new Texas_Instruments_SN74AXC4T774RSVR_package

    # Local decoupling (one per rail, placed right at the IC)
    c_ls_vcca = new Capacitor
    c_ls_vcca.value = 100nF +/- 10%
    c_ls_vcca.max_voltage = 6.3V
    c_ls_vcca.package = "0201"

    c_ls_vccb = new Capacitor
    c_ls_vccb.value = 100nF +/- 10%
    c_ls_vccb.max_voltage = 6.3V
    c_ls_vccb.package = "0201"

    v1v8 ~ level_shifter_pdm.VCCA
    v3v3 ~ level_shifter_pdm.VCCB
    gnd  ~ level_shifter_pdm.GND

    v1v8 ~ c_ls_vcca.positive
    gnd  ~ c_ls_vcca.negative
    v3v3 ~ c_ls_vccb.positive
    gnd  ~ c_ls_vccb.negative

    # Always enabled: OE is active-high Hi-Z, so tie OE low to enable 
    gnd ~ level_shifter_pdm.OE

    # Assign directions per signal:
    # A-side = MIC (1.8V), B-side = MCU (3.3V)
    # DATA/WAKE: A->B => DIR=1
    # CLK/THSEL: B->A => DIR=0
    gnd  ~ level_shifter_pdm.DIR1   # CLK   B->A
    v1v8 ~ level_shifter_pdm.DIR2   # DATA  A->B
    gnd  ~ level_shifter_pdm.DIR3   # THSEL B->A
    v1v8 ~ level_shifter_pdm.DIR4   # WAKE  A->B

    # Wiring (preserve your existing pin choices)
    # CLK (MCU -> MIC, with series resistor)
    mcu.P1_11 ~ level_shifter_pdm.B1
    level_shifter_pdm.A1 ~ r_pdm_clk.p1
    r_pdm_clk.p2 ~ mic.CLK

    # DATA (MIC -> MCU)
    mic.DATA ~ level_shifter_pdm.A2
    mcu.P0_05 ~ level_shifter_pdm.B2

    # THSEL (MCU -> MIC)
    mcu.P0_13 ~ level_shifter_pdm.B3
    mic.THSEL ~ level_shifter_pdm.A3

    # WAKE (MIC -> MCU)
    mic.WAKE ~ level_shifter_pdm.A4
    mcu.P0_04 ~ level_shifter_pdm.B4
```

**Notes:**

* This wiring assumes your generated part uses pin names like `A1/B1/DIR1/...`. That is consistent with TI naming and is how `ato create part` typically outputs pins. If your generated `.ato` names them differently, match the names in the generated file.
* This cuts translator-related BOM and placement massively (4 ICs → 1 IC, 8 caps → 2 caps).

---

## 2) “Main BOM is incomplete for real manufacturing” — what’s happening, and exact fix

### Root cause (in your logs)

Your `build/logs/.../main/bom.info.log` shows BOM generation is **skipping anything missing `has_part_picked`** (notably your HJ module), so it never appears in `main.bom.csv`.

This behavior is consistent with atopile’s model: **BOM is for “picked physical parts.”**
Docs explicitly say `has_part_picked` is what tells the compiler it can pick a part to fill the spot. ([docs.atopile.io][1])

### The fix (specific)

You must add `has_part_picked` to the HJ module **even if it’s consigned**, so it is treated as a “real BOM line-item.”

---

## 3) Add the HJ module to BOM as **CONSIGNED** (PCBWay-friendly)

### EXACT file to edit

`parts/HJ_N54L_SIP/HJ_N54L_SIP.ato`

### EXACT change

Add `has_part_picked` and make the **Value** clearly say “CONSIGNED” so PCBWay doesn’t assume they must source it.

Here is a literal patch you should apply:

```diff
 #pragma experiment("TRAITS")
 import has_datasheet_defined
 import has_designator_prefix
+import has_part_picked
 import is_atomic_part
 import is_auto_generated

 component HJ_N54L_SIP_package:
-    """HJ-N54L_SIP"""
+    """HJ-N54L_SIP (CONSIGNED BY CUSTOMER)"""
     trait is_atomic_part<manufacturer="HJSIP", partnumber="HJ-N54L_SIP", footprint="HJ-N54L_SIP.kicad_mod", symbol="HJ-N54L_SIP.kicad_sym">
+    # Make it appear in BOM output, but mark as consigned
+    trait has_part_picked::by_supplier<supplier_id="consigned", supplier_partno="HJ-N54L_SIP", manufacturer="HJSIP", partno="HJ-N54L_SIP">
     trait has_designator_prefix<prefix="U">
```

Now rebuild and confirm:

* `build/builds/main/main.bom.csv` includes `HJ_N54L_SIP_package` line item
* “Value” column includes “(CONSIGNED BY CUSTOMER)”

### Why “3.0V vs 3.3V” matters here

The HJ module’s recommended operating VCC range is **1.7V min, 3.3V typ, 3.6V max**.
So it is perfectly happy on a **3.0V** main rail.

---

## 4) BOM designators are “compressed/truncated” — what to do EXACTLY

Atopile’s BOM format is “grouped by part,” so designators are **intentionally aggregated** in one cell (e.g., `C5, C6, ...`). Some assembly workflows want **one designator per row** or no spaces.

### Best practical solution (do this, don’t fight atopile)

Post-process `main.bom.csv` into a **PCBWay BOM** format.

Create `scripts/explode_bom.py`:

```python
import csv
from pathlib import Path

IN = Path("build/builds/main/main.bom.csv")
OUT = Path("build/builds/main/main.bom.exploded.csv")

with IN.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

out_fields = ["Designator","Footprint","Quantity","Value","Manufacturer","Partnumber","LCSC Part #"]

exploded = []
for r in rows:
    # split designators like: "C1, C2, C3"
    des = [d.strip() for d in r["Designator"].split(",")]
    for d in des:
        nr = dict(r)
        nr["Designator"] = d
        nr["Quantity"] = "1"
        exploded.append(nr)

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=out_fields)
    w.writeheader()
    w.writerows(exploded)

print(f"Wrote {OUT} with {len(exploded)} rows")
```

Run:

```bash
python3 scripts/explode_bom.py
```

Now you have:

* `main.bom.csv` (grouped “engineering BOM”)
* `main.bom.exploded.csv` (assembly-friendly “one designator per row”)

This resolves the “compressed/truncated” complaint without waiting for atopile BOM exporter features.

---

## 5) “Inductor lcsc assignment is ignored” — exact reason + exact fix

### Why it happens

In `main.ato` you wrote:

```ato
l_buck1.lcsc = "C394950"
```

But atopile’s global attribute is **`lcsc_id`**, not `lcsc`. ([docs.atopile.io][1])
So the compiler warns and ignores it (which matches your log).

### EXACT fix in `main.ato`

Change both inductors:

```diff
-    l_buck1.lcsc = "C394950"
+    l_buck1.lcsc_id = "C394950"

-    l_buck2.lcsc = "C394950"
+    l_buck2.lcsc_id = "C394950"
```

That should:

* remove the warning
* **force the exact part** selection for both inductors

---

## 6) Lock the inductor choice — what to do EXACTLY

Do **both** of these (belt + suspenders):

1. Use the correct override attribute:

* `l_buck1.lcsc_id = "C394950"`
* `l_buck2.lcsc_id = "C394950"`

2. Verify the build result:

* confirm `build/builds/main/main.bom.csv` shows **LCSC Part # = C394950** for both inductors

This guarantees the pick doesn’t drift if the passive picker improves/changes later.

---

## 7) “Decide if BUCK2 must be true 3.3V at all battery levels” — what I meant + what you should do

### What I meant (in plain terms)

nPM1300’s BUCK2 is a **step-down (buck) regulator**.
A buck **cannot boost**. So if the battery falls below your programmed output (plus dropout), BUCK2 will eventually go into **dropout** and the “3.3V rail” will sag toward battery.

So you cannot have a guaranteed 3.3V rail across the full Li-ion discharge curve without a buck-boost.

### Why you probably *don’t want* “always true 3.3” here

Your key loads have these supply ranges:

* **HJ-N54L_SIP**: recommended **1.7V–3.6V**
* **SD NAND (CSNP64GCR01)**: power supply **Vcc = 2.7V–3.6V**

That means **3.0V main rail is totally valid** for both.

### My opinionated recommendation (do this)

Set BUCK2 nominal to **3.0V**, not 3.3V, so you get **regulated operation for more of the battery curve**, and you’re still within both module + NAND specs.

nPM1300 explicitly supports configuring VOUT2 to **3.0V using VSET2 = 150kΩ**.

#### EXACT hardware change in Atopile (`main.ato`)

Change:

```diff
-    r_vset2.resistance = 470kohm +/- 1%  # VSET2 = 470k => 3.3 V
+    r_vset2.resistance = 150kohm +/- 1%  # VSET2 = 150k => 3.0 V
```

(And ideally rename your net from `v3v3` to something like `vdd` or `v3v0` so the name is truthful.)

### Firmware handling plan (battery-only device)

Do **not** try to “keep 3.3 always.” Instead:

1. Run VDD at 3.0V.
2. Monitor battery (nPM1300 has measurement features; exact method depends on your firmware stack).
3. When VBAT approaches your chosen cutoff, stop flash writes cleanly and go to a low-power mode / shutdown.

This aligns with your “battery all the time” usage, keeps the board tiny, and avoids adding a buck-boost IC.

---

## 8) FINAL checklist: do these steps (in this exact order) before placement/routing

1. **Fix the inductor override**

   * Edit `main.ato`: change `.lcsc` → `.lcsc_id` for both buck inductors.

2. **Decide BUCK2 voltage**

   * Recommended: set VOUT2 = **3.0V** by changing `r_vset2` to **150k**
   * Optionally rename net `v3v3` → `vdd` or `v3v0` to avoid future confusion.

3. **Add HJ module to BOM as consigned**

   * Patch `parts/HJ_N54L_SIP/HJ_N54L_SIP.ato` with `has_part_picked` and change the docstring value to “(CONSIGNED…)” ([docs.atopile.io][1])

4. **Replace 4 translators with 1 translator**

   * Run `ato create part`, search `C1849454` ([docs.atopile.io][1])
   * Update `main.ato`:

     * remove 4× SN74LVC1T45 + 8 caps
     * add 1× SN74AXC4T774 + 2 caps
     * wire DIRx and OE exactly as described
   * Keep in mind the mic’s “no pull-down” note on PDM_DATA; decide if you accept the weak internal pulls.

5. **Rebuild and validate artifacts**

   * `ato build`
   * Confirm:

     * no “Ignoring assignment to lcsc” warnings
     * BOM now includes HJ module line item
     * BOM shows correct inductor LCSC ID
     * BOM shows the new translator (C1849454)

6. **Generate an assembly-friendly BOM**

   * Run `python3 scripts/explode_bom.py` (script above)
   * Use exploded BOM + KiCad CPL for PCBWay assembly

Only after all that:
7) Open KiCad PCB, do **mechanical planning** (19mm circle, antenna keepout, mic hole on bottom only, all components top-side), then placement/routing.

---