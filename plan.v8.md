According to a document from **2026-01-14** (your `snapshot.v2.zip` repo snapshot), the project **builds cleanly in Atopile** and the “big blocks” are in place, but there are still a few **hard blockers** that will prevent the hardware from working (or being manufacturable) unless you fix them **before** you invest time in the 19 mm layout.

Below is an opinionated, exhaustive review of what’s good, what’s still broken, and the exact next steps I would take.

---

## What looks solid / genuinely improved

### Power architecture is coherent

* **nPM1300** is used as charger + PMIC and you derive **1.8 V and 3.3 V from the two bucks**, which matches your overall partitioning. 
* **VSET strap values** match the datasheet guidance: 47 kΩ for 1.8 V and a 250–500 kΩ range for 3.3 V (you used 470 kΩ). Also, you’re not leaving VSET pins floating. ✅
* I²C pull‑ups exist (and go to the PMIC’s VDDIO rail, which you set to 3.3 V). ✅

### MCU voltage choice matches IO threshold reality

The HJ module’s IO high threshold is **0.7 × VCC**, so if VCC is 3.3 V you should expect ~2.31 V minimum VIH. That means **a 1.8 V mic cannot directly drive the MCU**—you correctly added level shifting for PDM. ✅

### SD NAND supporting passives are present

The SD NAND needs pull‑ups on CMD/DAT lines and local decoupling; your design includes:

* Pull‑ups (10 kΩ is within the datasheet’s suggested 10 kΩ–100 kΩ range) ✅
* Bulk + HF caps on VDD ✅

---

## Hard blockers that are **not** fixed yet

### 1) SD NAND footprint is wrong for the actual package

Your current footprint for `MKDV64GCL-STP` is a **WSON‑8 8.0×6.0 with exposed pad**, but the datasheet for the part you’re referencing describes an **8‑pin LGA, 6.6 mm × 8.0 mm × 0.8 mm** package.

LCSC’s own listing for the same part family also describes it as **LGA‑8 (6.6×8.0)**.

**Why this is a blocker**

* If the land pattern is wrong (size + pad geometry + presence of an EP pad that doesn’t exist), you can get:

  * opens/shorts,
  * the part “floating” on reflow,
  * mis-registration and total non-function.

**What to do**

* Create a **new KiCad footprint**: `LGA-8_8.0x6.6_P1.27` (or similar), using the datasheet’s mechanical drawing and pad geometry.
* Update the Atopile part (`parts/MK_MKDV64GCL_STP/...`) to:

  * reference the new footprint,
  * **remove the bogus pad 9 / EP** if it’s not actually present on this package.
* Rebuild and re-check the netlist/BOM/CPL.

This is the single most important mechanical/electrical fix in the whole repo right now.

---

### 2) SD NAND is not actually usable because CS is not connected to the MCU

In your `main.ato`, SD NAND `DAT3` is only connected to:

* a pull‑up resistor, and
* a pogo/test pad (`pad_nand_cs`),

…but it’s **not connected to any MCU GPIO**, so the MCU cannot select the device.

This matters because SD NAND “SD mode” requires an SD/MMC host (SDIO/SDMMC). The nRF54L series public datasheets list serial peripherals like SPI/I²C/UART/I²S/PDM but **do not indicate an SDMMC/SDIO host**.

Meanwhile, the SD NAND datasheet explicitly describes using **DAT3 pulled low to enter SPI mode**, and the host then issues **CMD0** to start SPI-mode operation. ✅

So practically: you should treat this as an **SPI SD device**, and in SPI mode you need **CS** (DAT3).

**What to do**

* Pick a free GPIO (example: `mcu.P1_07`, but any suitable one is fine) and connect it:

  * `nand.DAT3 ~ mcu.<your_cs_pin>`
  * keep `r_nand_dat3` pull‑up
  * keep `pad_nand_cs` if you still want external access
* Optionally add a small series resistor (0–33 Ω) on CS if you want a little isolation for adapter-driven programming.

Until you do this, the NAND subsystem is “present” but non-functional from firmware.

---

### 3) Mic WAKE is tied to GND (this can short a driven output)

You currently hard‑tie:

* `mic.WAKE ~ GND`

The T5838 datasheet describes modes where **WAKE is asserted** (set high) when a wake word event occurs and later returns low. ✅ 

If WAKE is driven high and you strap it to ground, you’ve built a **direct short** during that assertion.

**What to do**

* If you don’t need WAKE yet: **leave WAKE unconnected**.
* If you do want wake‑word interrupt capability:

  * route WAKE to an MCU GPIO, but remember the IO threshold issue: with MCU at 3.3 V, you’ll need **level shifting** for a 1.8 V WAKE signal to be reliably detected (VIH ≈ 0.7×VCC). ✅

---

### 4) PDM data level shifter DIR is tied to 3.3 V (should be driven from VCCA domain)

For the PDM data translator (`SN74LVC1T45`), you currently have:

* `level_shifter_data.VCCA ~ V1V8`
* `level_shifter_data.VCCB ~ V3V3`
* `level_shifter_data.DIR ~ V3V3`  ❌

TI’s datasheet states **DIR input is powered by VCCA**.
So when VCCA = 1.8 V, driving DIR with 3.3 V is not the intended usage and can cause:

* back-powering/injection into the VCCA domain,
* undefined behavior during sequencing.

**What to do**

* Tie `level_shifter_data.DIR` to **V1V8** (logic-high in the VCCA domain), not V3V3.
* Direction is still correct conceptually: DIR=H means A→B (mic→MCU).

---

### 5) PMIC external caps around VSYS/VBUSOUT/PVDD are under-specified vs reference configs

Your design defines `VSYS` and ties `pmic.PVDD ~ VSYS`, but:

* there’s **no VSYS bulk capacitor**, and
* `VBUSOUT` is currently not connected anywhere.

In the nPM1300 hardware configuration reference tables, **VBUSOUT is “Configured”** for the typical configurations (1 and 2). ✅ 
Those same reference configs show multiple external capacitors in the BOM (including 1 µF and several 10 µF parts) tied to the system rail region. ✅

Also, the PMIC spec explicitly says you should **not supply the application directly from VBAT**; use VOUT1/VOUT2/VSYS. ✅

**What to do (practical minimum)**

* Add **at least one** bulk capacitor on **VSYS** (I would do 10 µF X5R/X7R near the PMIC).
* Decide what you want to do with VBUSOUT:

  * If you follow the reference-style “configured” approach, connect `VBUSOUT` to the VSYS node and include the recommended decoupling for the combined node.
  * If you want VBUSOUT strictly for sensing, keep it separate and decouple it as described (but then be sure you still satisfy PVDD/VSYS stability).

Also note: If CC pins are floating (as yours are), the datasheet says that’s allowed if you’re not doing USB‑C configuration, but **the default VBUS current limit stays at 100 mA until configured**. ✅
That has real bring-up impact: if your system + charging exceeds 100 mA before firmware config, you can brown out.

---

### 6) RF pi network shunt caps are being populated by default (dangerous)

Your antenna matching network uses:

* series 0 Ω
* two shunt caps defined with a range (0.1–10 pF)

Atopile picked **4.7 pF** parts for both shunts and they appear in the BOM as real components.

The HJ module manual says the RF pin must be connected to the BOARD_ANT pin (and suggests a pi network). ✅ 
But with an onboard antenna, you generally **do not want random shunt capacitors** unless you’ve tuned the full assembled device.

**What to do**

* Treat both shunt capacitors as **DNP placeholders** by default.

  * The safest workflow in your current Atopile style is: represent them as **footprint-only** parts (no picker / no BOM part), similar to how you already treat pads.
* Keep the footprints so you can populate later during RF tuning.

---

## The layout is not started (and you can’t validate the “19 mm / 0.4 mm / top-only” requirement yet)

Your `requirements.md` is very specific: ~19 mm circular board, **0.4 mm thickness**, no bottom components, acoustic hole, RGB LED, etc. ✅

In the current KiCad PCB files:

* board thickness is still 1.6 mm,
* there is no Edge.Cuts outline,
* footprints are essentially in an auto-scatter state (not a placed/routed design).

So: the repo is **schematic-ready-ish**, but **not** “layout-ready” until the blockers above are fixed.

Also: the microphone acoustic hole constraints matter a lot and should drive placement early:

* datasheet recommends a **0.5–1.0 mm diameter** hole (or equivalent area), and to **avoid solder paste** contaminating the sound hole. ✅

---

## Opinionated next steps (in the order I would do them)

### Phase 0 — Freeze the pin map and pogo interface

1. Decide the **exact** signals that must cross to the adapter via pogo:

* SWDIO/SWCLK/RESET/GND/VBUS (minimum)
* NAND SPI (CLK/MOSI/MISO/CS) if you want adapter-side access
* optionally I²C (SCL/SDA) if you want to talk to nPM1300 without the main MCU

2. Make main+adapter agree on the same pad list and naming.

This avoids the classic “two boards evolve separately” failure.

---

### Phase 1 — Fix the 6 schematic/blocking issues

Do these before layout:

1. **Fix SD NAND footprint** (LGA‑8 6.6×8.0) and remove the exposed pad mismatch.
2. **Connect NAND CS (DAT3) to an MCU GPIO** for SPI mode. ✅
3. **Remove `mic.WAKE ~ GND`**. ✅
4. **Change `level_shifter_data.DIR` to V1V8**.
5. **Add VSYS bulk decoupling** and decide VBUSOUT wiring consistent with nPM1300 reference configs. ✅
6. Convert antenna shunt caps to **DNP footprints** (no picker) so they are not auto-populated.

After these, regenerate BOM and sanity-check:

* SD NAND is present + correct package
* RF shunt caps are not in BOM
* PMIC has the additional caps

---

### Phase 2 — Layout plan for a 19 mm round board

This is the part you can’t shortcut.

1. **Set board constraints first**

* Edge.Cuts: 18.6 mm or whatever your final diameter is
* thickness: 0.4 mm
* define keepouts for:

  * antenna region
  * mic acoustic hole region
  * pogo pad contact region

2. **Place HJ module first (RF-driven placement)**
   The manual guidance is clear:

* place module at **PCB edge/corner**,
* avoid placing traces/components near the antenna,
* keep copper away from the antenna area and underside. ✅

3. **Place the pi network immediately adjacent to pins 23/24**
   Keep it tight and symmetric, with very short stubs to shunt parts.

4. **Place mic + define the acoustic hole**

* Put the mic so the sound port aligns with the PCB hole.
* Follow the hole sizing and “no paste in hole” guidance. ✅

5. **Place PMIC + inductors + caps next**

* Keep buck loops tiny (SW pin → inductor → output cap → ground return).
* Put the VSYS/“system rail” caps right at the PMIC pins.

6. **Place SD NAND close to the MCU pins**

* Keep SPI traces short, avoid running under the antenna keepout.
* Add ground vias around the NAND and PMIC for a solid return.

7. **Add the RGB LED** (requirement)
   It’s in requirements but not in the schematic. ✅

---

### Phase 3 — DFM and ordering checklist

Before ordering:

* Confirm every footprint matches **the actual package** you’ll buy (especially SD NAND + X2SON translators).
* Add:

  * 2–3 fiducials,
  * tooling holes / panel rails if your assembler requires,
  * clear polarity/orientation marking for mic and PMIC.
* Ensure “no bottom components” is enforced in placement.
* Ensure the mic sound hole is treated properly in solder mask + paste layers (no paste).

---

### Phase 4 — Bring-up plan (what to test in what order)

1. Power only (no firmware):

* Apply VBUS, check VBAT/VSYS/VOUT1/VOUT2 rails, verify no overheating.

2. SWD + minimal firmware:

* Blink LED (when you add it)
* I²C scan PMIC
* Configure VBUS current limit above 100 mA early if needed. ✅

3. NAND SPI bring-up:

* Enter SPI mode via CS/DAT3 control and do CMD0 init sequence. ✅

4. Mic PDM capture:

* Ensure you do **not** enable pulls on the PDM data line (datasheet warns against pull-ups/downs because of tri-state behavior). ✅

5. RF smoke test:

* BLE advertising range sanity check
* Only tune the pi network after you have a mechanically representative assembly.

---

## Bottom line

Snapshot v2 is *close* on the architecture, but it’s **not “properly fixed” yet** because of:

* the SD NAND **package/footprint mismatch**,
* missing **NAND CS to MCU** (so storage can’t work),
* mic **WAKE short to ground**,
* data level shifter **DIR tied to the wrong rail**,
* PMIC **VSYS/VBUSOUT decoupling/config gaps**,
* RF shunt caps being **auto-populated**,
* and the layout is still a placeholder (no 19 mm / 0.4 mm enforcement).

If you want, I can also propose a concrete revised pin map (MCU pins for NAND SPI + PDM + pogo) that minimizes routing on a 19 mm circle and respects the antenna keepout rules.
