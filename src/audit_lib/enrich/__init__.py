from __future__ import annotations
from pathlib import Path
import json
from typing import List, Dict, Tuple, Optional
import csv

from .docx_sections import load_docx_sections
from .section_scoring import best_section_for_claim
from pathlib import Path
from .pdf_match import build_pdf_index as _legacy_build_pdf_index, resolve_pdf_path as _legacy_resolve_pdf_path
from audit_lib.pdf_map import (
    build_pdf_index as build_exact_pdf_index,
    resolve_source_pdf,
    write_warnings as write_pdf_warnings,
)


def enrich_registry_rows(raw_rows: List[dict], reviews_dir: Path, pdf_dir: Optional[Path] = None) -> List[dict]:
    """Enrich registry rows with section info and resolved PDF paths."""
    doc_cache: Dict[str, Tuple[str, List[Dict]]] = {}
    # Build exact-match index if pdf_dir provided, else fall back to legacy in case
    exact_index = build_exact_pdf_index(pdf_dir) if pdf_dir else {}
    legacy_index: List[Dict] = _legacy_build_pdf_index(pdf_dir) if (pdf_dir and not exact_index) else []
    warn_rows: List[Dict] = []

    enriched: List[dict] = []
    for r in raw_rows:
        rid = r.get("review_id", "")
        claim_text = r.get("claim_text", "") or ""

        if rid not in doc_cache:
            docx_path = reviews_dir / f"{rid}.docx"
            rq, sections = load_docx_sections(docx_path)
            sections = [s for s in sections if s.get("level") in (2, 3, 4) or (s.get("level") == 1 and s.get("body"))]
            doc_cache[rid] = (rq, sections)

        rq, sections = doc_cache[rid]

        if sections:
            section_title, section_canonical, section_level = best_section_for_claim(claim_text, sections)
        else:
            section_title, section_canonical, section_level = ("unknown", "unknown", "")

        out = dict(r)
        out["section_canonical"] = section_canonical
        out["section_level"] = section_level
        out["research_question"] = rq
        out["section_title"] = section_title

        existing = (out.get("source_pdf_path") or "").strip()
        if (not existing) and (exact_index or legacy_index):
            # Decide target author/year per rules
            is_secondary_raw = str(out.get("is_secondary", "")).strip().lower()
            is_secondary = is_secondary_raw in ("true", "1", "yes", "y", "t") or is_secondary_raw is True

            pm_auth = (out.get("primary_mentioned_author") or "").strip()
            pm_year = out.get("primary_mentioned_year")
            cit_auth = (out.get("citation_author") or "").strip()
            cit_year = out.get("citation_year")

            chosen_author = None
            chosen_year: Optional[int] = None

            if is_secondary and pm_auth and pm_year not in (None, ""):
                chosen_author = pm_auth
                try:
                    chosen_year = int(str(pm_year).strip()[:4])
                except Exception:
                    chosen_year = None
            else:
                chosen_author = cit_auth
                try:
                    chosen_year = int(str(cit_year).strip()[:4])
                except Exception:
                    chosen_year = None

            resolved_path: Optional[Path] = None
            reason: Optional[str] = None
            candidates: List[Path] = []

            if chosen_author and chosen_year and exact_index:
                res = resolve_source_pdf(
                    chosen_author,
                    chosen_year,
                    exact_index,
                    citation_text=out.get("citation_text", ""),
                )
                resolved_path = res.path
                reason = res.reason
                candidates = res.candidates
            elif legacy_index:
                # Fallback to legacy heuristic only if exact index empty (should be rare)
                m = _legacy_resolve_pdf_path(out, legacy_index)
                resolved_path = m
                reason = None
                candidates = [m] if m else []

            if resolved_path:
                try:
                    rel = resolved_path.relative_to(Path.cwd())
                    out["source_pdf_path"] = str(rel).replace("\\", "/")
                except Exception:
                    out["source_pdf_path"] = str(resolved_path).replace("\\", "/")
            else:
                # leave blank; log warning if we attempted exact resolution
                if chosen_author and chosen_year and (exact_index):
                    reason = reason or "no_match"
                else:
                    reason = None

            # Collect warnings for ambiguous/no_match cases
            if reason in ("ambiguous", "no_match"):
                warn_rows.append({
                    "review_id": out.get("review_id", ""),
                    "claim_id": out.get("claim_id", ""),
                    "chosen_author": str(chosen_author or ""),
                    "chosen_year": str(chosen_year or ""),
                    "candidates": ";".join(sorted(p.name for p in candidates)) if candidates else "",
                    "json_candidates": json.dumps([str(p) for p in candidates], ensure_ascii=False),
                    "reason": reason,
                })
        else:
            if existing:
                out["source_pdf_path"] = existing.replace("\\", "/")
        enriched.append(out)
    # Best-effort: write warnings CSV to outputs folder if we produced any
    if warn_rows:
        try:
            warnings_path = Path("outputs") / "source_pdf_warnings.csv"
            write_pdf_warnings(warn_rows, warnings_path)
        except Exception:
            pass
    return enriched


def _write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_enriched_csv(enriched_rows: List[dict], out_path: Path) -> None:
    """Write enriched rows to CSV preserving original columns."""
    if not enriched_rows:
        _write_csv(out_path, [], [])
        return
    base_cols = list(enriched_rows[0].keys())
    # Remove obsolete 'section' column from outputs
    if "section" in base_cols:
        base_cols.remove("section")
    for c in ["section_canonical", "section_level", "research_question", "section_title"]:
        if c in base_cols:
            base_cols.remove(c)
    fieldnames = base_cols + ["section_canonical", "section_level", "research_question", "section_title"]
    _write_csv(out_path, enriched_rows, fieldnames)


def _best_section_for_claim(claim_text: str, sections: List[Dict]) -> tuple[str, str, int | str]:
    """Backwards-compatible alias expected by tests.

    Returns (section_title, canonical_title, level).
    """
    return best_section_for_claim(claim_text, sections)


__all__ = [
    "enrich_registry_rows",
    "write_enriched_csv",
    "_best_section_for_claim",
]
