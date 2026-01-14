I unpacked `v4.zip` and reviewed:

* **Atopile source**: `main.ato`, `adapter.ato`, plus all custom parts in `parts/`
* **Build artifacts**: `build/builds/main/**` + `build/builds/adapter/**` (BOM + netlists + KiCad outputs)
* **Logs**: `build/logs/**` (picker + bom + export)
* **Datasheets you attached**:

  * HJ module hardware design manual
  * Nordic nPM1300 product spec
  * TDK/Invensense T5838 datasheet
  * CSNP64GCR01 SD NAND datasheet

Below is a “hardware bring-up / does-it-work” focused review, and then an opinionated next-steps plan.

---

## 1) High-level architecture as implemented (main board)

### Major ICs in `main.ato` (and in `main.bom.csv`)

* **U3**: `HJ-N54L_SIP` (consigned / not LCSC-picked)
* **U5**: `nPM1300-QEAA-R7` PMIC (LCSC **C2892451**)
* **U4**: `CSNP64GCR01-BOW` SD NAND (LCSC **C5258408**)
* **MK1**: `T5838` digital PDM mic (LCSC **C3290857**)
* **U1/U2**: `SN74LVC1T45` level shifters (LCSC **C7840**) for PDM CLK + DATA
* **L1/L2**: 2.2 µH inductors for nPM1300 buck converters (LCSC **C394950**)

### Power tree (as designed)

* **VBUS (5V)** comes in via pogo pad TP6 → **nPM1300 VBUS**
* **VBAT** comes in via solder pad J1 → **nPM1300 VBAT**
* **nPM1300 VSYS** power-path rail feeds the buck inputs (PVDD tied to VSYS in your design)
* **BUCK1 (VOUT1)** configured to **1.8 V** → supplies:

  * T5838 mic VDD
  * VCCA side of both level shifters
* **BUCK2 (VOUT2)** configured to **3.3 V** → supplies:

  * HJ-N54L_SIP VDD
  * SD NAND VCC
  * VCCB side of both level shifters
  * PMIC VDDIO (I/O rail for TWI)

This split (1.8V + 3.3V) is consistent with the mic’s *strict* ~1.8 V supply requirement and the NAND’s 2.7–3.6 V requirement. The T5838 operating supply is 1.62–1.98 V (abs max 1.98 V), so powering it from your 1.8 V buck is correct. 

---

## 2) Does the schematic have the required functional blocks?

### 2.1 HJ-N54L_SIP module (U3)

**What you did right**

* **Supply voltage**: HJ module VDD range is **1.7–3.6 V**, so 3.3 V rail is valid. 
* **Internal 32.768 kHz pins left alone**: manual warns P1-00/P1-01 connect to internal crystal and “no other components can connect” (unless you choose not to use that oscillator). Your design leaves them unconnected, which is correct. 
* **Antenna pins**: the module manual describes **pin 23 RF** and **pin 24 BOARD_ANT** and states that for the built-in antenna, you can “simply connect” RF to BOARD_ANT, while noting an additional **PI network** may be required depending on structure. Your design implements exactly that with a PI footprint (shunt caps DNP + 0Ω series link). 

**Main risk**

* **RF performance is going to be 90% layout**. The manual explicitly recommends placing the module at a PCB **edge/corner** and keeping other devices away from the antenna area. 
  Right now, the KiCad PCB in `build/builds/main/main.kicad_pcb` is still in the “pile of parts” placement (all footprints stacked at x=0, y=-10 mm steps), so there’s no evidence yet that the antenna keepouts / board-edge placement constraints are actually satisfied.

**Recommendation (schematic-level)**

* Keep your PI network default as you have it: **0Ω series + shunts DNP** is the correct “start” for bring-up, and gives you tuning options later. 

---

### 2.2 nPM1300 power management (U5)

#### BUCK output voltage configuration is correct

Your resistor choices match Nordic’s strap tables:

* **VSET1 = 47 kΩ → BUCK1 = 1.8 V** (25–75 kΩ range) 
* **VSET2 = 470 kΩ → BUCK2 = 3.3 V** (250–500 kΩ range) 
  The table also says *“Do not leave VSET[n] floating.”*  — and you didn’t.

Also, nPM1300 has **two 200 mA buck converters** (so your loads are within the intended envelope). 

#### Inductor/output capacitor selection: largely consistent

Nordic’s guidance (from the product spec) calls out:

* Inductor: **2.2 µH**, DCR ≤ 400 mΩ, saturation current > 350 mA, rated current > 200 mA
* Output cap: effective ≥ 4 µF, ESR ≤ 50 mΩ 

Your inductors are 2.2 µH and look to be comfortably above 200 mA rated (based on the LCSC part class). Your 10 µF 0603 ceramics on both rails are also in-family.

#### Critical schematic gap: PVDD / buck input decoupling is under-specified

Nordic explicitly states: **“BUCK supply voltage should be decoupled with high performance capacitors as close to the supply pins as possible.”** 

In Nordic’s reference BOM, there is a **dedicated 1.0 µF capacitor (C5)** associated with PVDD decoupling in the reference schematic/BOM set.

In your `main.ato`, **PVDD is tied to VSYS**, and you only place **one 10 µF** on VSYS (C22). There is **no explicit small/close PVDD decoupler** called out. Electrically, “a cap on VSYS” *can* serve PVDD if you place it right at the pin, but the reference design strongly suggests you want a **small high-performance cap local to PVDD** (and in practice: a 1 µF + 100 nF combo very close to the PMIC pins).

**This is the biggest “could cause unstable bucks / noisy rails / bring-up weirdness” item I see.**

#### Charger/current-limit behavior: works, but only if firmware configures it

Two key default-behavior points from the nPM1300 spec:

* If CC pins are not used/detected, **VBUS current limit remains at 100 mA** by default. 
* Battery charging is **disabled by default** (register reset value is 0) until the host enables it over TWI. 
  And the **default charge current** register value is **32 mA**. 

So: the board can power up from VBUS and run, but **“plug in USB and battery charges automatically” is not true** unless you configure nPM1300 (OTP or firmware). That’s not a schematic error—just a bring-up reality you should plan for.

#### CC1/CC2 pins are floating in your main board

You intentionally left **CC1/CC2** unconnected (single-node nets). Nordic notes CC pins can be left floating or tied to GND, but then the **default 100 mA limit** remains. 

**This is acceptable for a pogo-powered dev setup**, but it will likely surprise you during real-world USB testing (slow charging, brownouts if you draw >100 mA without first configuring the PMIC).

#### NTC handling is correct (but requires firmware disable)

You tied NTC to ground through a resistor. Nordic states: if thermistor is not used, NTC must be tied to GND (directly or through resistor) and the functionality must be disabled in BCHGDISABLESET.
So hardware choice is aligned; just remember firmware must disable NTC checks if you don’t have a thermistor.

---

### 2.3 SD NAND (U4: CSNP64GCR01-BOW)

**Electrical compatibility**

* VCC is **2.7–3.6 V**, so powering from 3.3 V is correct. 

**SPI-mode wiring is correct**
The datasheet’s “SPI mode” mapping states:

* **CD/SDD3 = CS**
* **CMD = DI (MOSI)**
* **SDD0 = DO (MISO)**
* **SCLK = CLK**
* **SDD2/SDD1 = reserved in SPI** 

Your netlist matches that:

* MCU P1_07 ↔ DAT3/CS
* MCU P1_03 ↔ CMD/MOSI
* MCU P1_04 ↔ DAT0/MISO
* MCU P1_02 ↔ SCLK

**Required passives: you did them correctly**
The vendor reference design explicitly recommends:

* Pull-ups: **RDAT/RCMD 10 k–100 k**, and host pulls up all DAT0–3
* VCC capacitance: **~2.2 µF**
* Series resistor on clock: **RCLK 0–120 Ω** 

Your design includes:

* 10 k pull-ups on CMD, DAT0, DAT1, DAT2, DAT3 (DAT1/2 are pulled high even though unused in SPI—good practice)
* 2.2 µF + 0.1 µF on VCC
* 33 Ω series on SCLK (within 0–120 Ω)

**So NAND hardware looks correct.**

**System-level note**
The NAND operation current is on the order of tens of mA at higher clock rates.  Your buck2 + 10 µF rail should be fine, but you’ll want tight routing and a solid ground reference.

---

### 2.4 TDK / InvenSense T5838 PDM mic (MK1)

**Supply is correct**
T5838 operating supply is **1.62–1.98 V** (typ 1.8). 
So your decision to run it from the 1.8 V buck is right.

**Pins you tied off are consistent with “no AAD mode”**

* WAKE can be tied to GND or left as **No Connect** when AAD isn’t used. 
* THSEL can be tied to GND or left NC when AAD isn’t used. 
* SELECT tied to GND sets one of the mono channel options (fine).

**Signal integrity guidance: you followed the key rules**

* Datasheet says place a **0.1 µF** decoupling cap close to VDD.  You did (C20 = 100 nF).
* Datasheet explicitly says **do not use pull-up or pull-down on PDM data** line.  You did not (your R12 is DNP and can remain DNP).
* Datasheet allows a **source termination resistor** on the PDM clock output.  You included 33 Ω in series.

**Acoustic hole / footprint**
TDK recommends an acoustic hole around **0.5–1.0 mm diameter** (and “not smaller than ~0.375 mm”). 
Your footprint file includes a **0.5 mm NPTH** hole, which is within that guidance.

Microphone source reference: 

---

### 2.5 Level shifting (U1/U2: SN74LVC1T45)

Given mic is ~1.8 V logic and MCU rail is 3.3 V, level shifting is justified.

* You used **two** 1T45s so clock and data can each have fixed direction:

  * U1: CLK B→A (3.3→1.8)
  * U2: DATA A→B (1.8→3.3)
* TI documentation states the **DIR pin is referenced to VCCA**, and the device supports **partial power-down (Ioff)** and “glitch-free power supply sequencing.”
  That matches your wiring (DIR tied to VCCA for the DATA shifter, DIR tied low for the CLK shifter).

**This block is correct and robust.**

---

## 3) What Atopile picked, and what the build/logs say

### Atopile picking / BOM status

* **Main BOM** includes all needed passives + ICs **except**:

  * HJ-N54L_SIP module is intentionally **not picked** (consigned)
  * DNP antenna shunt caps and DNP PDM data bias resistor are excluded (correct)
  * pogo pads / wire pads are footprints (no LCSC parts)

The `picker.warning.log` contains only “No pickers found” warnings for those expected items; there are **no fatal errors** in logs.

### Important: KiCad PCB placement is not done

In `build/builds/main/main.kicad_pcb`, all footprints are still in the “unplaced” vertical stack (x=0, y=-10mm increments). So:

* No 19 mm circular board outline is implemented yet
* No proof of antenna keepout, power loop placement, or “top-side only” optimization exists yet

So: schematic can be “right”, but the project isn’t yet in the stage where you can validate the hardest constraints (RF + switching + acoustic + 19mm mechanics).

---

## 4) My verdict: does this work as-is?

### It will very likely “power on and run” with firmware

* Rails (1.8 and 3.3) are configured correctly via VSET resistors. 
* Mic supply and interface are electrically correct. 
* SD NAND wiring and required pull-ups/cap/series resistor match vendor reference. 

### The biggest “could fail or be flaky” hardware issue

* **Buck input/PVDD decoupling is not explicit enough**. Nordic calls for close, high-performance decoupling at BUCK supply pins (PVDD). 
  You currently only have a single 10 µF on VSYS and no “PVDD-local” 1 µF + 100 nF called out.

This might still work if you place that 10 µF and a small 100 nF right on the PVDD/VSYS pins in layout, but the safest approach is to **add dedicated PVDD decouplers in the schematic** so you cannot forget them in layout.

### “It works” expectations you should set

* **Battery charging will not just happen** unless you configure the nPM1300: charging is disabled by default and charge current defaults low. 
* With CC pins floating, VBUS current limit defaults to **100 mA** until you configure it (or implement CC detection). 

---

## 5) Opinionated, final plan for next steps

### Step A — Fix the schematic now (before layout)

1. **Add explicit PVDD/VSYS decoupling local to U5**

   * Add **1.0 µF** + **100 nF** from **VSYS/PVDD** to GND, annotated clearly “place next to PVDD pin”.
   * This aligns with Nordic’s requirement for PVDD decoupling close to pins. 

   Atopile-style patch (conceptually):

   ```ato
   c_pvdd_bulk = new Capacitor
   c_pvdd_bulk.capacitance = 1uF +/- 20%
   c_pvdd_bulk.voltage = 10V
   c_pvdd_bulk.footprint = "C0402"  # or 0603 if you prefer stable capacitance

   c_pvdd_hf = new Capacitor
   c_pvdd_hf.capacitance = 100nF +/- 10%
   c_pvdd_hf.voltage = 10V
   c_pvdd_hf.footprint = "C0201"

   c_pvdd_bulk.p1 ~ VSYS
   c_pvdd_bulk.p2 ~ GND
   c_pvdd_hf.p1 ~ VSYS
   c_pvdd_hf.p2 ~ GND
   ```

   (Exact net name depends on your implementation; in your design PVDD is tied to VSYS.)

2. **Decide what you want from USB / VBUS behavior**

   * If “dev pogo power only”: keep CC pins floating; handle current limits in firmware.
   * If “real USB-C plug-in charging”: strongly consider **bringing CC1/CC2 to pogo pads** (or add a Type-C connector on some future board) so nPM1300 can do Type‑C detection and automatically lift limits. Otherwise you’re stuck at 100 mA until firmware intervenes. 

3. **Add one PMIC interrupt/GPIO to MCU (optional but high-value)**

   * Right now PMIC is only on I²C. If you want clean firmware, wire **one PMIC GPIO** (configured as interrupt) to an MCU pin + a test pad.
   * Not required to “work”, but it’s a big bring-up/firmware quality improvement.

4. **Keep R12 as DNP permanently unless you have a specific reason**

   * T5838 explicitly warns against pull-up/pull-down on PDM data. 

---

### Step B — Footprint/DFM sanity before you route

1. **nPM1300 exposed pad paste**

   * Your current QFN footprint uses a single large paste aperture for the exposed pad.
   * I would change it to **segmented paste** (or at minimum paste reduction) to reduce float/tilt risk during reflow. This is a common failure mode on small QFNs.

2. **0201 usage check**

   * You have many 0201 caps/resistors. That’s fine if your assembly house supports 0201 reliably (many do), but confirm now.
   * If you want to de-risk assembly for Rev A, moving “non-critical” 0201s to 0402 is often worth it, especially on a dense RF/power design.

---

### Step C — Layout (this is where success/failure will be decided)

Given the constraints (19 mm circle, RF module with antenna, switching bucks, bottom-port mic, SD NAND), I’d do this:

1. **Pick a 4-layer stackup**

   * Top: components + short routing
   * Inner1: solid GND plane
   * Inner2: power distribution (VBUS/VBAT/VSYS/V3V3/V1V8 regions)
   * Bottom: routing + pogo pads (or keep mostly GND)

   nPM1300 layout guidance strongly emphasizes ground plane and short supply/ground connections. 

2. **Place the HJ module first**

   * Put it at the **board edge/corner**, and enforce antenna keepout on *all layers* (no copper, no vias, no components) per the module manual’s guidance. 

3. **Place PI matching network right at the RF pins**

   * Keep RF trace extremely short between RF and BOARD_ANT pins and the PI parts. 

4. **Place nPM1300 + inductors + output caps as the next “fixed cluster”**

   * Put inductors tight to SW pins.
   * Keep the high di/dt loops tiny.
   * Keep SW copper away from the mic and away from antenna region.

5. **Place microphone with correct hole and keepout**

   * Ensure the acoustic hole is clear (no paste/mask issues) and routes to the outside of the enclosure.
   * Keep switching node traces away from mic.

6. **Place SD NAND near the MCU module pins**

   * Short SPI traces, keep a continuous ground reference.
   * Put its 2.2 µF + 0.1 µF caps right at the NAND VCC pins.

7. **Pogo pads**

   * Put pogo pads on the bottom if you need the entire top for components (typical).
   * Or keep on top if your jig presses from above—just don’t place them in the antenna keepout region.

---

### Step D — Bring-up plan (what I would do on Rev A)

1. **Power-only validation**

   * With battery and with VBUS:

     * Verify VSYS, VOUT1=1.8, VOUT2=3.3 under light load
     * Check ripple on 1.8 (mic rail) and 3.3

2. **I²C communication to nPM1300**

   * Confirm the MCU can read/write registers.
   * Early in firmware, set:

     * VBUS input current limit to a safe-but-useful value (depending on supply)
     * Enable charging if desired (it’s disabled by default) 

3. **SWD programming reliability**

   * Confirm SWD works with your pogo/adapter setup before touching peripherals.

4. **Peripheral validation**

   * Mic: enable PDM, confirm non-zero stream, check for obvious clocking/bit issues.
   * NAND: run SD-over-SPI init, identify card, do read/write test, then filesystem.

---

## Bottom line

* **Schematic correctness**: concept is solid and most interfaces match the attached datasheets.
* **Big required fix**: add explicit **PVDD/VSYS local decoupling** for nPM1300 (and then place it correctly). This is your highest-leverage hardware change before layout. 
* **Big system reality**: charging/current limits need **firmware configuration** (and CC pins floating means default 100 mA on VBUS). 
* **Biggest remaining work**: the PCB is not laid out yet, and your success on a 19 mm circle will hinge on **placement/keepouts** (antenna + buck switching + mic hole). 

If you want, I can also produce a **Rev-A layout placement strategy sketch** (“put these clusters here, route these nets like this, keepouts here”) tailored to a 19 mm circle—based strictly on your current netlist and the module/mic/PMIC layout rules.
