# scripts/70_aggregate_reports.py
from __future__ import annotations

import pandas as pd
import yaml
from pathlib import Path
from audit_lib.paths import load_adjudications  # NEW central loader

CONFIG = yaml.safe_load(open("config/config.yaml", "r", encoding="utf-8"))
OUT_DIR = Path(CONFIG["paths"]["outputs_dir"])

DASH = OUT_DIR / "summary_dashboard.csv"

def main():
    df = load_adjudications()  # adjudications_with_rewrites.csv
    if df.empty:
        print("No adjudications_with_rewrites.csv data.")
        return

    counts = df["verdict"].value_counts(dropna=False).rename_axis("verdict").reset_index(name="count")
    by_review = df.groupby(["review_id", "verdict"], dropna=False).size().reset_index(name="count")
    by_section = df.groupby(["review_id", "section", "verdict"], dropna=False).size().reset_index(name="count")

    counts["level"] = "overall"
    by_review["level"] = "review"
    by_section["level"] = "section"
    out = pd.concat([counts, by_review, by_section], ignore_index=True)

    out.to_csv(DASH, index=False)
    print(f"[OK] wrote dashboard -> {DASH}")

if __name__ == "__main__":
    main()
