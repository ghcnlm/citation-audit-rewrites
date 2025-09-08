# scripts/11_extract_and_enrich_SHIM.py
# -*- coding: utf-8 -*-
"""
Temporary shim: read outputs/ccp_registry.csv, enrich it, write ONLY outputs/ccp_registry_enriched.csv.
Use this until your extractor is refactored to return rows in memory.
"""
import csv, yaml
from pathlib import Path
from typing import List, Dict

from audit_lib.enrich import enrich_registry_rows, write_enriched_csv

CFG = yaml.safe_load(open("config/config.yaml","r",encoding="utf-8"))
OUT_DIR = Path(CFG["paths"]["outputs_dir"])
REVIEWS_DIR = Path(CFG["paths"]["reviews_dir"])

RAW_CSV = OUT_DIR / "ccp_registry.csv"
ENRICHED_CSV = OUT_DIR / "ccp_registry_enriched.csv"

def _read_csv(path: Path) -> List[Dict[str,str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def main():
    if not RAW_CSV.exists():
        raise SystemExit(f"ERROR: {RAW_CSV} not found. Run your extractor once to produce it, then re-run this shim.")
    rows = _read_csv(RAW_CSV)
    enriched = enrich_registry_rows(rows, REVIEWS_DIR)
    write_enriched_csv(enriched, ENRICHED_CSV)
    print(f"[OK] wrote enriched registry -> {ENRICHED_CSV}")

if __name__ == "__main__":
    main()
