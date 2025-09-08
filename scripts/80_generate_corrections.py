import pandas as pd
import yaml
from pathlib import Path

CONFIG = yaml.safe_load(open("config/config.yaml","r",encoding="utf-8"))
OUT_DIR = Path(CONFIG["paths"]["outputs_dir"])

ADJ = OUT_DIR/"adjudications.csv"
CORR = OUT_DIR/"corrections_list.csv"

def main():
    if not ADJ.exists():
        print("No adjudications.csv found.")
        return
    df = pd.read_csv(ADJ)
    df_bad = df[df["verdict"].isin(["UNSUPPORTED_FAIL","AMBIGUOUS_REVIEW"])].copy()
    rows = []
    for _, r in df_bad.iterrows():
        rows.append({
            "review_id": r["review_id"],
            "section": r["section"],
            "claim_id": r["claim_id"],
            "action_type": "edit_or_remove",
            "proposed_text": r.get("required_fix","") or "",
            "notes": r.get("rationale","")
        })
    pd.DataFrame(rows).to_csv(CORR, index=False)
    print(f"[OK] wrote corrections list -> {CORR}")

if __name__ == "__main__":
    main()
