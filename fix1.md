Here’s an exhaustive, engineering‑style audit of what’s in your Atopile project (main.ato + adapter.ato + picked parts + build artifacts/logs), with the specific goal you stated: **~19 mm round board using HJ‑N54L_SIP (nRF54L15 module) + SD‑NAND + TDK/InvenSense T5838 PDM mic**, and a clear, opinionated set of next steps.

I’m going to treat this as a “bring‑up ready?” review: what’s correct, what’s missing, what’s risky, and what I would change before you spin Rev‑A.

---

## What’s in the project, and what Atopile successfully produced

### Projects / builds

Your repo defines two top‑level Atopile components:

* **`main`**: the tiny “target” board with nRF54 module + PMIC + NAND + mic + pogo pads.
* **`adapter`**: a USB‑C powered board with an nRF52840 module, intended to talk to the target via pogo pads (or to act as an interface/programmer).

Atopile builds completed successfully (no fatal schematic/netlist errors). The important build artifacts are present:

* `build/builds/main/main.bom.csv`
* `build/builds/adapter/adapter.bom.csv`
* `build/builds/main/main/main.net` (KiCad netlist)
* KiCad PCB files in `layouts/main/main.kicad_pcb` and `layouts/adapter/adapter.kicad_pcb`
* Logs under `build/logs/archive/...`

### What Atopile picked vs what it did not pick

From the **picker logs**, Atopile did *not* pick parts for:

* HJ‑N54L_SIP module (consigned / no picker)
* Pogo pads & battery pads (intentionally no LCSC part)
* Your DNP antenna shunt caps (intentionally no picker)

This is expected — but it has a downstream consequence: **these items do not appear in the CSV BOM** and will not be ordered/assembled unless you manage them separately.

---

## Main board schematic audit

### 1) MCU module (HJ‑N54L_SIP)

**What you did:**

* Powered the module from the PMIC’s 3.3 V buck (V3V3/VCCB).
* Tied all module grounds to GND.
* Left P1.00 / P1.01 unconnected (correct).

**Why that’s correct:**

* The module documentation calls out that **P1‑00 and P1‑01 are used by the internal 32.768 kHz oscillator and should not be connected**.
* The module supply range is **1.7 V to 3.6 V** and 3.3 V is normal.

**RF path / antenna network**
You implemented a standard “bring‑up friendly” PI network:

* RF pin → **0 Ω series** → BOARD_ANT pin
* Two **DNP shunt caps** from each side to GND

This matches the guidance that RF and ANT pins should be connected directly, and adding a PI network is recommended for best effect/tuning.

✅ **Electrical design: good.**
⚠️ **Layout will make or break RF** (keepout, ground, placement; more below).

---

### 2) SD‑NAND (CSNP64GCR01‑BOW) on SPI‑mode SD interface

**What you did in `main.ato`:**

* Powered NAND from **3.3 V**.
* Added **2.2 µF + 0.1 µF** local decoupling at NAND VCC.
* Added **10 k pull‑ups** on CMD and DAT0/1/2/3.
* Added **33 Ω series resistor** on CLK.

**Cross‑check vs datasheet recommendations**
The SD‑NAND datasheet’s reference design calls out exactly these concepts:

* **2.2 µF** on VCC
* **pull‑ups on CMD and DATx**
* **series resistor on CLK** (0–120 Ω suggested)

So your discrete support network is aligned.

✅ **Electrically: very reasonable.**

#### Big red flag: NAND footprint / pad mismatch risk

When I inspected your KiCad footprint file for the NAND (`LGA-8_L8.5-W7.0-P1.27-TL.kicad_mod`), it contains an **extra pad “9”** that is **not represented in the symbol pin list** (your symbol is 1–8 only). In the netlist, that pad would end up **unconnected**.

Meanwhile, the datasheet pin assignment table lists only 8 pins (DAT2, DAT3, CMD, VSS, CLK, VCC, DAT0, DAT1).

This mismatch is exactly the kind of thing that can silently ruin Rev‑A.

**My opinionated recommendation:**

* Treat NAND footprint as **not yet trusted**.
* Before layout, confirm the package’s land pattern and whether the “extra” pad is:

  * real and must be soldered (and to what net), or
  * just an artifact that should be removed from the footprint.

If you get this wrong, you can end up with:

* assembly defects (tombstoning, skew),
* shorts (if the mystery pad overlaps paste),
* or poor reliability.

---

### 3) PDM microphone (T5838) and level shifting

**What you did:**

* Powered mic from **1.8 V buck**.
* Added **0.1 µF** local decoupling at mic VDD.
* Tied mode pins SELECT and THSEL to **GND**.
* Level shifting:

  * Clock: 3.3 V MCU → 1.8 V mic via SN74LVC1T45 (DIR low).
  * Data: 1.8 V mic → 3.3 V MCU via SN74LVC1T45 (DIR high).

**Supply sanity**
T5838 abs‑max VDD is **1.98 V** (tight!).
So feeding it from **nPM1300 BUCK1 @ 1.8 V** is correct. (nPM1300 buck accuracy is ±5% so 1.8 V stays safely below 1.98 V in normal conditions.)

✅ Supply choice good.

**Clock line overshoot / termination**
T5838 documentation explicitly recommends **source termination on the clock line** to reduce overshoot/ringing.
Given the mic’s abs‑max is only 1.98 V, even a modest overshoot can start to look scary.

⚠️ Your current design has **no series resistor on PDM_CLK**.
**I would add a footprint for 22–47 Ω** in series with PDM_CLK (DNP allowed).

**Data line tri‑state vs level shifter risk**
T5838 notes the **PDM data line is tri‑stated** during part of the clocking, and specifically warns not to add pull‑ups/pull‑downs that would force the state during tri‑state.

Now cross‑check with the TI SN74LVC1T45 datasheet: it says the input circuitry is always active and **inputs must have a defined HIGH or LOW to prevent excess ICC/ICCZ**.
And direction control is as you used it (DIR high = A→B; DIR low = B→A).

This creates a real design tension:

* The mic *intentionally* tri‑states (so the node can float / hold charge).
* The level shifter *prefers* a defined logic state.

This doesn’t necessarily mean it won’t work — the line may “hold” its last state due to capacitance and minimal leakage — but it is absolutely a **bring‑up risk** and could show up as:

* increased current draw in the level shifter,
* glitches on PDM_DATA in the “off” half cycles,
* unreliable audio capture at higher PDM clock rates.

**My opinionated recommendation:**

* Keep the translator approach (it’s still the most practical way to protect the mic from 3.3 V clock).
* Add an **optional very‑weak bias footprint** on the mic‑side (1.8 V domain) PDM data node (e.g., 1 MΩ to GND) **DNP by default**.

  * If you see power/current or data stability issues, you can populate it.
  * Keep it weak enough to not fight the mic during driven periods.

Also: the T5838 datasheet says buffering the data line is only needed for long wiring or heavy loads, and only safe when one mic is used (or after the stereo split).
Since you have **one mic**, a buffer/translator is acceptable — but validate with scope.

---

### 4) Power: nPM1300 implementation review

You used nPM1300 as:

* charger / power path,
* BUCK1 = 1.8 V,
* BUCK2 = 3.3 V,
* I2C control (SCL/SDA with pull‑ups),
* VBAT pads and VBUS pogo.

#### VSET resistor values: correct

Your VSET resistors:

* VSET1 = **47 kΩ** → VOUT1 = **1.8 V**
* VSET2 = **470 kΩ** → VOUT2 = **3.3 V**

This matches the nPM1300 voltage selection table.

✅ Good.

#### Inductors: the chosen parts are far beyond requirements (good)

nPM1300 recommends for buck inductors:

* 2.2 µH
* DCR ≤ 400 mΩ
* Isat > 350 mA, etc.

You picked **Sunlord MWSA0603S‑2R2MT** (LCSC C390408). That part is massively oversized (low DCR, very high current rating): datasheet shows DCR ~15 mΩ and Irms ~9.5 A (depending on variant).

✅ Electrically safe (if anything, overkill).
⚠️ Practically: check the **actual physical size** and whether this “0603 series” naming is misleading — many molded power inductors are not actually 0603 footprint‑class even if the name suggests it. Confirm footprint matches the real part.

#### CC1/CC2 left floating: acceptable, but has a consequence

You left CC1/CC2 floating (you even note it in comments). The nPM1300 spec says if type‑C current detection isn’t used and CC pins are left floating (or tied to GND), **VBUS current limit remains 100 mA until the host configures it**.

This is critical system behavior:

* If the main board is powered only from VBUS via pogo and tries to run RF + NAND writes + mic, you might bump into the 100 mA limit.
* Charging will also be constrained.

You can still make this work by:

* keeping boot current low,
* then raising limits/configuring through I2C in firmware once running.

✅ Not “wrong.”
⚠️ But you need to plan firmware around it.

#### NTC pin tied to ground: okay, but firmware must disable it

Your hardware ties NTC to GND through 0 Ω, and the spec says that’s acceptable **if you disable the NTC functionality in the appropriate register**.

✅ Hardware okay.
⚠️ Firmware requirement: disable NTC early or charging may not behave as expected.

#### High‑severity schematic issue: VBUSOUT tied to VSYS

In `main.ato` you did:

* `pmic.VBUSOUT ~ VSYS`
* `pmic.VSYS ~ VSYS`

So VBUSOUT and VSYS are shorted together.

This is almost certainly **incorrect**. The nPM1300 product spec states plainly:

* **“VBUSOUT is only for host sensing and should not be used as a source.”**
* It also describes modes where **VBUS is disconnected from VSYS but VBUSOUT remains active** (USB suspend behavior).

If you tie VBUSOUT to VSYS, you can unintentionally:

* defeat VBUS disconnect/suspend behavior,
* create weird back‑powering paths,
* violate intended current limits.

**This is the #1 schematic change I would make before layout.**

✅ Fix: **remove `pmic.VBUSOUT ~ VSYS`**.
Decide one of:

* Leave VBUSOUT unconnected (likely fine if you don’t need host sensing), or
* Route it to a test pad (and add the recommended decoupling if used).

---

### 5) Debug / pogo interface

On main board you currently expose:

* SWDIO
* SWDCLK
* NRESET
* VBUS
* GND
* VBAT+ / VBAT− pads
* a “3V3 sense” pogo pad (good as Vref)

That is enough for SWD programming *if* you have a real SWD probe and a stable power scheme.

However, your **high-level-plan.md** suggests the pogo interface should also include I2C and more signals — your current `main.ato` does not implement that interface. So either:

* the requirements doc is outdated, or
* your current schematic is missing intended pogo pins.

---

## Adapter board audit

### Electrically: mostly sane, but incomplete as a practical tool

Your adapter board includes:

* USB‑C receptacle + CC pull‑downs (sink)
* USB ESD protection (USBLC6)
* 3.3 V LDO
* an nRF52840 module (E73‑2G4M08S1C)

That can be a useful “smart adapter” if you plan to load firmware that:

* enumerates over USB,
* talks to the target over I2C/UART,
* maybe even implements CMSIS‑DAP or a custom SWD bridge.

But here are two very practical issues:

1. **No way to program/debug the adapter itself**
   I see no SWD header / Tag‑Connect / test pads in the design to program the nRF52840 module initially.

2. **Unclear SWD strategy**
   Even if the adapter is meant to program the nRF54 target, that requires:

* firmware on the nRF52840 that can drive SWD to the target, and
* a defined mechanism to power the target and set IO levels.

If your real plan is “adapter is just a pogo breakout and the real debugger is a J‑Link,” then you should add a standard SWD header and route pogo pins to it.

**My opinion: for Rev‑A, simplify**:

* Either (A) make adapter a dumb pogo breakout + USB power only (and add a Tag‑Connect for the target’s SWD), or
* (B) keep the nRF52840, but add **a proper SWD programming connector** and a very explicit power strategy.

---

## Layout readiness vs your stated goal (19 mm circle)

### Current KiCad layout files are not a real layout yet

The generated `layouts/main/main.kicad_pcb` and `layouts/adapter/adapter.kicad_pcb` are essentially:

* footprints placed in a simple spread/grid,
* **no board outline**, and
* **no routing**.

So: schematic/netlist is the meaningful part right now; PCB is a starting canvas, not a finished design.

### Mismatch with your stated mechanical target

From the KiCad board file settings:

* It’s configured as **2‑layer** and **1.6 mm thickness** (KiCad default),
* while your requirements say **4‑layer ~0.4 mm** and “top side only”.

You’ll need to explicitly change:

* layer stack (add inner planes),
* board thickness,
* board outline (19 mm circle),
* placement and routing.

### RF + power + mic on 19 mm is feasible, but only with disciplined placement

You can absolutely pack this into 19 mm, but you must commit to:

* module at the edge, antenna keepout respected,
* PMIC + inductors kept away from antenna and with tight current loops,
* mic hole + keepout and a clean ground reference,
* SD‑NAND close to MCU pins.

---

## Component selection audit from BOMs

### Main BOM completeness (as “what gets assembled”)

The main BOM includes:

* nPM1300 (U5)
* SD‑NAND (U4)
* T5838 mic (MK1)
* 2× SN74LVC1T45 level shifters (U1/U2)
* inductors and all passives

What it **does not include**:

* HJ‑N54L_SIP module
* pogo pads
* battery pads
* DNP antenna caps

That’s fine **only if you consciously manage consigned/DNP items** (in ordering docs and assembly notes).

### Parts sanity highlights

* Inductor choice: electrically excellent, but confirm physical footprint matches part.
* SN74LVC1T45 choice: functionally matches your translation needs, but watch floating input current behavior.
* T5838 mic: footprint includes through‑hole sound port; datasheet recommends 0.5–1 mm PCB sound hole which your footprint seems aligned with.
* nRF54L15 capabilities: Nordic’s product page lists PDM and multiple SPI/TWI/UART instances, which aligns with your use of SPI for SD‑NAND and PDM for mic.

---

## Summary of what is correct vs what must change

### Green (looks correct / complete for basic functionality)

* Power architecture (VBUS/VBAT → nPM1300 → 1.8 + 3.3 rails) **conceptually solid**
* VSET resistor choices for 1.8 and 3.3 **correct**
* SD‑NAND support network (decoupling, pullups, CLK series R) **matches reference guidance**
* RF PI network approach **matches module guidance**
* Mic powered at 1.8 V **correct vs abs‑max**

### Yellow (likely workable, but bring‑up risks)

* PDM level shifting with SN74LVC1T45:

  * direction is fine, but tri‑state input behavior and potential current draw needs validation.
* No PDM clock series resistor (recommended by mic vendor).
* CC pins left floating → 100 mA limit until configured.
* NTC grounded but requires firmware disable.

### Red (I would not spin a PCB without fixing)

1. **VBUSOUT tied to VSYS** on nPM1300.
   This conflicts with “VBUSOUT is only for host sensing and should not be used as a source.”

2. **SD‑NAND footprint/pinout mismatch risk** (extra pad in footprint vs symbol/pin table).
   Needs explicit confirmation or correction.

3. **There is no PCB layout yet** for a 19 mm circle:

   * no board outline,
   * no routing,
   * wrong default thickness/layers.

---

## Opinionated next‑steps plan

I’m going to give you a concrete “Rev‑A” plan that gets you to a manufacturable prototype with the highest chance of first‑power success.

### Step 1 — Fix schematic/Atopile now (before layout)

**1. Remove VBUSOUT↔VSYS short**

* Delete: `pmic.VBUSOUT ~ VSYS`
* Decide:

  * Leave VBUSOUT NC (simplest), or
  * Route to a test pad (if you want VBUS presence sensing for debug).

**2. Add optional PDM clock series resistor footprint**

* Add R in series with `PDM_CLK` (somewhere close to the driver, ideally on the 1.8 V side near the mic).
* Default value: 22–47 Ω (DNP allowed).
  This follows the mic vendor guidance on clock termination.

**3. Add an optional weak bias footprint on PDM data (DNP)**

* Because mic data tri‑states and the TI shifter warns about floating CMOS inputs, add a DNP footprint for 1 MΩ (or similar) bias.
* Keep it DNP unless you see problems on the bench.

**4. Decide your CC strategy**
Right now, CC floating means 100 mA VBUS limit until configured.

Pick one:

* **Firmware approach (recommended for simplicity):** keep CC floating, but in your boot firmware:

  * disable NTC,
  * configure charger/current limit/ship mode behavior ASAP.
* **Hardware approach:** bring CC1/CC2 onto pogo and connect to the Type‑C CC pins on the adapter board, so nPM1300 can do current detection in hardware.

**5. Resolve NAND footprint correctness**

* Confirm the correct land pattern for CSNP64GCR01‑BOW:

  * does it have an extra pad?
  * is it NC or GND?
  * where exactly is it located?
* Fix symbol ↔ footprint mapping accordingly.

This is a “stop‑ship” item.

---

### Step 2 — Make the adapter board actually usable

You need to decide what the adapter is.

**Option A (strongly recommended for Rev‑A): “dumb pogo + power + SWD header”**

* Keep USB‑C and power path.
* Add a Tag‑Connect or 2×5 1.27 mm SWD header that connects to:

  * POGO_SWDIO
  * POGO_SWDCLK
  * POGO_RESET
  * POGO_GND
  * POGO_VREF (sense from target, don’t drive it unless you mean to power the target)

This lets you use a real J‑Link immediately.

**Option B: “smart adapter using nRF52840”**

* Add an SWD programming connector for the nRF52840 module itself.
* Plan/commit to firmware (CMSIS‑DAP or custom SWD bridge).
  This is a much bigger software investment.

---

### Step 3 — Do the actual 19 mm PCB layout (this is where most projects fail)

**1. Set up the board definition**

* Define a **19 mm diameter circle** in Edge.Cuts.
* Set the correct layer stack:

  * If you truly want 0.4 mm, use 4‑layer with a stack your fab can build.
  * If your fab can’t do 0.4 mm 4‑layer reliably, pick 0.6–0.8 mm for Rev‑A.

**2. Placement strategy**

* Place HJ module near the board edge with its antenna side facing outward.
* Keep PMIC + inductors as far as practical from the antenna.
* Put SD‑NAND close to the MCU pins (short CLK).
* Place mic so the port hole has:

  * clear path through board,
  * no soldermask blockage,
  * keepout for adhesives/tape on the back.

**3. Power layout discipline**

* For nPM1300:

  * inductors tight to pins,
  * minimize SW node loop area,
  * solid ground under PMIC,
  * lots of vias from exposed pad to ground plane.

**4. RF discipline**

* Implement the module manual’s “no components/traces behind antenna” guidance.
* Keep matching network tight to the RF pins.
* Stitch ground via fence around RF region.

**5. Manufacturing discipline**

* 0201 everywhere is doable but increases risk.
  If you want Rev‑A success, consider moving non‑critical passives to 0402 where possible.

---

### Step 4 — Bring‑up test plan (so you don’t “guess” on the bench)

**Power bring‑up**

1. Power from VBUS (no battery). Confirm:

   * VSYS behavior
   * VOUT2 ≈ 3.3 V
   * VOUT1 ≈ 1.8 V
2. Confirm no excessive current draw at idle.
3. Confirm I2C works to nPM1300.

**Firmware early init checklist**

* Disable NTC monitoring (because NTC tied low).
* Configure VBUS current limit/charging parameters if CC floating.

**SD‑NAND**

* Confirm card init in SPI mode.
* Test at low SPI speed first, then scale up.
* Probe CLK for ringing; adjust series resistor if needed.

**Mic**

* Start with lower PDM clock rate.
* Scope the mic CLK at the mic pin for overshoot (series resistor helps).
* Verify PDM data integrity; if weird, try populating the weak bias DNP resistor.

**RF**

* Just do a basic RSSI / link test first.
* If range is bad, populate/tune PI network parts.

---

## Key reference docs used

* HJ‑N54L_SIP Hardware Design Manual: 
* nPM1300 Product Spec: 
* T5838 datasheet: 
* CSNP64GCR01 SD‑NAND datasheet: 

---

## The 3 things I would do *immediately* (highest ROI)

1. **Remove VBUSOUT ↔ VSYS** (real functional correctness issue).
2. **Resolve SD‑NAND footprint/pad mapping** (high risk of dead board).
3. **Add PDM clock series R footprint + optional weak data bias footprint** (cheap insurance).

If you want, I can also produce a concrete **Rev‑A netlist‑level change list** (exact Atopile code diffs) for the above items, but the above is the “final plan” I would execute without further clarification.
