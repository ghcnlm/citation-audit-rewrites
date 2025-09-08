import pandas as pd
import yaml
from pathlib import Path

CONFIG = yaml.safe_load(open("config/config.yaml","r",encoding="utf-8"))
OUT_DIR = Path(CONFIG["paths"]["outputs_dir"])

ADJ = OUT_DIR/"adjudications.csv"
DASH = OUT_DIR/"summary_dashboard.csv"

def main():
    if not ADJ.exists():
        print("No adjudications.csv found.")
        return
    df = pd.read_csv(ADJ)
    counts = df["verdict"].value_counts().rename_axis("verdict").reset_index(name="count")
    by_review = df.groupby(["review_id","verdict"]).size().reset_index(name="count")
    by_section = df.groupby(["review_id","section","verdict"]).size().reset_index(name="count")

    counts["level"] = "overall"
    by_review["level"] = "review"
    by_section["level"] = "section"
    out = pd.concat([counts, by_review, by_section], ignore_index=True)
    out.to_csv(DASH, index=False)
    print(f"[OK] wrote dashboard -> {DASH}")

if __name__ == "__main__":
    main()
