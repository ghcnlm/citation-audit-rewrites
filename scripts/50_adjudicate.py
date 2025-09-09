# scripts/50_adjudicate.py
# Create/refresh adjudications_with_rewrites.csv for ALL rows in enriched registry.
# Never drop rows. Preserve existing adjudications when merging on keys.

from __future__ import annotations
import csv
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"

CANONICAL_ORDER = [
    "review_id","section","claim_id","claim_text",
    "citation_author","citation_year","source_pdf_path",
    "verdict","rationale","evidence_span","required_fix","risk_flags",
    "proposed_rewrite","page_anchor","rewrite_notes","rewrite_flags"
]

# Columns that must exist in enriched source (besides many others)
ENRICH_KEYS = [
    "review_id","section","claim_id","claim_text",
    "citation_author","citation_year","source_pdf_path"
]

def _find_enriched() -> Path:
    candidates = [
        OUT / "ccp_registry_enriched.csv",
        OUT / "ccp_registry_enriched_FIXED.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    # as a fallback: search anywhere under outputs for either name
    for p in OUT.glob("**/ccp_registry_enriched*.csv"):
        return p
    raise FileNotFoundError("Could not locate enriched registry in outputs/.")

def _ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    for col in ENRICH_KEYS:
        if col not in df.columns:
            df[col] = ""
    return df

def _load_existing() -> pd.DataFrame:
    path = OUT / "adjudications_with_rewrites.csv"
    if path.exists():
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        # ensure expected columns exist
        for c in CANONICAL_ORDER:
            if c not in df.columns:
                df[c] = ""
        return df[CANONICAL_ORDER]
    else:
        return pd.DataFrame(columns=CANONICAL_ORDER)

def _canonicalize_types(df: pd.DataFrame) -> pd.DataFrame:
    # Treat everything as string to avoid dtype merge issues
    return df.astype(str)

def main():
    OUT.mkdir(exist_ok=True)
    enr_path = _find_enriched()
    enr = pd.read_csv(enr_path, dtype=str, keep_default_na=False)
    enr = _ensure_cols(enr)

    # base (1 row per claim) with adjudication fields empty
    base = enr[ENRICH_KEYS].copy()
    base["verdict"] = ""            # to be filled by a reviewer/LLM step
    base["rationale"] = ""
    base["evidence_span"] = ""
    base["required_fix"] = ""
    base["risk_flags"] = ""
    base["proposed_rewrite"] = ""
    base["page_anchor"] = ""
    base["rewrite_notes"] = ""
    base["rewrite_flags"] = ""

    base = _canonicalize_types(base)
    base = base[CANONICAL_ORDER]

    # merge with any existing adjudications (preserve existing non-empty annotations)
    prev = _load_existing()
    if not prev.empty:
        key = ["review_id","section","claim_id"]
        merged = base.merge(prev, on=key, how="left", suffixes=("", "_prev"))

        def coalesce(row, col):
            return row[col] if row[col] else row.get(f"{col}_prev","")

        for col in CANONICAL_ORDER:
            if col in ["review_id","section","claim_id"]:
                continue
            merged[col] = merged.apply(lambda r, c=col: coalesce(r, c), axis=1)

        # drop *_prev helper columns
        keep = CANONICAL_ORDER
        merged = merged[keep]
        out = merged
    else:
        out = base

    # final ordering + write
    out = out[CANONICAL_ORDER]
    out.to_csv(OUT / "adjudications_with_rewrites.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"[OK] adjudications_with_rewrites.csv -> {len(out)} rows (1 per enriched claim).")

if __name__ == "__main__":
    main()