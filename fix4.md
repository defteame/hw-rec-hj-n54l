According to a document from **2026-01-14** (the `high-level-plan.md` + the generated `build/` outputs inside `v4.zip`), **most of the previously flagged schematic/footprint “stop-ship” issues are fixed**, but there are **two remaining electrical fixes** you should do *before* you move on to PCB layout / ordering.

## What’s fixed in v4

### Main board (`main.ato`)

* **NAND decoupling is now correct**: you added the **2.2 µF + 0.1 µF** bypass at the SD NAND VCC, matching the vendor’s recommended application circuit.
* **PDM DATA pull-down is removed (DNP)**: this aligns with the T5838 guidance that the DATA line is tri-stated when not selected and you should not use pull-ups/pull-downs. 
* **T5838 WAKE/THSEL handling is acceptable**: WAKE/THSEL can be tied to GND or left unconnected if unused; SELECT can be tied high/low for channel. (Your current “leave WAKE NC” approach is still OK.)
* **nPM1300 BUCK enable/voltage selection via VSET resistors is coherent**:

  * BUCK is enabled if VSET is connected to a resistor (and disabled if grounded). 
  * Your chosen resistor values match the default outputs you want:

    * **47 kΩ → 1.8 V** (VOUT1)
    * **470 kΩ → 3.3 V** (VOUT2)
* **HJ module antenna wiring concept matches the vendor guidance** (RF to BOARD_ANT with a PI option): the manual explicitly calls out connecting the RF interface pin to the built‑in antenna pin through a PI filter for best effect. 
* **Pins P1_00/P1_01 are left alone** (as required for the internal 32.768 kHz oscillator). 

### NAND “mystery pad” resolution

* Your decision to keep the extra middle pad as **NC with no solder paste** is consistent with vendor/test‑board guidance: “middle PIN should remain untinned and left as NC.” ([longsto.com][1])

## What is **not** fully fixed yet (important)

### 1) Main board: **Missing VBUSOUT decoupling capacitor** (nPM1300)

Even if you leave **VBUSOUT unconnected**, Nordic’s own product spec states **VBUSOUT must have a decoupling capacitor**. 

And in Nordic’s reference BOM/schematic, **VBUSOUT has a 1.0 µF capacitor (C14)**. 

Right now in your `main` netlist, `VBUSOUT` only connects to U5 and nothing else (no cap), so this is a real missing component.

**Why it matters:** leaving a regulator/output pin without its required local decoupling can cause instability/noise or unpredictable behavior.

### 2) Adapter board: **E73 USB power pins aren’t connected (USB likely won’t work)**

Your adapter includes USB‑C and routes D+/D‑, but the E73/nRF52840 module pins for USB power mode aren’t wired:

* Nordic guidance: the **USB peripheral runs off VBUS (4.35–5.5 V)**, and you must supply **VBUS** plus the normal supply rails. ([Internet Archive][2])
* The E73 user manual text (mirrors common nRF52840 module pinouts) identifies **VBS as VBUS (USB 5 V input)**.
* The same manual describes **Normal voltage mode** as **VDD = VDDH = power supply** (i.e., you should tie VDDH to your 3.3 V rail if you’re powering the module at 3.3 V). ([Internet Archive][2])

Right now your adapter powers only `VCC` from the LDO and leaves `VBS` and `VDH` floating → that’s very likely to break USB enumeration (and may violate the module’s expected power configuration).

## Exact next actions

### A) Make these two edits (minimum required)

#### 1) **Main board (`main.ato`)** — add `VBUSOUT` capacitor

Add a capacitor from `pmic.VBUSOUT` to `GND`.

* Value: **1.0 µF** (match Nordic reference) 
* Voltage rating: pick something safe for “VBUS-ish” nodes (I’d use **≥10 V**).

Example snippet (place near other PMIC caps):

```ato
    # Required nPM1300 VBUSOUT decoupling
    c_vbusout = new Capacitor
    c_vbusout.value = 1uF
    c_vbusout.package = "0402"  # or 0201 if you must
    c_vbusout.voltage = 10V
    c_vbusout.p1 ~ pmic.VBUSOUT
    c_vbusout.p2 ~ GND
```

Also update `high-level-plan.md` line about VBUSOUT to say “left unconnected **but still decoupled with 1 µF**” (because the spec explicitly requires the capacitor). 

#### 2) **Adapter board (`adapter.ato`)** — wire E73 USB/power pins

Add these connections:

* `mcu.VBS ~ VBUS` (USB VBUS input) ([Internet Archive][2])
* `mcu.VDH ~ V3V3` (tie VDDH to the 3.3 V rail in normal voltage mode) ([Internet Archive][2])

Example:

```ato
    # Required for nRF52840 USB operation + normal voltage mode
    mcu.VBS ~ VBUS     # 5V from USB-C
    mcu.VDH ~ V3V3     # tie VDDH to 3.3V (normal mode: VDD = VDDH)
```

(Leave `mcu.DCH` alone unless you intentionally plan to use the high-voltage/DC/DC mode.)

---

### B) Rebuild and sanity-check nets (fast verification)

After those edits:

1. Re-run your atopile build (whatever you used for v4).
2. Confirm in the **main** netlist that net `VBUSOUT` now has **U5 + the new capacitor**.
3. Confirm in the **adapter** netlist that `VBUS` connects to **USB connector VBUS + LDO VIN + E73 VBS**, and `V3V3` connects to **E73 VCC + E73 VDH**.

### C) Decide on USB‑C / nPM1300 current-limit behavior (so you don’t get “mystery brownouts”)

Because your main board leaves `CC1/CC2` unused, Nordic notes:

* CC pins may be left floating or tied to ground if USB Type‑C config isn’t used, **but**
* the **default VBUS current limit stays 100 mA** until the host config is set. 

Action:

* Make sure your firmware (main MCU or adapter MCU over I2C) sets the VBUS current limit appropriately early during bring-up if you expect >100 mA.

### D) Then move to PCB layout

Once schematic is clean:

1. **Set board outline** (18.6 mm circle) and decide stackup (2L vs 4L).
2. **Place HJ module at the edge** and implement its antenna guidance (keepout/clearance + PI network close). 
3. Place **PMIC + inductors + caps** tightly (small switching loops).
4. Place **NAND close to MCU**, keep CLK short, keep the series resistor near the driver.
5. Place **mic + acoustic hole** and keep it away from switching inductors/RF.
6. Add **ground stitching** and enforce the antenna keepout (including inner planes if 4-layer).

### E) Manufacturing prep (before you hit “order”)

* Confirm your DNP parts remain excluded from assembly outputs (antenna caps, PDM bias resistor).
* If you’re using **0201 passives**, note that JLC commonly flags 0201 as **Standard PCBA only / fixture needed** (not “Economic”).
  If you want cheaper assembly, convert as many passives as possible to 0402.

---

If you want, I can also give you a **very specific “layout placement order”** (what goes down first, where to put the HJ antenna edge relative to the circle, which parts can go under the module footprint, etc.), but the two schematic fixes above are the gating items before layout.

[1]: https://www.longsto.com/product/72-en.html "SD NAND Test Board"
[2]: https://archive.org/stream/ebytecdebytedl0719/627_E73_Usermanual_EN_v1.30_djvu.txt "Full text of \"Ebyte / cdebyte site downloads copy (07 2019)\""
