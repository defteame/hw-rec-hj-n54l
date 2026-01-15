"""
BOM Exploder Script for PCBWay Assembly

Converts atopile's grouped BOM format (where designators are comma-separated)
into an assembly-friendly format with one designator per row.

Usage:
    python scripts/explode_bom.py

Output:
    build/builds/main/main.bom.exploded.csv
"""

import csv
from pathlib import Path

IN = Path("build/builds/main/main.bom.csv")
OUT = Path("build/builds/main/main.bom.exploded.csv")

def explode_bom():
    if not IN.exists():
        print(f"Error: Input file {IN} not found. Run 'ato build' first.")
        return False

    with IN.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("Error: BOM file is empty.")
        return False

    # Get field names from input, ensure we have the key fields
    input_fields = list(rows[0].keys())

    # Define output fields (PCBWay-friendly ordering)
    out_fields = ["Designator", "Footprint", "Quantity", "Value", "Manufacturer", "Partnumber", "LCSC Part #"]

    # Add any additional fields from input that we want to preserve
    for field in input_fields:
        if field not in out_fields and field.lower() not in [f.lower() for f in out_fields]:
            out_fields.append(field)

    exploded = []
    for r in rows:
        # Handle both "Designator" and "Designators" column names
        designator_col = "Designator" if "Designator" in r else "Designators" if "Designators" in r else None
        if not designator_col:
            print(f"Warning: No designator column found in row: {r}")
            continue

        # Split designators (handle various formats: "C1,C2,C3" or "C1, C2, C3")
        designators = [d.strip() for d in r.get(designator_col, "").split(",") if d.strip()]

        for d in designators:
            nr = {}
            # Copy all fields, normalizing column names
            for field in out_fields:
                # Try exact match first
                if field in r:
                    nr[field] = r[field]
                # Try case-insensitive match
                elif field.lower() in [k.lower() for k in r.keys()]:
                    for k, v in r.items():
                        if k.lower() == field.lower():
                            nr[field] = v
                            break
                else:
                    nr[field] = ""

            nr["Designator"] = d
            nr["Quantity"] = "1"
            exploded.append(nr)

    # Create output directory if needed
    OUT.parent.mkdir(parents=True, exist_ok=True)

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(exploded)

    print(f"Wrote {OUT} with {len(exploded)} rows (from {len(rows)} grouped entries)")
    return True


if __name__ == "__main__":
    import sys
    sys.exit(0 if explode_bom() else 1)
