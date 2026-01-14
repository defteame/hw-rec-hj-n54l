According to a document from 2026-01-14 (your `snapshot.v2.zip` build artifacts + the datasheets you included), **most of the schematic-level issues are fixed on the main board**, but there are still **two true “stop-ship” items** (one footprint and one signal-bias choice), plus a couple of smaller but real corrections to make before you spend money on PCBs.

Below is an exhaustive status review, then an opinionated “do-this-next” plan.

---

## Main board (HJ_N54L + nPM1300 + SD NAND + T5838 mic)

### ✅ Fixed (the big ones)

**1) nPM1300 VBUSOUT misuse (previously tied into power)**

* In `main.ato`, **VBUSOUT is no longer used as a supply rail** (it is left unconnected), which is the correct interpretation of the datasheet.
* Nordic explicitly describes **VBUSOUT as “for host sensing” and “should not be used as a source.”** 
* Nordic also states VBUS is the input that supplies the system regulator (VSYS). 

**Action:** keep it unconnected electrically (or route to a testpoint only if you want measurement).

---

**2) PMIC buck voltage strap values**

* Your resistor choices match the nPM1300 strap tables:

  * **BUCK1 (VSET1 = 47kΩ) → 1.8 V** 
  * **BUCK2 (VSET2 = 470kΩ) → 3.3 V** (within the 250k–500k band for 3.3 V) 

This is correct.

---

**3) Mic PDM clock signal integrity**

* You added **a series resistor on PDM CLK** (33 Ω) on the 1.8 V side, as recommended.
* The mic datasheet explicitly says to use a series resistor on CLK to reduce overshoot/ringing. 

---

**4) nPM1300 “no thermistor” approach**

* You tied NTC to GND via 0 Ω and intend to disable the NTC function in firmware. That matches Nordic’s guidance: when thermistor isn’t used, NTC can be tied to GND (or via resistor) and the feature must be disabled via register. 

---

**5) HJ module “do not touch” pins**

* You did **not** connect P1-00 / P1-01, which is what the module manual wants if the 32.768 kHz oscillator is used internally. 

---

**6) Antenna matching “starter” network**

* You included a PI footprint set (0 Ω series + DNP shunts), which is the right “bring-up safe” approach.
* The module doc calls out the antenna pins to connect and the keep-out requirements. 

---

### ⚠️ Not fixed / still risky

These are the items I would *not* proceed to fabrication with until addressed.

#### A) **STOP-SHIP #1: SD NAND footprint has an extra pad (Pad 9) that does not exist in the pinout**

Your `CSNP64GCR01-BOW` part definition and footprint include an extra pad 9 (and you even connect it to GND in `main.ato` via `nand.NC ~ GND`).

But the datasheet pin assignment clearly defines **only pins 1–8** (CLK, VCC, CMD, DAT0–DAT3, GND).

In your KiCad footprint file (`LGA-8_L8.5-W7.0-P1.27-TL.kicad_mod`), **pad 9 is a real SMD pad located top-center**, not a “mechanical only” marker. That’s a very high probability of an assembly failure (misalignment, solder bridging, or an outright wrong land pattern).

**Opinionated recommendation:**

* **Delete pad 9 from the footprint** and remove the `NC` pin mapping from the symbol/part.
* Do **not** connect any “mystery pad” to GND unless the datasheet explicitly calls it out as EP/GND *and* provides a land pattern for it.

If you want maximum confidence: make a tiny **footprint coupon PCB** (just this NAND + pads) and solder one part before you commit the full design.

---

#### B) **STOP-SHIP #2: PDM DATA pull-down should not be populated**

Right now, you have a **1 MΩ pull-down** on the mic’s PDM_DATA at the 1.8 V side.

The T5838 datasheet explicitly warns: **do not use pull-up or pull-down resistors on the PDM data line** because they can force an incorrect state during the tri-stated interval. 

**Opinionated recommendation:**

* Keep the resistor **footprint** as an option if you want, but make it **DNP by default**.
* If you insist on a bias option, I’d rather bias on the **MCU input side** (after translation) and still keep it DNP until proven needed.

---

### ⚠️ Smaller but real improvements needed

#### 1) SD NAND local decoupling is below the vendor recommendation

Your NAND VCC decoupling is currently **1 µF + 0.1 µF** local.

The vendor reference notes recommend **2.2 µF on VCC** (and pull-ups + optional RCLK series). 

**Recommendation:** change `c_vdd` to **2.2 µF (or 4.7 µF)** and keep the 0.1 µF close.

---

#### 2) Your nPM1300 inductor choice is actually good (and already low-profile)

Nordic’s BUCK inductor guidance: DCR ≤ 400 mΩ, Isat > 350 mA, Imax > 200 mA. 

Your picked inductor (Sunlord CMH160808B2R2MT / C394950) datasheet shows:

* **1.6 × 0.8 × 0.8 mm** dimensions (height ~0.8 mm)
* **RDC ~0.24 Ω**
* **Rated current ~750 mA**

So you don’t “need” to change inductors for height.

---

#### 3) Level shifter direction pins are correct, but keep the “DIR is referenced to VCCA” rule in mind

You did the right thing (DIR=GND for CLK B→A, DIR=V1V8 for DATA A→B). TI notes DIR is **powered by VCCA** and should not be left floating.
Nothing to change here—just keep routing/decoupling tight.

---

#### 4) Documentation mismatch

`requirements.md` still says “Connect VBUSOUT to VSYS” which conflicts with the datasheet guidance and your corrected schematic. 
Update the doc so you don’t “fix it back” later.

---

#### 5) Layout is still not in a manufacturable state

In the generated KiCad PCB files:

* **No Edge.Cuts board outline is present** (so there is no 19 mm circle defined).
* Board thickness is still listed as 1.6 mm in the KiCad file headers (ordering can override, but the design intent should be consistent).

This isn’t a schematic error; it just means: **you’re not at “send to fab” yet.**

---

## Adapter board (USB-C + nRF52840 module)

Two separate issues here:

### 1) The adapter design is still electrically incomplete

In `adapter.ato` you define `POGO_*` signals, but:

* You do **not** instantiate pogo pads/connectors for those nets.
* You also do **not** connect `POGO_VBUS` to the USB VBUS net, or `POGO_GND` to GND.

So even if you had pads in KiCad, the *Atopile-generated netlist/BOM/PCB* won’t represent a usable adapter.

### 2) USB-C CC pins are missing Rd pull-downs

For a USB-C receptacle used as a device/sink, you typically need **Rd pull-down resistors on CC1/CC2** so the source will present VBUS. A Microchip Type‑C adapter reference schematic explicitly shows **5.1 kΩ on CC**. ([Microchip][1])

Right now your adapter.ato doesn’t include any CC network.

---

## One more red flag: adapter build outputs look inconsistent

In your snapshot, `build/builds/adapter/adapter.bom.csv` and the adapter logs appear to mirror the *main* board’s BOM/logs, while the `adapter.2026...kicad_pcb` file clearly contains the adapter components.

That indicates the adapter build outputs are **not trustworthy as-is** (likely stale build folder contamination). Even if you don’t change the schematic, I would not rely on those artifacts until you do a clean rebuild.

---

# Final, exact, opinionated plan: what to do next

I’m going to give you a plan that ends in **boards you can order + a bring-up sequence that will actually work**.

## Phase 1: Fix the remaining schematic/footprint show-stoppers (before layout)

1. **Fix SD NAND footprint**

   * Remove the extra pad 9 from `LGA-8_L8.5-W7.0-P1.27-TL.kicad_mod`.
   * Remove the `NC ~ pin 9` mapping from `CS_CSNP64GCR01_BOW.ato`.
   * Remove `nand.NC ~ GND` from `main.ato`.
   * Verification step: open the NAND datasheet pinout (pins 1–8 only) and make sure your symbol/footprint mapping exactly matches it.

2. **Make PDM DATA bias resistor DNP**

   * Keep the footprint if you want debug optionality.
   * Default to **not populated**, because the microphone datasheet says don’t use pull-ups/downs on PDM data. 

3. **Increase NAND local VCC decoupling**

   * Change NAND `c_vdd` from 1 µF → **2.2 µF (or 4.7 µF)**, keep 0.1 µF.
   * This matches the vendor reference note. 

4. **Update `requirements.md` to match reality**

   * Explicitly state: *VBUSOUT is sensing only, do not connect as a supply.* 
   * (Optional) Clean up the SD “SPI mode” wording so it doesn’t imply DAT3 is pulled low as a strap.

Only after these 4 are done do you move on.

---

## Phase 2: Make the adapter board either real or explicitly “out of scope”

Pick one of these paths (don’t stay in the middle):

### Path A (recommended): finish the adapter so it can actually power/program the main board

1. Add **CC1/CC2 pull-down resistors** (Rd) to GND (typically 5.1 kΩ). ([Microchip][1])
2. Instantiate pogo pads/connectors in `adapter.ato` and connect:

   * `POGO_VBUS ~ VBUS`
   * `POGO_GND ~ GND`
   * `POGO_SWDIO/CLK/RESET/DFU ~ the chosen GPIO pins`
3. Add a way to program the adapter MCU itself:

   * either a small SWD header/tag-connect, or a guaranteed USB DFU path (with a documented “how to flash first firmware” procedure).

### Path B: freeze adapter work and focus on main board only

* Remove adapter from your “deliverables” and don’t generate/manufacture it yet.
* But be explicit in the repo README: “adapter is placeholder / not for fab.”

---

## Phase 3: Define the main PCB as a real board

1. In KiCad (`layouts/main/main.kicad_pcb`), draw:

   * **19 mm circular Edge.Cuts**
   * **mounting/handling features** if needed (at least 2 tooling holes or a small flat edge)
2. Decide your stackup assumptions:

   * If you truly need 0.4 mm thickness, bake that into your rules/impedance assumptions.
3. Add keep-outs now:

   * Antenna keep-out region per the HJ module doc. 
   * Mic port keep-out + solder mask rules so the acoustic hole stays clear.

---

## Phase 4: Placement and routing rules (the “this will actually work” layout approach)

1. **Place the HJ module first**

   * Antenna at the edge; keep-out respected; no copper under/near antenna as required. 
2. **Place the PMIC + inductors + caps as a tight power island**

   * Short, wide power loops.
   * Keep SW nodes tight and away from mic/data lines.
3. **Place the mic near the edge with its PCB port hole**

   * Keep the hole clear and away from solder mask/paste issues.
4. **Place the SD NAND close to the MCU pins**

   * Keep CLK/CMD/DAT traces short, route as a small bus.
   * Put the NAND decoupling cap right at VCC/GND pins.
5. Route with a disciplined 2-layer approach:

   * Bottom layer as “as solid ground as possible”
   * Stitch ground vias around PMIC, around SD bus, around mic.

---

## Phase 5: Pre-fab checklist (don’t skip)

1. Run ERC/DRC with:

   * unconnected-pin report (expected: CC1/CC2 maybe on PMIC; SHPHLD; WAKE)
2. BOM sanity:

   * Ensure every populated part has a valid sourcing path (LCSC IDs, or marked “hand place”)
3. Footprint audit:

   * NAND (critical), PMIC QFN, mic, HJ module pads, pogo pads.
4. Output package:

   * Gerbers + drill + pick/place + BOM
   * assembly drawings (top) showing polarity/orientation of mic + NAND + PMIC.

---

## Phase 6: Bring-up plan (ordered, minimal pain)

1. **Power-only validation**

   * Apply USB 5 V to VBUS pad.
   * Confirm VSYS, BUCK2=3.3, BUCK1=1.8 come up.
2. **I2C bring-up**

   * Confirm MCU can read nPM1300 registers.
   * Disable NTC in firmware if you’re tying it to GND. 
3. **SWD programming reliability**

   * Verify you can flash the HJ module repeatedly via pogo pads.
4. **SD NAND**

   * Start at low SPI clock, read ID / init in SPI mode.
5. **Mic**

   * Verify CLK integrity (your series resistor is there). 
   * Capture PDM data and confirm audio stream.
6. **RF sanity**

   * Simple BLE advertising + scan test.
   * Only tune the PI network if range/performance is bad.

---

## The “do this right now” short list

If you want the quickest path to a board you can order without regret:

1. **Fix NAND footprint pad 9** (remove it; remove NC mapping; remove `nand.NC ~ GND`).
2. **Make PDM DATA bias resistor DNP** (datasheet says no pulls). 
3. **Change NAND VCC decoupling to 2.2 µF**. 
4. **Draw Edge.Cuts (19 mm circle) + keep-outs**, then start real placement/routing.
5. Decide whether you’re finishing the adapter now; if yes, add **CC pull-downs + pogo pads + connect POGO_VBUS/GND**. ([Microchip][1])

That’s the clean breakpoint between “schematic concept” and “prototype you can trust.”

[1]: https://ww1.microchip.com/downloads/en/DeviceDoc/USB-Type-C-Adapter-Users-Guide-50003005A.pdf "USB Type-C® Adapter Quick Start Guide"
