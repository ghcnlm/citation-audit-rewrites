# scripts/fix_source_pdf_mappings.py
# -*- coding: utf-8 -*-
"""
Recompute source_pdf_path in outputs/ccp_registry_enriched.csv using exact (surname, year) mapping.

Usage:
  python scripts/fix_source_pdf_mappings.py [--inplace]

Writes:
  - outputs/ccp_registry_enriched_FIXED.csv (unless --inplace)
  - outputs/source_pdf_warnings.csv
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from audit_lib.pdf_map import (
    build_pdf_index,
    resolve_source_pdf,
    write_warnings,
)


REPO_ROOT = Path.cwd()
DEFAULT_IN = REPO_ROOT / "outputs" / "ccp_registry_enriched.csv"
DEFAULT_OUT = REPO_ROOT / "outputs" / "ccp_registry_enriched_FIXED.csv"
PDF_DIR = REPO_ROOT / "pilot_inputs" / "sources_pdf"
WARNINGS_CSV = REPO_ROOT / "outputs" / "source_pdf_warnings.csv"


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _truthy(v) -> bool:
    s = str(v).strip().lower()
    return s in ("true", "1", "yes", "y", "t")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inplace", action="store_true", help="Overwrite inputs/ccp_registry_enriched.csv in place")
    args = ap.parse_args()

    rows = _read_csv(DEFAULT_IN)
    index = build_pdf_index(PDF_DIR)

    warn_rows: List[Dict[str, str]] = []
    out_rows: List[Dict[str, str]] = []

    for r in rows:
        out = dict(r)
        existing = (out.get("source_pdf_path") or "").strip()

        # Select author/year per rules
        is_secondary = _truthy(out.get("is_secondary", ""))
        pm_auth = (out.get("primary_mentioned_author") or "").strip()
        pm_year = (out.get("primary_mentioned_year") or "").strip()
        cit_auth = (out.get("citation_author") or "").strip()
        cit_year = (out.get("citation_year") or "").strip()

        if is_secondary and pm_auth and pm_year:
            chosen_author = pm_auth
            try:
                chosen_year = int(pm_year[:4])
            except Exception:
                chosen_year = None
        else:
            chosen_author = cit_auth
            try:
                chosen_year = int(cit_year[:4])
            except Exception:
                chosen_year = None

        resolved_path: Optional[Path] = None
        reason: Optional[str] = None
        candidates: List[Path] = []  # type: ignore[name-defined]

        if chosen_author and chosen_year:
            res = resolve_source_pdf(chosen_author, chosen_year, index, citation_text=out.get("citation_text",""))
            resolved_path = res.path
            reason = res.reason
            candidates = res.candidates

        if resolved_path:
            try:
                rel = resolved_path.relative_to(REPO_ROOT)
                out["source_pdf_path"] = str(rel).replace("\\", "/")
            except Exception:
                out["source_pdf_path"] = str(resolved_path).replace("\\", "/")
        else:
            # No exact match: leave blank (no cross-year fallback)
            out["source_pdf_path"] = ""
            if chosen_author and chosen_year:
                reason = reason or "no_match"

        if reason in ("ambiguous", "no_match"):
            warn_rows.append({
                "review_id": out.get("review_id", ""),
                "claim_id": out.get("claim_id", ""),
                "chosen_author": chosen_author or "",
                "chosen_year": str(chosen_year or ""),
                "candidates": ";".join(sorted(p.name for p in candidates)) if candidates else "",
                "json_candidates": __import__("json").dumps([str(p) for p in candidates], ensure_ascii=False),
                "reason": reason or "",
            })

        out_rows.append(out)

    if warn_rows:
        write_warnings(warn_rows, WARNINGS_CSV)

    out_path = DEFAULT_IN if args.inplace else DEFAULT_OUT
    fieldnames = list(rows[0].keys()) if rows else []
    _write_csv(out_path, out_rows, fieldnames)
    print(f"[OK] wrote: {out_path}")
    if warn_rows:
        print(f"[WARN] wrote warnings: {WARNINGS_CSV} ({len(warn_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
