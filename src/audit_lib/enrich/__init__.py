from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import csv

from .docx_sections import load_docx_sections
from .section_scoring import best_section_for_claim
from .pdf_match import build_pdf_index, resolve_pdf_path


def enrich_registry_rows(raw_rows: List[dict], reviews_dir: Path, pdf_dir: Optional[Path] = None) -> List[dict]:
    """Enrich registry rows with section info and resolved PDF paths."""
    doc_cache: Dict[str, Tuple[str, List[Dict]]] = {}
    pdf_index: List[Dict] = build_pdf_index(pdf_dir) if pdf_dir else []

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
        if (not existing) and pdf_index:
            m = resolve_pdf_path(out, pdf_index)
            if m:
                try:
                    rel = m.relative_to(Path.cwd())
                    out["source_pdf_path"] = str(rel).replace("\\", "/")
                except Exception:
                    out["source_pdf_path"] = str(m).replace("\\", "/")
        else:
            if existing:
                out["source_pdf_path"] = existing.replace("\\", "/")
        enriched.append(out)
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
    for c in ["section_canonical", "section_level", "research_question", "section_title"]:
        if c in base_cols:
            base_cols.remove(c)
    fieldnames = base_cols + ["section_canonical", "section_level", "research_question", "section_title"]
    _write_csv(out_path, enriched_rows, fieldnames)


__all__ = ["enrich_registry_rows", "write_enriched_csv"]
