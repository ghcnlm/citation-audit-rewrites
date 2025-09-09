# scripts/80_generate_corrections.py
"""
Canonical corrections builder (replaces any legacy logic that read adjudications.csv).

Input:  outputs/adjudications_with_rewrites.csv
Output: outputs/corrections_list.csv with schema:
        review_id,section,claim_id,action_type,proposed_text,notes
"""
from pathlib import Path
import pandas as pd
import yaml

CONFIG = yaml.safe_load(open("config/config.yaml", "r", encoding="utf-8"))
OUT_DIR = Path(CONFIG["paths"]["outputs_dir"])

ADJ_WR = OUT_DIR / "adjudications_with_rewrites.csv"
CORR = OUT_DIR / "corrections_list.csv"

BAD_VERDICTS = {"UNSUPPORTED_FAIL", "AMBIGUOUS_REVIEW"}

def main():
    if not ADJ_WR.exists():
        print("No adjudications_with_rewrites.csv found.")
        return

    df = pd.read_csv(ADJ_WR, dtype=str).fillna("")
    # Keep rows that either explicitly failed/ambiguous OR proposed some fix/rewrite
    mask = (
        df["verdict"].isin(BAD_VERDICTS)
        | (df["required_fix"].str.len() > 0)
        | (df["proposed_rewrite"].str.len() > 0)
    )
    df_bad = df[mask].copy()

    rows = []
    for _, r in df_bad.iterrows():
        rows.append(
            {
                "review_id": r.get("review_id", ""),
                "section": r.get("section", ""),
                "claim_id": r.get("claim_id", ""),
                "action_type": "edit_or_remove",  # stable action label
                "proposed_text": r.get("proposed_rewrite", "") or r.get("required_fix", "") or "",
                "notes": r.get("rationale", "") or "",
            }
        )

    pd.DataFrame(rows, columns=[
        "review_id","section","claim_id","action_type","proposed_text","notes"
    ]).to_csv(CORR, index=False)
    print(f"[OK] wrote corrections list -> {CORR} (rows={len(rows)})")

if __name__ == "__main__":
    main()
