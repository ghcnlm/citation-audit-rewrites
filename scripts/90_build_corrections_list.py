# scripts/90_build_corrections_list.py
# Canonical builder for corrections_list.csv from adjudications_with_rewrites.csv.
# Schema: review_id,section,claim_id,action_type,proposed_text,notes

from __future__ import annotations

import csv
from pathlib import Path
import pandas as pd
from audit_lib.paths import load_adjudications

def main():
    df = load_adjudications()  # loads outputs/adjudications_with_rewrites.csv
    if df.empty:
        print("No adjudications_with_rewrites.csv data to build corrections.")
        return

    out_rows = []
    for _, r in df.iterrows():
        rid = str(r.get("review_id", "") or "").strip()
        sec = str(r.get("section", "") or "").strip()
        cid = str(r.get("claim_id", "") or "").strip()

        req = str(r.get("required_fix", "") or "").strip()
        if req:
            out_rows.append({
                "review_id": rid,
                "section": sec,
                "claim_id": cid,
                "action_type": "required_fix",
                "proposed_text": req,
                "notes": str(r.get("rationale", "") or "")
            })

        rew = str(r.get("proposed_rewrite", "") or "").strip()
        if rew:
            out_rows.append({
                "review_id": rid,
                "section": sec,
                "claim_id": cid,
                "action_type": "proposed_rewrite",
                "proposed_text": rew,
                "notes": str(r.get("rewrite_notes", "") or "")
            })

    out = pd.DataFrame(out_rows, columns=[
        "review_id","section","claim_id","action_type","proposed_text","notes"
    ])
    out_path = Path("outputs") / "corrections_list.csv"
    out.to_csv(out_path, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"[OK] corrections_list.csv -> {out_path} ({len(out)} rows)")

if __name__ == "__main__":
    main()
