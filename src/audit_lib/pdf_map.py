from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

_BASENAME_RE = re.compile(r"^([A-Za-z]+)_(\d{4})\b.*\.pdf$", re.IGNORECASE)


def _strip_diacritics(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def normalize_lead_surname(name: str) -> str:
    """Normalize a citation/institution name to a lead-surname key.

    Rules:
    - Extract the first personal surname (ignore "et al.").
    - Lowercase, strip diacritics, drop non-letters.
    - For institutional/corporate authors, use the first alphanumeric token.
    """
    if not name:
        return ""
    s = _strip_diacritics(str(name)).strip()
    # remove typical joiners and parentheses content; drop 'et al.'
    s = re.sub(r"\bet\.?\s*al\.?\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[\(\)\[\]\{\}<>]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # take first chunk before 'and' or '&' or comma
    first = re.split(r",|\band\b|&", s, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    # pick the last token (surname) for personal names; for institutions, the first token is fine too
    tokens = [t for t in re.split(r"\s+", first) if t]
    candidate = tokens[-1] if tokens else first
    # remove any non-letters
    candidate = re.sub(r"[^A-Za-z]", "", candidate)
    return candidate.lower()


def _norm_file_surname(raw: str) -> str:
    # Apply the same normalization as normalize_lead_surname but input is already a filename prefix
    return normalize_lead_surname(raw)


def build_pdf_index(pdf_dir: Path) -> Dict[Tuple[str, int], List[Path]]:
    """Scan ``pdf_dir`` and build an index keyed by (surname_key, year).

    - Matches files whose basename satisfies: ^([A-Za-z]+)_(\d{4})\b.*\.pdf$
    - The captured surname is normalized like ``normalize_lead_surname``.
    - Returns mapping to a list of candidate paths for deterministic tie-breaking later.
    """
    index: Dict[Tuple[str, int], List[Path]] = {}
    if not pdf_dir or not pdf_dir.exists():
        return index
    for p in sorted(pdf_dir.glob("*.pdf")):
        m = _BASENAME_RE.match(p.name)
        if not m:
            continue
        surname_raw, year_str = m.group(1), m.group(2)
        key = (_norm_file_surname(surname_raw), int(year_str))
        index.setdefault(key, []).append(p)
    return index


@dataclass
class ResolveResult:
    path: Optional[Path]
    candidates: List[Path]
    reason: Optional[str] = None  # None, 'no_match', or 'ambiguous'


def _tie_break(surname_key: str, year: int, candidates: List[Path]) -> Path:
    # 1) Prefer exact base "<Surname>_<Year>.pdf" (case-insensitive), no extra tokens
    exact = f"{surname_key}_{year}.pdf"
    for p in candidates:
        if p.name.lower() == exact.lower():
            return p
    # 2) Shortest basename length
    cands_sorted = sorted(candidates, key=lambda x: (len(x.name), x.name.lower()))
    # 3) If tie persists, lexicographically smallest (covered by sort key)
    return cands_sorted[0]


def resolve_source_pdf(author: str, year: int, index: Dict[Tuple[str, int], List[Path]]) -> ResolveResult:
    """Resolve a source PDF path via exact (surname_key, year) match.

    - No cross-year fallback.
    - Deterministic tie-break rules.
    """
    surname_key = normalize_lead_surname(author)
    if not surname_key or not year:
        return ResolveResult(path=None, candidates=[], reason="no_match")
    candidates = list(index.get((surname_key, int(year)), []))
    if not candidates:
        return ResolveResult(path=None, candidates=[], reason="no_match")
    if len(candidates) == 1:
        return ResolveResult(path=candidates[0], candidates=candidates, reason=None)
    chosen = _tie_break(surname_key, int(year), candidates)
    return ResolveResult(path=chosen, candidates=candidates, reason="ambiguous")


def write_warnings(rows: Iterable[dict], out_path: Path) -> None:
    """Write warnings CSV with columns:
    review_id,claim_id,chosen_author,chosen_year,candidates,json_candidates,reason
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "review_id",
        "claim_id",
        "chosen_author",
        "chosen_year",
        "candidates",
        "json_candidates",
        "reason",
    ]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


__all__ = [
    "normalize_lead_surname",
    "build_pdf_index",
    "resolve_source_pdf",
    "ResolveResult",
    "write_warnings",
]

