#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
90_build_corrections_list.py
Build a corrections list from adjudications_with_rewrites.csv.

Output:
  - outputs/corrections_list.csv
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
OUT_DIR = Path(CONFIG["paths"]["outputs_dir"])

WR   = OUT_DIR / "adjudications_with_rewrites.csv"
CORR = OUT_DIR / "corrections_list.csv"

BAD_VERDICTS = {"UNSUPPORTED_FAIL", "AMBIGUOUS_REVIEW", "PARTIAL_PASS", "SUPPORTED_PASS_WITH_FIX"}

def main():
    if not WR.exists():
        print(f"Missing {WR}. Run 50_adjudicate.py first.")
        return

    df = pd.read_csv(WR, dtype=str).fillna("")
    if df.empty:
        print("No adjudications to process.")
        return

    # include if verdict is bad OR a fix/rewrite exists
    need = (
        df["verdict"].isin(BAD_VERDICTS) |
        (df["required_fix"].str.len() > 0) |
        (df["proposed_rewrite"].str.len() > 0)
    )
    rows = []
    for _, r in df[need].iterrows():
        action = "edit_or_remove" if r.get("verdict","") in {"UNSUPPORTED_FAIL","AMBIGUOUS_REVIEW"} else "edit"
        proposed = r.get("proposed_rewrite","") or r.get("required_fix","") or ""
        rows.append({
            "review_id": r["review_id"],
            "section": r["section"],
            "claim_id": r["claim_id"],
            "action_type": action,
            "proposed_text": proposed,
            "notes": r.get("rationale",""),
        })

    out = pd.DataFrame(rows)
    out.to_csv(CORR, index=False, encoding="utf-8")
    print(f"[OK] corrections_list.csv -> {CORR} ({len(out)} rows)")

if __name__ == "__main__":
    main()
