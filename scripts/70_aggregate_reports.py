#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
70_aggregate_reports.py
Aggregate adjudication results for dashboarding.

Output:
  - outputs/summary_dashboard.csv
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
OUT_DIR = Path(CONFIG["paths"]["outputs_dir"])

WR = OUT_DIR / "adjudications_with_rewrites.csv"
DASH = OUT_DIR / "summary_dashboard.csv"

def main():
    if not WR.exists():
        print(f"Missing {WR}. Run 50_adjudicate.py first.")
        return

    df = pd.read_csv(WR, dtype=str).fillna("")
    if df.empty:
        print("No rows in adjudications_with_rewrites.csv")
        return

    counts = df["verdict"].value_counts(dropna=False).rename_axis("verdict").reset_index(name="count")
    by_review = df.groupby(["review_id","verdict"]).size().reset_index(name="count")
    # 'section' removed from pipeline; drop section-level aggregation

    counts["level"] = "overall"
    by_review["level"] = "review"
    out = pd.concat([counts, by_review], ignore_index=True)
    out.to_csv(DASH, index=False, encoding="utf-8")
    print(f"[OK] wrote dashboard -> {DASH}")

if __name__ == "__main__":
    main()
