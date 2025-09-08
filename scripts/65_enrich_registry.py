# scripts/65_enrich_registry.py
# -*- coding: utf-8 -*-
from pathlib import Path
import sys, csv
from audit_lib.enrich import enrich_registry_rows, write_enriched_csv

def _read_csv(path: Path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def main():
    if len(sys.argv) < 5:
        print("Usage: python scripts/65_enrich_registry.py <in_csv> <reviews_dir> <out_csv> <qa_dir>")
        sys.exit(2)
    in_csv = Path(sys.argv[1]); reviews_dir = Path(sys.argv[2]); out_csv = Path(sys.argv[3])
    rows = _read_csv(in_csv)
    enriched = enrich_registry_rows(rows, reviews_dir)
    write_enriched_csv(enriched, out_csv)
    print(f"[OK] wrote enriched registry -> {out_csv}")

if __name__ == "__main__":
    main()
