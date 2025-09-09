#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
50_adjudicate.py  —  Merge decisions into a single working CSV.

Inputs:
  - outputs/ccp_registry_enriched.csv               (scaffold)
  - outputs/adjudications.csv                       (legacy or LLM-generated decisions)

Output:
  - outputs/adjudications_with_rewrites.csv         (working table for downstream steps)

Notes:
  * This hot fix makes merge counts accurate (no false positives from NaNs).
  * It is resilient to duplicate keys and partial/empty legacy fields.
  * It writes any keys found in legacy but not in the scaffold to:
        outputs/.staging/legacy_unmatched_after_merge.csv
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import pandas as pd
import yaml
import sys
import os

# ---------------------------
# Config / Paths
# ---------------------------

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))

OUT_DIR = Path(CONFIG["paths"]["outputs_dir"])
OUT_DIR.mkdir(parents=True, exist_ok=True)
STAGING_DIR = OUT_DIR / ".staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

ENRICHED_CSV = OUT_DIR / "ccp_registry_enriched.csv"
LEGACY_ADJ_CSV = OUT_DIR / "adjudications.csv"
WR_OUT = OUT_DIR / "adjudications_with_rewrites.csv"

BASE_COLS = [
    "review_id", "section", "claim_id",
    "claim_text",
    "citation_author", "citation_year",
    "source_pdf_path",
]
DECISION_COLS = [
    "verdict", "rationale", "evidence_span",
    "required_fix", "risk_flags", "page_anchor",
]
REWRITE_COLS = [
    "proposed_rewrite", "rewrite_notes", "rewrite_flags",
]

ALL_COLS = BASE_COLS + DECISION_COLS + REWRITE_COLS


# ---------------------------
# Helpers
# ---------------------------

def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def _ensure_columns(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Ensure all columns exist (with empty string) and return with those columns first if present."""
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    # preserve order for the requested cols, then any extras at the end
    ordered = [c for c in cols if c in df.columns] + [c for c in df.columns if c not in cols]
    return df.loc[:, ordered]


def _scaffold_from_enriched(enriched: pd.DataFrame) -> pd.DataFrame:
    if enriched.empty:
        print(f"[ERR] Missing or empty {ENRICHED_CSV}.")
        sys.exit(2)
    # only take the columns we need if they exist
    have = [c for c in BASE_COLS if c in enriched.columns]
    left = enriched.loc[:, have].copy()
    # add decision & rewrite columns blank
    for c in DECISION_COLS + REWRITE_COLS:
        if c not in left.columns:
            left[c] = ""
    # ensure string, no NaN
    left = left.astype(str).fillna("")
    return _ensure_columns(left, ALL_COLS)


def _dedupe_by_key(df: pd.DataFrame, key_cols: List[str]) -> pd.DataFrame:
    if df.empty:
        return df
    # Keep the first occurrence for each key triple
    return df.drop_duplicates(subset=key_cols, keep="first")


def merge_fill(left: pd.DataFrame, right: pd.DataFrame, on_cols: List[str], stage_name: str) -> tuple[pd.DataFrame, Dict[str, int]]:
    """
    Fill blanks in `left[DECISION_COLS]` from `right[DECISION_COLS]` by keys `on_cols`.
    Accurate counts; NaNs treated as empty; duplicates handled.
    """
    if right.empty:
        return left, {c: 0 for c in DECISION_COLS}

    # Reduce right to the minimal columns we need (and any base cols we might want to backfill)
    keep_cols = list({*on_cols, *DECISION_COLS, "source_pdf_path"})
    keep_cols = [c for c in keep_cols if c in right.columns]
    r = right.loc[:, keep_cols].copy().astype(str).fillna("")
    r = _dedupe_by_key(r, on_cols)

    merged = left.merge(r, how="left", on=on_cols, suffixes=("", "_r"))

    counts: Dict[str, int] = {}
    for c in DECISION_COLS:
        before_blank = merged[c].fillna("").astype(str).str.len() == 0
        candidate = merged.get(f"{c}_r", "")
        candidate = pd.Series(candidate).reindex(merged.index).fillna("").astype(str)

        merged.loc[before_blank, c] = candidate[before_blank]
        filled_now = int((before_blank & (merged[c].fillna("").astype(str).str.len() > 0)).sum())
        counts[c] = filled_now

        rcol = f"{c}_r"
        if rcol in merged.columns:
            merged = merged.drop(columns=[rcol])

    # opportunistically fill source_pdf_path if it's blank on the left but present on the right
    if "source_pdf_path_r" in merged.columns:
        before_blank = merged["source_pdf_path"].fillna("").astype(str).str.len() == 0
        candidate = merged["source_pdf_path_r"].fillna("").astype(str)
        merged.loc[before_blank, "source_pdf_path"] = candidate[before_blank]
        merged = merged.drop(columns=["source_pdf_path_r"])

    print(f"[MERGE {stage_name}] " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return merged, counts


def _write_unmatched_keys(right: pd.DataFrame, left_keys: pd.DataFrame, on_cols: List[str]) -> None:
    """Write keys present in right but not in left scaffold (helps detect section/key inconsistencies)."""
    if right.empty:
        return
    rk = right.loc[:, [c for c in on_cols if c in right.columns]].copy()
    lk = left_keys.loc[:, [c for c in on_cols if c in left_keys.columns]].copy()
    rk = rk.astype(str).fillna("")
    lk = lk.astype(str).fillna("")
    tmp = rk.merge(lk.drop_duplicates(), how="left", on=on_cols, indicator=True)
    unmatched = tmp[tmp["_merge"] == "left_only"].drop(columns=["_merge"])
    if not unmatched.empty:
        outp = STAGING_DIR / "legacy_unmatched_after_merge.csv"
        unmatched.to_csv(outp, index=False, encoding="utf-8")
        print(f"[DEBUG] Unmatched legacy keys written → {outp}")


# ---------------------------
# Main
# ---------------------------

def main():
    # 1) Load scaffold
    enriched = _read_csv(ENRICHED_CSV)
    left = _scaffold_from_enriched(enriched)
    left = _ensure_columns(left, ALL_COLS)
    print(f"[INFO] Scaffold rows: {len(left)}")

    # 2) Load legacy decisions (or LLM-generated adjudications.csv)
    legacy = _read_csv(LEGACY_ADJ_CSV)
    if legacy.empty:
        print(f"[WARN] {LEGACY_ADJ_CSV} missing or empty. No decisions to merge.")
    else:
        legacy = _ensure_columns(legacy, BASE_COLS + DECISION_COLS)
        # strictly ensure key types
        for c in ["review_id", "section", "claim_id"]:
            legacy[c] = legacy[c].astype(str).fillna("")
            left[c] = left[c].astype(str).fillna("")

        # 3) Merge-fill decisions
        on = ["review_id", "section", "claim_id"]
        left, _ = merge_fill(left, legacy, on_cols=on, stage_name="K=review_id+section+claim_id")

        # 4) Report any keys in legacy not present in scaffold (debugging)
        _write_unmatched_keys(legacy, left[on], on_cols=on)

    # 5) Normalize and write
    left = left.fillna("")  # hot-fix: ensure blanks are true blanks
    left = _ensure_columns(left, ALL_COLS)

    # Decision-blank rows (for honest reporting)
    blanks = (
        (left["verdict"].astype(str).str.len() == 0) &
        (left["required_fix"].astype(str).str.len() == 0) &
        (left["proposed_rewrite"].astype(str).str.len() == 0)
    )
    left.to_csv(WR_OUT, index=False, encoding="utf-8")
    print(f"[OK] wrote {WR_OUT} | rows={len(left)} | decision-blank rows={int(blanks.sum())}")


if __name__ == "__main__":
    main()
