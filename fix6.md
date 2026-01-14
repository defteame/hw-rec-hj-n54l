According to a document from 2025/10/09, I went through the **atopile sources** (`main.ato`, `adapter.ato`, part definitions), the **generated artifacts** (`build/builds/*/*.bom.csv`, `main.net`), and the **atopile logs** under `build/logs/archive/*`. I also cross‑checked the design against the **HJ‑N54L_SIP hardware design manual**, **nPM1300 datasheet**, **CSNP64GCR01‑BOW datasheet**, and the **T5838 datasheet** .

Below is an exhaustive, opinionated review + a concrete next‑step plan.

---

## 0) What you’re building (architecture sanity check)

**Goal**: ~19 mm circular board, *one-side populated*, bottom side flat with *only* the MEMS mic acoustic hole.

**Current architecture (as implemented in `main.ato`)**:

* **Compute / RF**: HJ‑N54L_SIP (nRF54L15 SiP w/ built‑in antenna)
* **Power**: nPM1300 (charger + power‑path + 2 buck rails)

  * Buck1 set to **1.8 V** (mic + level shifter VCCA)
  * Buck2 set to **3.3 V** (MCU + SD‑NAND + level shifter VCCB + PMIC VDDIO)
* **Storage**: CSNP64GCR01‑BOW “SD‑NAND” (SDIO pins used; SPI mode planned)
* **Audio**: TDK/InvenSense T5838 PDM mic (1.8 V domain, with WAKE/THSEL used)
* **Debug/bring-up**: pogo pads for SWD/UART/I2C/Power + extra pads for SD lines

✅ Overall block diagram is coherent.

---

## 1) Validation: “Did we pick all required components?”

### 1.1 PMIC: nPM1300 external passives look complete (and mostly correct)

**Buck outputs**

* nPM1300 requires **≥4 µF effective output capacitance** and **≤50 mΩ ESR** at each buck output.
* Inductor guidance: **2.2 µH**, **DCR ≤ 400 mΩ**, **Isat > 350 mA**.

Your BOM uses **2× FH CMH160808B2R2MT 2.2 µH** inductors. LCSC lists **DCR 240 mΩ** and **rated current 0.75 A**, which clears the nPM1300 constraints comfortably.

**Buck voltage set straps**

* VSET1 39–68 kΩ → **1.8 V**
* VSET2 250–500 kΩ → **3.3 V**

Your straps **47 k** + **470 k** exactly match those tables.

**VBUS / CC pins**

* CC pins can be left floating if Type‑C detection isn’t used, but **VBUS current limit stays at 100 mA until host config**.
  ⚠️ That is a “works eventually with firmware” situation, not “charges fast out‑of‑box”.

**SHPHLD**

* SHPHLD has internal pull‑up and is used for ship mode; datasheet explicitly describes wake conditions and notes a push‑button-to‑GND is typically required to wake from ship mode when VBUS isn’t present.
  ⚠️ You currently only have a capacitor to GND. That means you can’t conveniently use ship/hibernate features unless you accept “plug VBUS to recover.”

✅ PMIC component set is sufficient electrically.
⚠️ Two system-level issues remain: **VBUS current limit default** and **SHPHLD usability** (more in section 3).

---

### 1.2 HJ‑N54L_SIP module support components & RF are sane

**Supply range**

* Module power range: **1.7 V–3.6 V** → your 3.3 V rail is fine.

**GPIO input thresholds**

* Input high threshold is specified as **VIH ≥ 0.7×VCC**. At 3.3 V, that’s ~2.31 V.
  ✅ This is exactly why your mic’s 1.8 V signals need translation.

**32 kHz pins**

* P1‑00/P1‑01 are internally tied to a 32.768 kHz crystal and **should not be used**.
  ✅ Your design leaves them unused.

**RF / antenna**

* Manual recommends a π matching network and strict keepout (no copper/no devices near antenna, none on back side).
  ✅ You implemented a π network footprint with DNP shunt caps + 0 Ω series link (good for tuning).

✅ Electrically and conceptually correct.
⚠️ The *layout* must respect antenna keepout (not yet done).

---

### 1.3 SD‑NAND: required pullups + caps are present

The CSNP64GCR01‑BOW datasheet explicitly calls for:

* **0.1 µF + 2.2 µF** supply decoupling
* **pull‑ups on CMD and DAT[3:0]**
* **series resistor on CLK** (RCLK 0–120 Ω recommended)

Your design includes:

* 100 nF + 2.2 µF on VCC (matches)
* 10 k pull‑ups on CMD + DAT0–DAT3 (matches)
* 33 Ω series on CLK (inside allowed band)

Also, current draw is modest (write/read tens of mA), so nPM1300 buck current capability isn’t threatened.

✅ Storage hardware looks correct.

---

### 1.4 T5838 mic: power, clock resistor, hole, and “no pull” rule

Key requirements:

* Supply: **1.62–1.98 V**
  ✅ You power from 1.8 V buck.
* Clock: series **33 Ω** recommended in the datasheet’s application circuit
  ✅ You have 33 Ω on PDM clock.
* Data line: datasheet explicitly says **no pull‑up or pull‑down on DATA** and notes the DATA output is high‑Z in sleep
  ✅ You made the bias resistor DNP (good). Keep it that way.
* Bottom port hole: recommended **0.5 mm–1 mm** PCB hole
  ✅ Your footprint uses a 0.5 mm NPTH.

✅ Mic connectivity now matches datasheet guidance.

---

## 2) Validation: “Is atopile schematic / connectivity correct?”

Based on `main.net` + `main.ato`, these are **correct**:

* nPM1300:

  * PVDD tied to VSYS
  * VDDIO tied to the 3.3 rail (datasheet recommends VDDIO = a buck output)
  * VSET straps correct for 1.8/3.3 rails
* HJ module:

  * SWDIO/SWDCLK/NRESET go to debug pads
  * Antenna pins routed through π network footprint
* SD‑NAND:

  * CLK/CMD/DAT0 to MCU pins as SPI
  * DAT1/DAT2/DAT3 pulled up
* Mic:

  * Correct domain crossing using SN74LVC1T45
  * DIR pins set (important: TI warns DIR must not float and device has no OE)

✅ Electrically consistent.

---

## 3) Major problems / risks (very opinionated)

### Critical (must address before ordering PCBs)

1. **The HJ‑N54L_SIP module is missing from the generated BOM**

* Logs show `has_part_picked` missing for `mcu` and many footprint-only items.
* Footprint-only items are fine to omit, but **the MCU module must appear in BOM**.

**Fix**: add part-picking metadata for the module (MPN, manufacturer, supplier/SKU or “DNF / customer supplied”) so it is BOM-visible.

2. **No board outline / no placement**

* The `layouts/main/main.kicad_pcb` file currently has footprints auto-stacked, not placed, and no Edge.Cuts circle.
* Until you place and route, you do not actually satisfy the 19 mm or the antenna keepout requirement.

**Fix**: draw the 19 mm circular outline + component placement + routing + DRC.

---

### High (will bite you during bring-up or power behavior)

3. **VBUS current limit will default to 100 mA**
   With CC pins unused, the datasheet says VBUS current limit remains 100 mA until configured by host. That means:

* slow charging until firmware config
* possible brownouts if you try to run + charge aggressively before configuring

**Decision**:

* If you accept “firmware config required,” keep it.
* If you want robust charging with no firmware, you need CC routing strategy (likely via your adapter board/pogo).

4. **SHPHLD is not exposed**
   nPM1300 ship/hibernate wake behavior expects SHPHLD control options. With only a cap, you’ve effectively decided:

* no user-controlled power latch
* recovery from ship mode relies on VBUS presence (or never entering ship mode)

**Decision**: either explicitly commit to “always-on when battery connected,” or add:

* a tiny button/pad to pull SHPHLD low, and/or
* SHPHLD routed to an MCU GPIO so firmware can manage it.

---

### Medium (layout/manufacturability concerns)

5. **Antenna keepout is non-negotiable**
   The module manual is very explicit: no copper/no devices near antenna and none on the backside.
   Your “bottom side empty” requirement helps, but you must:

* keep copper away on both layers in the antenna zone
* keep inductors/switchers away from that zone

6. **0201 everywhere**
   This is doable with a good assembly house, but for prototypes it increases risk and cost.
   If this is JLC-style assembly: verify their capability for 0201 + SOT‑563 + QFN‑32 + the mic.

---

## 4) “One-side populated / bottom flat except mic hole” requirement

✅ In the current KiCad layout file, all footprints are on the **front copper**; none are assigned to B.Cu.
⚠️ But the layout is not finalized; you must enforce:

* tent all vias on bottom
* no exposed pads/test pads on bottom
* copper keepout around mic hole (your footprint already removes copper/mask at the port)

---

## 5) COMPLETE, opinionated next-step plan (do this in order)

### Phase A — Make the project “orderable”

1. **Fix BOM completeness**

   * Add part metadata for HJ‑N54L_SIP so it appears in BOM.
   * Decide whether pogo pads should be BOM entries (normally: no).
   * Rebuild and confirm logs no longer warn about the MCU.

2. **Lock electrical decisions**

   * Decide if you truly need **THSEL + WAKE**.
     If not, hard-strap THSEL and omit WAKE translation to cut IC count + decouplers.
   * Decide what you want regarding **VBUS current limit**:

     * firmware-configured charging (acceptable), or
     * “works without firmware” (requires CC strategy)
   * Decide SHPHLD philosophy:

     * always-on device, or
     * add button/pad or MCU control for ship/hibernate

3. **Re-run atopile build**

   * Confirm `main.net` still matches expectations
   * Confirm `main.bom.csv` contains all critical purchased parts

---

### Phase B — Layout for a 19 mm circle that actually works

4. **Create the circular board outline**

   * Draw 19 mm diameter on `Edge.Cuts`
   * Place mic hole location intentionally (don’t let it drift)

5. **Component placement strategy (strong recommendation)**

   * Put **mic near center** (acoustics + keep bottom hole clean)
   * Put **HJ module at the edge** with antenna side facing outward; reserve keepout per manual
   * Keep **PMIC + inductors** as far from antenna and mic as routing allows
   * Put **SD‑NAND close to MCU**, short SPI lines, place CLK series resistor close to driver

6. **Power integrity routing**

   * Follow nPM1300 guidance: caps close to supply pins, minimize high-current loops
   * Wide traces for switch node loops (SW1/SW2)
   * Solid ground on bottom layer (except antenna & mic keepouts)

7. **RF layout discipline**

   * Keep RF trace short, controlled impedance as much as possible
   * Place π network right at the RF pins
   * No copper or routing under/near antenna zone

8. **DFM**

   * Add fiducials (at least 3 global top)
   * Panelization strategy (tabs/rails) because a 19 mm circle is annoying to assemble otherwise
   * Decide PCB thickness (0.8–1.0 mm often nicer for bottom-port mic response)

9. **DRC / ERC / constraint review**

   * Run full KiCad DRC
   * Check clearances around mic hole and antenna keepout
   * Ensure no bottom exposed copper except the mic port

---

### Phase C — Bring-up plan (hardware + firmware)

10. **Power bring-up first (no firmware assumptions)**

* Apply VBUS → verify VSYS, VOUT1 (~1.8), VOUT2 (~3.3)
* Confirm buck stability under load
* Verify no overheating around inductors/PMIC

11. **SWD & programming**

* Confirm SWDIO/SWDCLK/NRESET pads are reachable with pogo jig
* Flash minimal firmware that:

  * talks to nPM1300 over I2C
  * raises VBUS current limit if desired
  * sets charger params / disables NTC if you keep NTC shorted

12. **Mic validation**

* Verify PDM clock reaches mic (at 1.8 side)
* Verify PDM data captured at MCU
* Confirm WAKE behavior only if you truly need it

13. **SD‑NAND validation**

* Initialize in SPI mode
* Test sustained writes (audio-rate logging)
* Confirm pullups behave and bus is stable (CLK resistor helps)

14. **RF sanity**

* BLE advertising range test
* If poor: tune π network (populate C shunts if needed)

---

## What I did **not** complete (due to tooling time limit)

* I didn’t finish an automated scan of the netlist for “single-node/dangling” nets (I started writing a parser). Functionally, the important nets (power, SWD, mic, SD) are connected correctly, but a full dangling-net report would add extra confidence.
* I didn’t deeply audit the **adapter board firmware feasibility** (CMSIS-DAP / SWD bit-bang on nRF52840 is plausible, but it’s a project on its own).

If you want, I can produce:

* a strict “dangling nets and unused pins” report from `main.net`
* a layout placement sketch for the 19 mm circle (where each block should go)
* a minimal “rev0 BOM cleanup PR” list for the atopile parts

---

### Bottom line (go/no-go)

**GO electrically**, with two blockers:

1. **Make the HJ module appear in BOM** (and decide how it’s sourced)
2. **Do real placement + board outline + RF keepout** before ordering

After that, the design is genuinely close to a buildable first prototype.

# UPD 1 

Here’s what I would lock electrically **before** you spend time on placement/routing — and the single best “works every time but still fits” solution for **VBUS/CC** and **SHPHLD**.

## 1) THSEL + WAKE

✅ Yes — keep both, and keep them **level‑shifted**.

The T5838’s digital pins are on a **1.8 V domain** and its absolute max for digital input voltage is **limited to ~1.98 V** (not 3.3 V tolerant), so THSEL/WAKE/CLK/DATA must not ever see 3.3 V directly.

Your present approach (SN74LVC1T45 dual‑supply translator per signal) is electrically correct provided the DIR is strapped correctly:

* DIR **LOW** ⇒ B→A
* DIR **HIGH** ⇒ A→B【([Texas Instruments][1])

And your intended directions are exactly:

* CLK, THSEL: MCU → mic (3.3→1.8) ⇒ **B→A** (DIR low)
* DATA, WAKE: mic → MCU (1.8→3.3) ⇒ **A→B** (DIR high)

Also: don’t add pullups/pulldowns on the **PDM DATA** line; the datasheet explicitly warns against it.

That’s enough to confidently move to layout on the mic interface.

---

## 2) VBUS / CC pins on nPM1300

### What the nPM1300 will do if you ignore CC pins

If you **do not use USB‑C detection**, Nordic explicitly says:

* **CC1/CC2 can be left floating or tied to GND**
* but then the **default VBUS current limit stays at 100 mA** until a host negotiates/configures a higher current (same statement also appears in Nordic’s v1.1 PS)【([docs-be.nordicsemi.com][2])

So: leaving CC pins unconnected is electrically allowed — but it’s inherently a **firmware‑configured charging‑speed** situation.

### My decision for your design

**Decision:** **Do not route CC1/CC2 at all on the main 19 mm board. Leave them NC.**

Why this is the best “it will work and it will fit” choice in your architecture:

* Your main board doesn’t have a USB‑C connector; VBUS comes in via pads/adapter.
* If you try to “bring CC through pogo,” you create a *Type‑C termination ownership* problem (because your adapter likely already has Rd resistors; nPM1300 also effectively expects to be the Type‑C sink front-end).
* The clean, robust solution is to treat VBUS as a generic 5 V input and **set the current limit explicitly** via TWI (I²C).

### The exact way to guarantee >100 mA charging (no ambiguity)

The nPM1300 gives you a dedicated **VBUSIN register block**:

* **VBUSIN instance base address**: `0x00000200`
* **TASKUPDATEILIMSW** offset `0x0` (so register `0x0200`)
* **VBUSINILIM0** offset `0x1` (so register `0x0201`)
* **7‑bit I²C address**: `0b1101011` = `0x6B`

**Recommended “safe default fast charge” behavior:**

* Set input current limit to **500 mA** (USB‑friendly) by writing `VBUSINILIM0 = 0x00` (the “500MA0” enum)
* Then apply it by writing `TASKUPDATEILIMSW = 0x01` (“SELVBUSILIM0”)

Also critical detail: **VBUS removal switches back to VBUSINILIMSTARTUP** (so you must re-apply after replug).

That is the “no guessing” solution that doesn’t require CC pins and doesn’t cost PCB area.

---

## 3) SHPHLD

### What SHPHLD is (and why leaving it inaccessible is risky)

SHPHLD is not just “nice to have.” Nordic describes it as:

* a **reset control**
* and also used for **exiting Ship and Hibernate** modes

Key behaviors:

* Internal pull‑up exists (to VBAT or VBUS, whichever is higher)
* In Ship/Hibernate: a logic‑low longer than **tshipToActive** wakes the device and triggers an internal reset
* In normal mode: long low (> tRESETBUT) causes a power cycle (enabled by default unless firmware disables)

### My decision for your design

**Decision:** You should **expose SHPHLD physically** on the main board (top side) via a **pad/testpoint (or pogo pad)** and have a nearby ground reference.

This gives you a guaranteed recovery path if:

* firmware accidentally enters ship mode,
* battery is present but you don’t have VBUS at hand,
* or you need a “hard” physical reset mechanism during bring-up.

You do **not** need any extra resistor/cap network for basic correctness because SHPHLD already has its pull‑up and timing is handled internally/configurably.

To keep your bottom side clean: put the SHPHLD pad on the **top**, and if you want a button, put it on the **adapter**, not the 19 mm board.

---

# The best “will work, still fits” solution summary

**Do this on the main 19 mm board:**

1. ✅ Keep THSEL + WAKE with level shifting (you already must anyway because of the mic pin voltage limits).
2. ✅ Leave **CC1/CC2 unconnected** (NC).
3. ✅ Add **one exposed pad (or pogo pad)** for **SHPHLD** on the **top side**.

**Do this in system/firmware (so charging is never stuck at 100 mA):**
4. ✅ On VBUS present, write:

* `I2C addr 0x6B`
* `reg 0x0201 (VBUSINILIM0) = 0x00` (500 mA)
* `reg 0x0200 (TASKUPDATEILIMSW) = 0x01` (apply limit)

5. ✅ Re-run that whenever VBUS is replugged (because VBUS removal returns to startup limit).

**Do this on the adapter (recommended):**
6. ✅ Add a momentary button (or just a shortable pad pair) from **SHPHLD→GND** so you can wake/reset reliably.

---

# Exact next steps

## A) Schematic / atopile edits you should make now

1. **Main board**: add SHPHLD pad

* Add a new `POGO_PAD` (or test pad footprint) and connect it:

  * `pmic.SHPHLD ~ pad_shphld.p1`

2. **Main board**: explicitly keep CC pins NC

* No routing, no pads. (Optional: add a schematic note “CC pins intentionally NC; firmware sets VBUS limit”.)

3. **Adapter** (strongly recommended): bring SHPHLD to something you can actuate

* Add a pogo that mates to `pad_shphld`
* Add either:

  * a tactile switch to GND, or
  * two exposed pads you can short (simpler / zero BOM risk)

## B) Verification gates before you start placement

4. Confirm these are true in your netlist/schematic:

* Mic: THSEL/WAKE/CLK/DATA are all on translators and no pin sees 3.3 directly.
* No pull‑ups/downs on mic PDM DATA line.
* SHPHLD is reachable by a probe/pogo/button (not buried).
* CC1/CC2 are intentionally left unconnected and won’t create DRC “ratsnest” expectations.

## C) Firmware bring-up steps you can implement immediately

5. Implement a tiny “PMIC init on VBUS” routine (either on the main MCU firmware or adapter firmware; ideally both):

* Detect VBUS present (poll `VBUSINSTATUS` at `0x0207` if desired)
* Write:

  * `0x0201 = 0x00` (500 mA)
  * `0x0200 = 0x01` (apply)
* Log/LED confirm so you know it happened.

This single routine removes the “stuck at 100 mA” risk without consuming PCB area.

## D) Then move to placement/layout

6. Only after A–C are locked, start placement with these non-negotiables:

* Keep mic port keepout/cutout clean (no vias/copper in the acoustic hole area).
* Place nPM1300 + its inductor/caps in a tight power loop region (short SW loops, solid ground).
* Keep the radio module antenna area clear per its hardware guide (edge placement + keepout).
