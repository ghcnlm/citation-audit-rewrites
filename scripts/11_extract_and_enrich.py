# scripts/11_extract_and_enrich.py
# -*- coding: utf-8 -*-
"""
Final direct-output path: run CCP extraction in-memory, then enrich and write ONLY outputs/ccp_registry_enriched.csv.
Refactor your extractor so extract_raw_rows() returns a list[dict] in the same schema your old ccp_registry.csv used.
"""
import yaml
from pathlib import Path
from typing import List, Dict

from audit_lib.enrich import enrich_registry_rows, write_enriched_csv

CFG = yaml.safe_load(open("config/config.yaml","r",encoding="utf-8"))
OUT_DIR = Path(CFG["paths"]["outputs_dir"])
REVIEWS_DIR = Path(CFG["paths"]["reviews_dir"])

def extract_raw_rows() -> List[Dict[str,str]]:
    """
    TODO: Replace this stub with a call to your current extraction logic that returns rows in memory.
    Must return rows with columns:
      review_id, section, claim_id, claim_text, is_quote, has_numbers, is_causal_or_normative,
      citation_text, citation_type, citation_author, citation_year, is_secondary,
      primary_mentioned_author, primary_mentioned_year, stated_page, in_reference_list,
      source_pdf_path, priority
    """
    raise NotImplementedError("Wire this to your extraction routine so it returns a list[dict].")

def main():
    rows = extract_raw_rows()
    enriched = enrich_registry_rows(rows, REVIEWS_DIR)
    out_csv = OUT_DIR / "ccp_registry_enriched.csv"
    write_enriched_csv(enriched, out_csv)
    print(f"[OK] wrote enriched registry -> {out_csv}")

if __name__ == "__main__":
    main()