#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
60_sampling_plan.py
Make a sampling plan from adjudications_with_rewrites.csv and enriched registry.

Output:
  - outputs/sampling_plan.csv
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
OUT_DIR = Path(CONFIG["paths"]["outputs_dir"])

WR = OUT_DIR / "adjudications_with_rewrites.csv"
EN = OUT_DIR / "ccp_registry_enriched.csv"
PLAN = OUT_DIR / "sampling_plan.csv"

LOW_SAMPLE_FRACTION = 0.3
FAIL_REVIEW_ESCALATE_THRESHOLD = 0.05
BAD_VERDICTS = {"UNSUPPORTED_FAIL", "AMBIGUOUS_REVIEW"}

def main():
    wr = pd.read_csv(WR, dtype=str).fillna("")
    en = pd.read_csv(EN, dtype=str).fillna("") if EN.exists() else pd.DataFrame()

    # priority from enriched preferred; fallback to High
    pri = en[["review_id","section","claim_id","priority"]].copy() if not en.empty else pd.DataFrame()
    if pri.empty:
        wr["priority"] = "High"
    else:
        wr = wr.merge(pri, how="left", on=["review_id","section","claim_id"])
        wr["priority"] = wr["priority"].replace("", "High")

    # compute bad rate by (review_id, section)
    wr["_is_bad"] = wr["verdict"].isin(BAD_VERDICTS)
    rates = wr.groupby(["review_id","section"])["_is_bad"].mean().reset_index().rename(columns={"_is_bad": "bad_rate"})

    plan_rows = []
    for (rid, sec), group in wr.groupby(["review_id","section"]):
        high = group[group["priority"] == "High"]
        low  = group[group["priority"] == "Low"]

        # sample 30% of low (min 10 if enough)
        n_sample = max(10, int(len(low) * LOW_SAMPLE_FRACTION)) if len(low) > 0 else 0
        low_sample = low.sample(n=min(n_sample, len(low)), random_state=42) if n_sample > 0 else low.iloc[0:0]

        bad_rate = rates[(rates["review_id"]==rid) & (rates["section"]==sec)]["bad_rate"]
        escalate = bool((not bad_rate.empty) and (bad_rate.values[0] > FAIL_REVIEW_ESCALATE_THRESHOLD))

        include = pd.concat([high, low_sample], ignore_index=True)
        include["escalate_to_full_section"] = escalate

        for _, r in include.iterrows():
            plan_rows.append({
                "review_id": rid,
                "section": sec,
                "claim_id": r["claim_id"],
                "priority": r["priority"],
                "escalate_to_full_section": escalate
            })

    pd.DataFrame(plan_rows).to_csv(PLAN, index=False, encoding="utf-8")
    print(f"[OK] wrote sampling plan -> {PLAN}")

if __name__ == "__main__":
    main()
