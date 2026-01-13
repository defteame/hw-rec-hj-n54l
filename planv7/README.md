# hw-rec-hj-n54l — Current Surfaced Artifacts

This bundle contains EVERYTHING that has been completed so far.
No future planning is included here.

## Included
- placement_main_v1.csv
    Latest validated main-board placement (LED removed).
- keepouts_main_v1.md
    Text definition of RF, mic, and switching keepouts.
- scripts/validate_fit.py
    Python script used to validate placement against circular outline.

## Notes
- LED subsystem has been fully removed.
- Passive footprint reduction (0402) is assumed but not yet reflected
  in KiCad files.
- KiCad PCB file has NOT been rewritten yet; placements are authoritative
  via CSV.
- HJ-N54L footprint mismatch and mic NPTH fix are identified but not
  yet implemented in files.

This represents the full, honest current state.