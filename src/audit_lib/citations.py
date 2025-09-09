import re
from typing import List

from .models import Citation


# Basic building blocks
PAREN_BLOCK_RE = re.compile(r"\(([^()]+)\)")
PAIR_RE = re.compile(r"([A-Z][^,;()]+?)\s*,\s*(\d{4}[a-z]?)")

# Support unicode apostrophe and hyphen; allow one- or two-author narrative; and "et al."
NARR_RE = re.compile(
    r"\b([A-Z][A-Za-z'’\-]+(?:\s+(?:&|and)\s+[A-Z][A-Za-z'’\-]+)?(?:\s+et al\.)?)\s*\(\s*(\d{4}[a-z]?)\s*\)"
)
AS_CITED_IN_RE = re.compile(r"\bas cited in\s+([A-Z][^,;()]+?)\s*,\s*(\d{4}[a-z]?)", re.I)

# Allow p./pp. with optional ranges using -, – or —
PAGE_RE = re.compile(r"\bp{1,2}\.\s*(\d+(?:\s*[-–—]\s*\d+)?)", re.I)


def _extract_parenthetical_pairs(sentence: str) -> List[Citation]:
    out: List[Citation] = []
    for m in PAREN_BLOCK_RE.finditer(sentence):
        block = m.group(1)
        span = (m.start(), m.end())
        as_cited = AS_CITED_IN_RE.search(block)

        stated_page = None
        page_m = PAGE_RE.search(block)
        if page_m:
            stated_page = page_m.group(1).strip()

        if as_cited:
            host_author, host_year = as_cited.groups()
            # Capture the primary mentioned citation before "as cited in" if present
            before = block.split(as_cited.group(0))[0]
            primary_pairs = PAIR_RE.findall(before)
            p_author, p_year = (primary_pairs[0] if primary_pairs else (None, None))
            out.append(
                Citation(
                    citation_text=f"({block})",
                    citation_type="secondary_parenthetical",
                    author=host_author.strip(),
                    year=host_year.strip(),
                    is_secondary=True,
                    primary_mentioned_author=p_author.strip() if p_author else None,
                    primary_mentioned_year=p_year.strip() if p_year else None,
                    stated_page=stated_page,
                    span=span,
                )
            )
            continue

        for a, y in PAIR_RE.findall(block):
            out.append(
                Citation(
                    citation_text=f"({block})",
                    citation_type="parenthetical",
                    author=a.strip(),
                    year=y.strip(),
                    is_secondary=False,
                    primary_mentioned_author=None,
                    primary_mentioned_year=None,
                    stated_page=stated_page,
                    span=span,
                )
            )
    return out


def _extract_narrative_pairs(sentence: str) -> List[Citation]:
    out: List[Citation] = []
    for m in NARR_RE.finditer(sentence):
        a, y = m.groups()
        span = (m.start(), m.end())
        tail = sentence[m.end():]
        as_cited = AS_CITED_IN_RE.search(tail)

        stated_page = None
        page_m = PAGE_RE.search(sentence[m.end():]) or PAGE_RE.search(sentence[:m.start()])
        if page_m:
            stated_page = page_m.group(1).strip()

        if as_cited:
            host_author, host_year = as_cited.groups()
            out.append(
                Citation(
                    citation_text=sentence[m.start():m.end()] + ", as cited in " + as_cited.group(0),
                    citation_type="secondary_narrative",
                    author=host_author.strip(),
                    year=host_year.strip(),
                    is_secondary=True,
                    primary_mentioned_author=a.strip(),
                    primary_mentioned_year=y.strip(),
                    stated_page=stated_page,
                    span=span,
                )
            )
        else:
            out.append(
                Citation(
                    citation_text=sentence[m.start():m.end()],
                    citation_type="narrative",
                    author=a.strip(),
                    year=y.strip(),
                    is_secondary=False,
                    primary_mentioned_author=None,
                    primary_mentioned_year=None,
                    stated_page=stated_page,
                    span=span,
                )
            )
    return out


def parse_citations(sentence: str) -> List[Citation]:
    parenth = _extract_parenthetical_pairs(sentence)
    narr = _extract_narrative_pairs(sentence)
    seen = set()
    out: List[Citation] = []
    for item in parenth + narr:
        key = (item.author, item.year, item.citation_type, item.span)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out

