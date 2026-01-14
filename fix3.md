That “extra” **middle pad** you’re seeing on the package drawing is real, but for this SD NAND family it’s **not part of the functional 8‑pin SD/SPI interface**.

* The **CSNP64GCR01 pin assignment table defines only 8 pins** (SDD2, CD/SDD3, SCLK, VSS, CMD, SDD0, SDD1, VCC) and does **not** assign any electrical function to a 9th/center pad. ([LCSC Datasheet][1])
* The vendor application/test-board instructions explicitly call this out: **“The middle PIN should remain untinned and left as NC (No Connection).”** ([Longsto][2])

## What you should do on your PCB footprint

### Best-practice, low-risk option (what I’d do)

1. **Include the center pad in the footprint as a “mechanical / NC” pad**

   * Name it something unambiguous like **“NC_CENTER”**, **“PAD9_NC”**, or **“MECH”**.
   * **Do not connect it to any net** in schematic/PCB (leave it “no net” / “NC”).
2. **Remove it from the solder paste layer**

   * I.e., **no paste opening** for that pad (paste ratio 0%, or “F.Paste/B.Paste disabled” depending on tool).
   * This matches the vendor guidance to keep it “untinned” and avoids the risk of the package “floating” on a center solder bump and starving the edge pads.
3. **Solder mask handling**

   * Either is usually fine:

     * **Mask opening ON** (pad exposed copper but no paste), or
     * **Mask opening OFF** (covered by solder mask)
   * If you’re unsure, pick **mask opening ON + no paste**: it keeps the footprint aligned with the package metal but won’t introduce extra solder volume.

### What I would NOT do (unless you have a strong reason)

* **Don’t pour solder paste on it by default.**
  Even if it’s NC electrically, solder there can change standoff height and reduce edge-pad solder quality.
* **Don’t tie it to GND “just because”.**
  Since the vendor calls it NC, assume it’s not guaranteed internally connected and treat it as non-functional. ([Longsto][2])

## Quick decision rule

* If your current footprint **already has** that center pad → **keep it, but disable paste and leave unconnected**.
* If your current footprint **doesn’t have** that center pad → you can still ship a prototype, but I’d update it to match the mechanical drawing and the vendor’s own “middle pin NC” handling (because it avoids future surprises and matches their adapter board guidance). ([Longsto][2])

If you want, paste (or upload) the **current CSNP64GCR01 footprint definition** you’re using (pads + paste/mask settings), and I’ll tell you *exactly* what to change (pad name, dimensions strategy, paste/mask flags) to make it match the above with minimal churn.

[1]: https://datasheet.lcsc.com/lcsc/2410121516_CS-Semiconductor-CSNP64GCR01-AOW_C5365291.pdf "SD NAND Memory (CSNP64GCR01-AOW )"
[2]: https://www.longsto.com/product/72-en.html "SD NAND Test Board"
