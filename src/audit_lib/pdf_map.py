from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# Author-like prefix may contain spaces, underscores, and hyphens (multi-word surnames, particles, corporate names)
_BASENAME_RE = re.compile(r"^([A-Za-z][A-Za-z _-]*)_(\d{4})\b.*\.pdf$", re.IGNORECASE)


def _strip_diacritics(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _normalize_quotes_dashes(s: str) -> str:
    # normalize curly quotes and various dashes
    return (
        (s or "")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201C", '"')
        .replace("\u201D", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )


def normalize_lead_surname(name: str) -> str:
    """Normalize a citation/institution name to a lead-surname key.

    Rules:
    - Extract the first personal surname (ignore "et al.").
    - Lowercase, strip diacritics, drop non-letters.
    - For institutional/corporate authors, use the first alphanumeric token.
    """
    if not name:
        return ""
    s = _normalize_quotes_dashes(str(name))
    s = _strip_diacritics(s).strip()
    # remove typical joiners and parentheses content; drop 'et al.'
    s = re.sub(r"\bet\.?\s*al\.?\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[\(\)\[\]\{\}<>]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # take first chunk before 'and' or '&' or comma
    first = re.split(r",|\band\b|&", s, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    # strip possessive on narrative (Kirkhart's -> Kirkhart)
    first = re.sub(r"([A-Za-z\-])(?:['’]s)\b", r"\1", first)
    # drop any trailing apostrophe
    first = re.sub(r"['’]$", "", first)
    # tokens preserving hyphens inside tokens
    raw_tokens = [t for t in re.split(r"\s+", first) if t]
    tokens: List[str] = []
    for t in raw_tokens:
        # remove punctuation except letters and hyphen
        t2 = re.sub(r"[^A-Za-z\-]", "", t)
        if t2:
            tokens.append(t2)
    if not tokens:
        return ""
    parts = {"van", "von", "de", "den", "der", "del", "la", "le", "da"}
    key_tokens: List[str] = []
    if tokens[0].lower() in parts:
        key_tokens.append(tokens[0])
        if len(tokens) >= 2:
            key_tokens.append(tokens[1])
        if len(tokens) >= 3 and tokens[1].lower() in {"den", "der", "de"}:
            key_tokens.append(tokens[2])
    else:
        # Include up to two tokens to support multi-word surnames like 'Ripoll Lorenzo'
        key_tokens.append(tokens[0])
        if len(tokens) >= 2:
            key_tokens.append(tokens[1])
    # build key: lowercase, join with underscores; treat hyphen and space equivalently as separators
    key = "_".join(t.lower().replace("-", "_") for t in key_tokens if t)
    key = re.sub(r"_+", "_", key).strip("_")
    return key


def _norm_file_surname(raw: str) -> str:
    # Normalize author-like prefix from filename: keep sequence of words connected by '_' or '-' as underscores
    s = _normalize_quotes_dashes(_strip_diacritics(raw or "").strip())
    s = s.replace(" ", "_").replace("-", "_")
    s = re.sub(r"[^A-Za-z_]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.lower().strip("_")


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


def _author_key_from_text_fragment(citation_text: str, year: int) -> str:
    if not citation_text or not year:
        return ""
    s = _normalize_quotes_dashes(_strip_diacritics(str(citation_text)))
    # split on semicolons for multi-cite
    parts = [p.strip() for p in re.split(r";", s) if p.strip()]
    y = str(year)
    for p in parts or [s]:
        if y in p:
            head = p.split(y, 1)[0]
            # common pattern: 'Author(s), 2017' -> trim trailing comma/space
            head = re.sub(r"[,\s]+$", "", head)
            return normalize_lead_surname(head)
    return ""


def resolve_source_pdf(author: str, year: int, index: Dict[Tuple[str, int], List[Path]], citation_text: Optional[str] = None) -> ResolveResult:
    """Resolve a source PDF path via exact (surname_key, year) match.

    - No cross-year fallback.
    - Deterministic tie-break rules.
    """
    surname_key = normalize_lead_surname(author)
    if not surname_key or not year:
        return ResolveResult(path=None, candidates=[], reason="no_match")
    candidates = list(index.get((surname_key, int(year)), []))
    # If no candidates and we have citation_text, try to parse the phrase for particles (e.g., 'van Wingerden')
    if not candidates and citation_text:
        alt_key = _author_key_from_text_fragment(citation_text, int(year))
        if alt_key and alt_key != surname_key:
            candidates = list(index.get((alt_key, int(year)), []))
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
