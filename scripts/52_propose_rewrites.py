# scripts/52_propose_rewrites.py
# Non-dropping rewrite pass. Only fills rewrite fields for UNSUPPORTED_FAIL,
# preserving row count == enriched row count.

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

def main():
    path = OUT / "adjudications_with_rewrites.csv"
    if not path.exists():
        raise FileNotFoundError("Expected adjudications_with_rewrites.csv in outputs/. Run 50_adjudicate.py first.")

    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    # Only propose rewrites for UNSUPPORTED_FAIL; do NOT drop other rows
    mask = df["verdict"].str.upper().eq("UNSUPPORTED_FAIL")

    # If your prompt/LLM logic exists elsewhere, integrate here.
    # For now, auto-fill a conservative scaffold when required_fix is present.
    def propose(row):
        if row.get("proposed_rewrite"):
            return row["proposed_rewrite"]
        if row.get("required_fix"):
            # simple placeholder – keeps pipeline lossless
            return f"[REWRITE NEEDED] {row['required_fix']}"
        return row.get("proposed_rewrite","")

    df.loc[mask, "proposed_rewrite"] = df.loc[mask].apply(propose, axis=1)
    # page_anchor/rewrite_notes/flags left as-is (user/LLM may fill later)

    # Reorder + write back
    for col in CANONICAL_ORDER:
        if col not in df.columns:
            df[col] = ""
    df = df[CANONICAL_ORDER]
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"[OK] rewrites merged into adjudications_with_rewrites.csv (rows preserved = {len(df)}).")

if __name__ == "__main__":
    main()