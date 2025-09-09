# verify_all.py
from pathlib import Path
import pandas as pd

out = Path("outputs")
cand = [out/"ccp_registry_enriched.csv", out/"ccp_registry_enriched_FIXED.csv"]
enr_path = next((p for p in cand if p.exists()), None)

def load(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)

def show(label, path, cols=None):
    if not path or not path.exists():
        print(f"{label}: MISSING -> {path}")
        return None
    df = load(path)
    print(f"{label}: {path} -> rows={len(df)}")
    if cols:
        missing = [c for c in cols if c not in df.columns]
        if missing:
            print(f"  Missing cols: {missing}")
    return df

print("== Enriched registry ==")
enr = show("enriched", enr_path, cols=[
    "review_id","section","claim_id","claim_text","citation_author","citation_year","source_pdf_path"
])

print("\n== Adjudications with rewrites ==")
adj_path = out/"adjudications_with_rewrites.csv"
adj = show("adjudications_with_rewrites", adj_path, cols=[
    "review_id","section","claim_id","claim_text","citation_author","citation_year","source_pdf_path",
    "verdict","rationale","evidence_span","required_fix","risk_flags",
    "proposed_rewrite","page_anchor","rewrite_notes","rewrite_flags"
])

print("\n== Corrections list ==")
corr_path = out/"corrections_list.csv"
corr = show("corrections_list", corr_path, cols=[
    "review_id","section","claim_id","action_type","proposed_text","notes"
])

if enr is not None and adj is not None:
    ek = set(enr[['review_id','section','claim_id']].apply(tuple, axis=1))
    ak = set(adj[['review_id','section','claim_id']].apply(tuple, axis=1))
    print("\n== Cross-check ==")
    print("Same keys (review_id,section,claim_id):", ek == ak)
    print("Counts — enriched vs adjudications:", len(enr), len(adj))
