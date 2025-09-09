from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional
import re
import string

PUNCT_TABLE_SP = str.maketrans({c: " " for c in string.punctuation})
YEAR_RE = re.compile(r"\b(19|20)\d{2}[a-z]?\b", re.IGNORECASE)


def norm_pdf_stem(name: str) -> str:
    s = (name or "")
    s = s.replace("-", "_")
    s = s.replace("&", " and ")
    s = s.translate(PUNCT_TABLE_SP)
    s = re.sub(r"[^a-zA-Z0-9_ ]+", " ", s)
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace(" ", "_")
    s = re.sub(r"_+", "_", s)
    return s


def extract_year(s: str) -> Optional[str]:
    m = YEAR_RE.search(s or "")
    return m.group(0).lower() if m else None


def strip_et_al(s: str) -> str:
    return re.sub(r"\bet\.?\s*al\.?\b", "", s or "", flags=re.IGNORECASE)


def primary_author_from_citation_author(cit_author: str) -> str:
    a = strip_et_al(cit_author or "")
    a = a.replace("&", " and ")
    a = re.sub(r"[\(\)\[\]\{\},.;:]", " ", a)
    a = re.sub(r"\s+", " ", a).strip()
    first_piece = re.split(r"\band\b|,|\u2013|\u2014|–|—", a, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    base = first_piece.lower().replace("-", "_").replace("’", "").replace("'", "")
    base = re.sub(r"\s+", "_", base).strip("_")
    if not base:
        return ""
    return base


def author_variants(author: str) -> List[str]:
    a = strip_et_al(author or "")
    a = a.replace("&", " and ")
    a = re.sub(r"[\(\)\[\]\{\},.;:]", " ", a)
    a = re.sub(r"\s+", " ", a).strip()
    first = re.split(r"\band\b|,|\u2013|\u2014|–|—", a, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    tokens = first.split()
    surname = tokens[-1] if tokens else first
    base = first.lower()
    base = base.replace("-", "_").replace("’", "").replace("'", "")
    base = re.sub(r"\s+", "_", base).strip("_")
    variants = {base}
    if surname:
        s = surname.lower().replace("-", "_").replace("’", "").replace("'", "")
        s = re.sub(r"\s+", "_", s)
        variants.add(s)
    more = set()
    for v in list(variants):
        more.add(v.replace("_", ""))
    variants |= more
    prefixes = {"de", "van", "von", "da", "del", "di"}
    if "_" in base:
        parts = base.split("_")
        if parts[0] in prefixes and len(parts) > 1:
            variants.add("_".join(parts[1:]))
            variants.add("".join(parts[1:]))
    return [v for v in variants if v]


def mine_authors_from_citation_text(citation_text: str) -> List[str]:
    if not citation_text:
        return []
    txt = strip_et_al(citation_text)
    txt = txt.replace("&", " and ")
    txt = re.sub(r"[\(\)]", " ", txt)
    year = extract_year(txt)
    if year:
        head = txt.split(year, 1)[0]
    else:
        head = txt
    chunks = re.split(r",|\band\b", head, flags=re.IGNORECASE)
    authors = []
    for c in chunks:
        c = norm_pdf_stem(c)
        c = c.strip("_ ")
        if not c:
            continue
        parts = c.split("_")
        if len(parts) == 1:
            authors.append(parts[0])
        else:
            authors.append(parts[-1])
            authors.append(c)
    out = set()
    for a in authors:
        out.add(a)
        out.add(a.replace("_", ""))
    return [x for x in out if x]


def split_multi_citation_parts(citation_text: str) -> List[str]:
    if not citation_text:
        return []
    t = citation_text.strip()
    t = t[1:-1] if t.startswith("(") and t.endswith(")") else t
    parts = [p.strip() for p in t.split(";")]
    return [p for p in parts if p]


def year_base(y: Optional[str]) -> Optional[str]:
    if not y:
        return None
    m = re.match(r"^((?:19|20)\d{2})", y.lower())
    return m.group(1) if m else y.lower()


def build_pdf_index(pdf_dir: Path) -> List[Dict]:
    items: List[Dict] = []
    if not pdf_dir or not pdf_dir.exists():
        return items
    for p in pdf_dir.glob("*.pdf"):
        stem = p.stem
        stem_norm = norm_pdf_stem(stem)
        items.append({
            "path": p,
            "stem_norm": stem_norm,
            "year": extract_year(stem_norm),
        })
    return items


def score_pdf_match(
    *,
    stem_norm: str,
    year: Optional[str],
    author_variants: List[str],
    want_year: Optional[str],
    primary_variant: Optional[str] = None,
) -> int:
    score = 0
    stem_year_base = year_base(year)
    want_year_base = year_base(want_year)

    if want_year_base and stem_year_base:
        if want_year_base == stem_year_base:
            score += 10
        else:
            return -999

    if primary_variant:
        if re.search(rf"(?:^|_){re.escape(primary_variant)}(?:_|$)", stem_norm):
            score += 4
        elif primary_variant in stem_norm:
            score += 2

    for v in author_variants:
        if not v:
            continue
        if primary_variant and v == primary_variant:
            continue
        if re.search(rf"(?:^|_){re.escape(v)}(?:_|$)", stem_norm):
            score += 2
        elif v in stem_norm:
            score += 1

    return score


def infer_year_for_target_author(citation_author: str, citation_text: str) -> Optional[str]:
    if not citation_text:
        return None
    primary = primary_author_from_citation_author(citation_author)
    if not primary:
        return None
    primary_variants = {primary, primary.replace("_", "")}
    parts = split_multi_citation_parts(citation_text)
    for part in parts:
        pn = norm_pdf_stem(part)
        if any(re.search(rf"(?:^|_){re.escape(v)}(?:_|$)", pn) for v in primary_variants):
            y = extract_year(pn)
            if y:
                return y
    return extract_year(citation_text)


def resolve_pdf_path(row: Dict[str, str], pdf_index: List[Dict]) -> Optional[Path]:
    cit_author = (row.get("citation_author") or "").strip()
    cit_text = (row.get("citation_text") or "").strip()
    cit_year = (str(row.get("citation_year") or "").strip() or None)

    primary_variant = primary_author_from_citation_author(cit_author)
    variants: List[str] = []
    if cit_author:
        variants += author_variants(cit_author)
    if cit_text:
        variants += mine_authors_from_citation_text(cit_text)

    pm_author = (row.get("primary_mentioned_author") or "").strip()
    pm_year = (str(row.get("primary_mentioned_year") or "").strip() or None)
    if pm_author:
        variants += author_variants(pm_author)

    seen = set()
    uniq_variants: List[str] = []
    for v in sorted(set(variants), key=lambda x: (-len(x), x)):
        if v not in seen:
            uniq_variants.append(v)
            seen.add(v)

    want_year = cit_year
    inferred = infer_year_for_target_author(cit_author, cit_text)
    if inferred:
        want_year = inferred
    elif not want_year:
        want_year = pm_year or extract_year(cit_text)

    best_score = -10**9
    best_item: Optional[Dict] = None
    for item in pdf_index:
        s = item["stem_norm"]
        y = item["year"]
        score = score_pdf_match(
            stem_norm=s,
            year=y,
            author_variants=uniq_variants,
            want_year=want_year,
            primary_variant=primary_variant if primary_variant else None,
        )
        if score > best_score:
            best_score = score
            best_item = item

    if best_item and best_score >= 2:
        return best_item["path"]
    return None
