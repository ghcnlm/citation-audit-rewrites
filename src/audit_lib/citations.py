import re
from typing import Any, Dict, List

PAREN_BLOCK_RE = re.compile(r"\(([^()]+)\)")
PAIR_RE = re.compile(r"([A-Z][^,;()]+?)\s*,\s*(\d{4}[a-z]?)")
NARR_RE = re.compile(r"\b([A-Z][A-Za-z'’\-]+(?:\s+(?:&|and)\s+[A-Z][A-Za-z'’\-]+)?(?:\s+et al\.)?)\s*\(\s*(\d{4}[a-z]?)\s*\)")
AS_CITED_IN_RE = re.compile(r"\bas cited in\s+([A-Z][^,;()]+?)\s*,\s*(\d{4}[a-z]?)", re.I)
PAGE_RE = re.compile(r"\bpp?\.\s*(\d+(?:\s*[-–]\s*\d+)?)", re.I)

def _extract_parenthetical_pairs(sentence: str) -> List[Dict[str, Any]]:
    """Extract parenthetical citation information from a sentence.

    Parameters
    ----------
    sentence: str
        Sentence potentially containing parenthetical citations.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries describing each citation found. The list is
        empty when no citations are present.

    Notes
    -----
    No exceptions are raised; invalid input types will result in a
    ``TypeError`` from the underlying regex operations.
    """

    out: List[Dict[str, Any]] = []
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
            out.append({
                "citation_text": "(" + block + ")",
                "citation_type": "secondary_parenthetical",
                "author": host_author.strip(),
                "year": host_year.strip(),
                "is_secondary": True,
                "primary_mentioned_author": None,
                "primary_mentioned_year": None,
                "stated_page": stated_page,
                "span": span,
            })
            continue
        for a, y in PAIR_RE.findall(block):
            out.append({
                "citation_text": "(" + block + ")",
                "citation_type": "parenthetical",
                "author": a.strip(),
                "year": y.strip(),
                "is_secondary": False,
                "primary_mentioned_author": None,
                "primary_mentioned_year": None,
                "stated_page": stated_page,
                "span": span,
            })
    return out

def _extract_narrative_pairs(sentence: str) -> List[Dict[str, Any]]:
    """Extract narrative citation information from a sentence.

    Parameters
    ----------
    sentence: str
        Sentence potentially containing narrative citations.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries describing each citation found. The list is
        empty when no citations are present.

    Notes
    -----
    No exceptions are raised; invalid input types will result in a
    ``TypeError`` from the underlying regex operations.
    """

    out: List[Dict[str, Any]] = []
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
            out.append({
                "citation_text": sentence[m.start():m.end()] + ", as cited in " + as_cited.group(0),
                "citation_type": "secondary_narrative",
                "author": host_author.strip(),
                "year": host_year.strip(),
                "is_secondary": True,
                "primary_mentioned_author": a.strip(),
                "primary_mentioned_year": y.strip(),
                "stated_page": stated_page,
                "span": span,
            })
        else:
            out.append({
                "citation_text": sentence[m.start():m.end()],
                "citation_type": "narrative",
                "author": a.strip(),
                "year": y.strip(),
                "is_secondary": False,
                "primary_mentioned_author": None,
                "primary_mentioned_year": None,
                "stated_page": stated_page,
                "span": span,
            })
    return out

def parse_citations(sentence: str) -> List[Dict[str, Any]]:
    """Parse all citation forms within a sentence.

    Parameters
    ----------
    sentence: str
        Sentence containing potential parenthetical or narrative citations.

    Returns
    -------
    List[Dict[str, Any]]
        A list of unique citation dictionaries extracted from the sentence.

    Notes
    -----
    No exceptions are raised; invalid input types will result in a
    ``TypeError`` from the underlying regex operations.
    """

    parenth = _extract_parenthetical_pairs(sentence)
    narr = _extract_narrative_pairs(sentence)
    seen = set()
    out: List[Dict[str, Any]] = []
    for item in parenth + narr:
        key = (item["author"], item["year"], item["citation_type"], item["span"])
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out
