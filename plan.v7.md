Below is a deep review of what’s **actually in the repo right now** (the current `main.ato` / `adapter.ato`, the `build/builds/**.bom.csv`, and the archived logs), cross‑checked against the **HJ‑N54L_SIP hardware manual**, **nPM1300 product specification**, **T5838 datasheet**, and **MKDV64GCL SD‑NAND datasheet / LCSC listing**.

I’m going to be blunt: **as‑is, the “main” board schematic is not buildable into a working recorder** (multiple hard blockers in the PMIC/power tree + at least one footprint mismatch that will likely make assembly fail). The good news is the overall architecture is reasonable, and the fixes are clear.

---

## What the Atopile build artifacts say you currently have

### Main board BOM (`build/builds/main/main.bom.csv`)

Populated parts (JLC/LCSC-picked) include:

* **PMIC:** nPM1300 (U6, LCSC C7501206)
* **Storage:** MKDV64GCL-STP SD NAND (U1, LCSC C7500180)
* **Mic:** TDK/InvenSense T5838 (U4, LCSC C7230692)
* **2× level shifters:** SN74LVC1T45 (U2/U3, LCSC C2677455)
* **2× inductors:** 2.2 µH (L1/L2)
* **Caps:** 10 µF ×4, 100 nF ×12
* **Resistors:** 33 Ω ×1, 10 kΩ ×5 (for SD pull-ups)

Missing from the BOM (because Atopile can’t pick them):

* **HJ-N54L_SIP module itself** (your MCU module)
* **Battery pads**
* **Pogo pads / test pads**

This is confirmed in the **picker warning**: it explicitly says there are “No pickers” for the HJ module and pad footprints (so they won’t appear as sourced parts). That’s normal, but it means you need a deliberate “consigned / DNP / manual assembly” plan.

### Main build logs (`build/logs/archive/.../main/picker.info.log`)

The key thing: **Atopile did not flag electrical correctness issues** (because it largely doesn’t know device-specific “pin must not float” rules). It only flagged missing pickers for pads/module.

So you must rely on datasheet-driven review for correctness (below).

---

## Requirement coverage check (vs your own `requirements.md`)

You want: HJ‑N54L_SIP + SD NAND + T5838 mic + nPM1300 power + RGB LED + antenna pi pads + 19 mm round PCB.

### What you DO have (conceptually)

* HJ‑N54L_SIP module instantiation and nets
* SD NAND wired in 1‑bit SD mode with required pull-ups and CLK series resistor (values look fine)
* T5838 mic connected through level shifting (good architectural choice because T5838 is ~1.8 V class)
* nPM1300 included with two buck converters and charger (correct PMIC class)

### What you do NOT have (missing vs requirements)

* **RGB LED subsystem** is not present in `main.ato` at all.
* **Antenna pi network footprints** are not present; you directly short RF→BOARD_ANT.

  * The HJ manual says direct connect works, but **also explicitly recommends a PI matching network footprint** between pin 23 (RF) and pin 24 (BOARD_ANT).
* **Board outline / 19 mm circular constraint** is not represented in the KiCad outputs (your generated `*.kicad_pcb` in `build/builds/**` is essentially empty), so there is no mechanical validation happening yet.

---

## Main board schematic review (`main.ato`) — hard blockers and fixes

### 1) nPM1300 power tree is wired in a way that will almost certainly NOT boot the board

#### 1A — You tie **VSYS** and **PVDD** to **VBAT**

In your `main.ato`:

* `pmic.VBAT ~ VBAT` ✅ good
* `pmic.VSYS ~ VBAT` ❌ likely wrong / defeats power-path behavior
* `pmic.PVDD ~ VBAT` ❌ likely wrong (PVDD is buck input; typically fed from VSYS)

nPM1300’s own guidance says: **don’t supply the application directly from VBAT**; use VOUT1/VOUT2 or VSYS instead.
And its pin table clearly distinguishes **VBAT** (battery input) from **VSYS** (system voltage output) and **PVDD** (buck input).

**Practical consequence of your current wiring:**
You’re effectively bypassing the PMIC’s intended power-path topology, and you also make ship/hibernate/power-cycle behaviors unreliable (because VSYS is no longer something the PMIC can truly manage).

**Fix (recommended):**

* Make a dedicated net `VSYS`.
* Connect:

  * `pmic.VSYS ~ VSYS`
  * `pmic.PVDD ~ VSYS` (or a net-tie footprint if you want to mirror Nordic’s reference schematic style)
  * `pmic.VBAT ~ VBAT` only to the battery pad

This gives you proper “run while charging” behavior and lets the PMIC manage the system rail as designed.

#### 1B — You mapped the buck outputs backwards for your target voltages

You currently do:

* Buck1: `SW1/VOUT1` → **V3V3**
* Buck2: `SW2/VOUT2` → **V1V8**

But nPM1300’s resistor strap tables show:

* **VOUT1** strap range tops out at **2.7 V** (250–500 kΩ → 2.7 V).
* **VOUT2** strap range can reach **3.3 V** (250–500 kΩ → 3.3 V).

So if you want a guaranteed “~3 V / 3.3 V” rail at boot, it wants to be **VOUT2**, not VOUT1.

**Fix (strongly recommended):**

* Use:

  * **VOUT1 → 1.8 V rail**
  * **VOUT2 → 3.0 V or 3.3 V rail**

This also aligns with Nordic’s own “Configuration 1” reference design example (VOUT1=1.8, VOUT2=3.0).

#### 1C — You do not connect VSET1/VSET2 at all (currently floating)

This is a real “won’t boot / undefined behavior” class issue.

The nPM1300 spec is explicit:

* **“Do not leave VSET[n] floating.”**
* VSET straps also gate buck enable at power-on; e.g., BUCK1 will be enabled at power-on if VSET1 has a resistor, and disabled if VSET1 is grounded.

**Fix: add the two strap resistors:**

* `VSET1 → GND`: pick value for your BUCK1 voltage (e.g., 47 kΩ for 1.8 V in Nordic’s reference config).
* `VSET2 → GND`: pick value for BUCK2 voltage (e.g., 150 kΩ for 3.0 V in Nordic’s reference config; 250–500 kΩ range for 3.3 V).

If you’re trying to maximize usable battery range on LiPo, I’d be opinionated and choose **3.0 V** rather than 3.3 V:

* SD NAND is fine at 3.0 V (it needs 2.7–3.6 V).
* 3.0 V lets you run deeper into battery discharge before the rail droops.

#### 1D — NTC is floating (charger behavior will be wrong unless you intentionally disable it)

Your schematic leaves `pmic.NTC` unconnected.

nPM1300 documentation is explicit:

* If no thermistor is used, **NTC must be tied to ground (directly or through a resistor)** and the functionality must be disabled via register `BCHGDISABLESET`.

**Fix (practical):**

* Put a footprint that lets you choose:

  * (A) a thermistor to GND, or
  * (B) a 0 Ω / resistor to GND for “no thermistor”
* Document in firmware bring-up: disable NTC function if you chose option (B).

#### 1E — VDDIO decoupling is underspecified and I2C pull-ups are missing

You have `pmic.VDDIO ~ V3V3` and only a **100 nF** decoupler.

Nordic’s reference schematic uses **a 1.0 µF capacitor** on VDDIO and also shows optional **TWI pull-ups** on SDA/SCL.

Also: you currently have **no external pull-ups** on SDA/SCL at all. Yes, MCUs can enable internal pull-ups, but on a board like this (with a PMIC that also controls charging and rails) you really want deterministic I2C behavior.

**Fix:**

* Add **1 µF** on VDDIO (keep the 100 nF too).
* Add 2× pull-ups (start with 4.7 kΩ to VDDIO).

#### 1F — CC pins: OK to leave, but be aware of the default current limit

You’re not using USB‑C on the main board directly, so leaving CC unconnected is fine.

But the spec notes: if Type‑C config isn’t used, CC1/CC2 can float or be grounded, **and the default VBUS current limit stays at 100 mA** until configured higher.

So your firmware must raise input current limit, otherwise charging at 200–400 mA won’t happen.

**Fix:**

* Ensure early boot code sets VBUS input current limit and charge current.

#### 1G — SHPHLD tied to V3V3 is a bad idea

You do: `pmic.SHPHLD ~ V3V3`.

But SHPHLD already has an internal pull-up to VBAT/VBUS whichever is higher.
Tying it to a buck output risks backfeeding or messing with ship-mode/power-cycle semantics.

**Fix:**

* Leave SHPHLD unconnected **or**
* Route it to a GPIO / button / test pad (so you can intentionally enter/exit ship mode)

---

### 2) T5838 microphone wiring: mostly good, but WAKE is wrong

#### 2A — Supply / level shifting choice is correct

T5838 operates around 1.8 V (datasheet shows 1.62–1.98 V).
So generating a 1.8 V rail and level shifting to a ~3 V rail is sensible.

Also, the datasheet notes not to use pull-ups/pull-downs on the PDM DATA line because it can pull the signal during the tri-state period.
You didn’t add any pull resistors there ✅.

#### 2B — WAKE pin is an output; you must not tie it to VDD

You currently do: `mic.WAKE ~ V1V8` (hard tie).

But the T5838 pin table states:

* **WAKE is a “Wake Output Pin”**
* If you’re not using AAD/WAKE, it **can be tied to GND or left NC**

So tying WAKE to VDD is electrically wrong (best case: WAKE function is destroyed; worst case: you create a short when the pin drives low).

**Fix:**

* If you don’t need WAKE: connect to **GND** or **leave NC** (per datasheet).
* If you do need WAKE: route to an MCU GPIO **through level shifting** (because 1.8 V “high” won’t meet a ~3 V MCU input-high threshold in many designs).

#### 2C — Acoustic port / hole looks compatible

The datasheet recommends an acoustic port hole roughly **0.5–1.0 mm** diameter and says board thickness does not affect performance.
Your footprint uses a 0.8 mm NPTH, which is in the recommended range ✅.

---

### 3) SD NAND wiring: resistor values are OK, but decoupling + footprint are serious issues

#### 3A — Pull-ups and CLK series resistor values match the datasheet guidance

The SD NAND reference guidance says pull-ups on CMD/DAT lines are typically **10 kΩ–100 kΩ**, and CLK series resistance is **0–120 Ω** (depending on the platform).
You used **10 kΩ** pull-ups and **33 Ω** on CLK ✅.

#### 3B — You should add a local bulk capacitor near the NAND

The same reference guidance calls out **2.2 µF on VDD** for the SD NAND device.
Right now you only have a 100 nF at NAND VDD plus whatever bulk is on the rail elsewhere.

**Fix:**

* Add a **2.2 µF (or 4.7 µF)** very close to the NAND VDD pin(s).

#### 3C — The chosen SD NAND part/package vs your footprint looks mismatched (HIGH RISK)

This is the other major “you’ll lose boards” blocker.

* LCSC lists C7500180 as **LGA‑8 (6.6×8 mm)** and “Standard only” assembly.
* The datasheet also states **LGA‑8 6.6×8.0 mm** package size.

But your footprint in the repo is named:

* `WSON-8_L8.0-W6.0-...-EP...`
  …and it clearly includes a **center exposed pad (pad 9)** and a **6.0 mm body width**.

That does not match “LGA‑8 6.6×8.0 mm”, and suggests you’re using a WSON-with-EP land pattern for an LGA part.

**Fix (mandatory before fab):**

* Replace the footprint with the **manufacturer-recommended LGA-8 land pattern** for MKDV64GCL-STP (or use the verified footprint from LCSC/EasyEDA for that exact LCSC ID).
* Re-verify pin-1 orientation against the datasheet’s pin assignment.

#### 3D — Buck current capacity is adequate for NAND load

Typical SD NAND operating current in the datasheet is on the order of **~30 mA** for write/read.
nPM1300 bucks are 200 mA class devices (also reflected in Nordic’s product brief).
So the power budget is fine.

---

### 4) HJ‑N54L_SIP module: RF and IO-level implications

#### 4A — RF pin connection: functional, but missing the recommended matching footprint

You currently do: `mcu.BOARD_ANT ~ mcu.RF` (direct short).

The HJ manual says:

* You can simply connect RF (pin 23) to BOARD_ANT (pin 24) for the onboard antenna, **but** recommends a PI network footprint for tuning/matching.

**Fix (strongly recommended):**

* Add a PI footprint: shunt C – series 0 Ω – shunt C between RF and BOARD_ANT, and DNP the caps by default.

#### 4B — Respect the antenna keep-out

The manual explicitly calls for a keep-out region for the antenna area.
Your Atopile project currently has no board outline/keepouts in the generated outputs, so this is not enforced anywhere yet.

#### 4C — IO thresholds reinforce why you need level shifting

The HJ manual’s logic levels show **VIH(min) ~ 0.7×VCC** for digital inputs.
So a 1.8 V WAKE output cannot be read directly by a ~3 V supplied MCU pin as a “high” reliably; that supports the earlier recommendation (either don’t use WAKE, or level shift it).

---

## Adapter board (`adapter.ato`) review — key problems

### 1) USB-C DP1/DN1 must be tied to DP2/DN2 for reversibility

Your USB-C connector symbol has `DP1/DN1` and `DP2/DN2`, but you only connect DP1/DN1.

For USB‑C receptacles, you must connect:

* **A6 and B6 together (D+)**
* **A7 and B7 together (D-)**

A clear reference statement (example article, but technically correct): the two D+ pins must connect together, and the two D- pins must connect together for the cable flip to work.

**Fix (mandatory for reliable USB):**

* `usb_conn.DP1 ~ usb_conn.DP2 ~ mcu.D_plus`
* `usb_conn.DN1 ~ usb_conn.DN2 ~ mcu.D_minus`

### 2) The adapter currently defines recorder interface nets but doesn’t *implement* the physical pogo connector

You have the right logical nets (`recorder_vbus`, `recorder_swdio`, etc.), but there are no pogo-pin footprints or a connector footprint placed/defined in the Atopile design. So today it’s not a mateable dock—just a USB dongle schematic.

**Fix:**

* Add the pogo-pin footprint(s) or mating connector and wire them to those signals.

### 3) Consider whether the E73 module needs VBUS sense

The E73 module exposes `VBS`. You currently don’t connect it. Depending on how its USB reference is implemented, you may need to connect VBUS sense to allow USB attach detection / internal regulator decisions. (This needs checking against the module’s own hardware reference; it’s not in the repo docs I was given, so I’m flagging as a likely follow-up item rather than asserting it as fact.)

---

## Big picture: “Will this work if we build it right now?”

No.

Even ignoring missing LED / missing RF PI pads / missing mechanical layout, the **main board has multiple power-tree blockers**:

* VSET pins floating (explicitly disallowed)
* Buck output mapping is incompatible with “3.3 V at boot” expectation
* VSYS/PVDD wired to VBAT undermines the intended PMIC topology
* NTC floating (requires tie+disable if not used)
* Mic WAKE tied to VDD even though it’s an output
* SD NAND footprint likely wrong for the chosen package

---

## Opinionated “final” next-steps plan (in the order I would execute)

### Phase 1 — Make the schematic electrically correct (Rev A schematic freeze)

Do these first; don’t start layout until done.

1. **Fix nPM1300 net topology**

   * Create `VSYS` net.
   * Connect:

     * `VBAT` only to `pmic.VBAT` and the battery pad
     * `pmic.VSYS` → `VSYS`
     * `pmic.PVDD` → `VSYS`
   * Keep `pmic.AVSS` to GND as you do now.

2. **Swap buck assignment**

   * Use:

     * **Buck1 (SW1/VOUT1)** → `V1V8`
     * **Buck2 (SW2/VOUT2)** → `V3Vx` (recommend `3.0 V` for battery life; 3.3 if you insist)

3. **Add VSET resistors (mandatory)**

   * `VSET1 → GND`: 47 kΩ for 1.8 V (reference config)
   * `VSET2 → GND`: 150 kΩ for 3.0 V (reference config)

     * If you truly need 3.3 V at boot, use a value in the 250–500 kΩ range per table.

4. **Fix NTC handling**

   * Add NTC option footprint:

     * either a thermistor, or 0 Ω to GND
   * Document: if “no thermistor”, disable NTC feature in firmware (BCHGDISABLESET).

5. **Add proper VDDIO decoupling + I2C pull-ups**

   * Add **1 µF** + keep 100 nF on VDDIO (as per reference)
   * Add SDA/SCL pull-ups (start with 4.7 kΩ to VDDIO)

6. **Fix mic WAKE**

   * If unused: tie to **GND** or leave NC (per datasheet)
   * If used: route via level shifting to MCU (don’t direct-connect at 1.8 V)

7. **Add SD NAND local bulk cap**

   * Place **2.2 µF** very close to NAND VDD (datasheet guidance)

8. **Add antenna PI footprint**

   * Insert PI pads between RF and BOARD_ANT; populate 0 Ω in series by default.

9. **Add RGB LED subsystem**

   * My recommendation: use **nPM1300 LED0/1/2 current sinks** and a tiny RGB LED (common anode to VSYS / V3Vx). This minimizes MCU pin usage and fits the “tiny board” goal. (nPM1300 has 3 LED drivers noted in its feature list.)
   * If you need a “NeoPixel”-style LED, do it only if you can guarantee logic thresholds across VBAT range.

### Phase 2 — Fix footprints (before you spend money)

1. **Replace MKDV64GCL footprint** to match LGA‑8 6.6×8 mm and correct pad count/orientation.
2. Re-check:

   * nPM1300 QFN footprint (likely fine)
   * T5838 footprint vs datasheet acoustic port guidance (your hole size is OK)
   * HJ module footprint pin-1 and outline vs manual

### Phase 3 — Make the project actually generate a board you can validate mechanically

Right now, the build outputs don’t meaningfully encode the 19 mm circle constraint or antenna keepouts.

1. Create a real KiCad PCB file with:

   * **19 mm circular Edge.Cuts**
   * antenna keepout (per HJ manual)
   * mic port hole + bottom keepout

2. Ensure Atopile is actually updating that file (today your generated `.kicad_pcb` outputs are basically empty stubs, so layout integration isn’t happening).

### Phase 4 — Finish the adapter so it’s a real dock

1. **Fix USB-C D+/D- flip wiring**

   * Tie DP1↔DP2 and DN1↔DN2.

2. Add pogo-pin footprints / mating mechanism and map the adapter signals to real pins/pads.

3. Decide what the adapter MCU actually does:

   * SWD bridge? I2C bridge? NAND SPI programmer? power-only?
   * Then wire E73 GPIOs accordingly.

### Phase 5 — Firmware bring-up checklist (because nPM1300 needs configuration)

Even with perfect hardware, you still need early firmware to:

* Raise VBUS input current limit above the default 100 mA when charging from the dock.
* Configure charging current (default examples show low currents like 32 mA in a reference config).
* Disable NTC function if you strapped it to GND/no thermistor.
* Optionally control LED drivers.

---

## If you want one “minimum viable Rev A” target

If the goal is “works on first spin” rather than “perfect features”:

* Use nPM1300 config style: **1.8 V (VOUT1) + 3.0 V (VOUT2)** with strap resistors and proper VSYS/PVDD wiring.
* Don’t use mic WAKE (tie to GND).
* Keep SD NAND + mic + SWD + power + I2C.
* Add PI pads and a tiny RGB LED driven by PMIC LED pins.
* Fix the NAND footprint before anything else.

That path gives you the highest probability of a bootable board inside 19 mm.
