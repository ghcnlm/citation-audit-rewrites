from typing import Any, Dict, List
from rapidfuzz import fuzz, process
import re


def chunk_pages_to_windows(
    pages: Dict[int, str],
    chunk_words: int = 180,
    stride: int = 90,
    cross_page: bool = False,
) -> List[Dict[str, Any]]:
    """Create fixed-size word windows from page texts.

    - Per-page mode (default): windows are created independently for each page.
    - Cross-page mode: windows slide across concatenated pages; page_start/page_end
      reflect the min/max page indices covered by the window.
    """
    chunks: List[Dict[str, Any]] = []

    # Normalize and sort pages by page number to ensure stable order.
    items = sorted(pages.items(), key=lambda kv: int(kv[0]))

    if not cross_page:
        for pno, text in items:
            words = re.split(r"\s+", text.strip()) if text else []
            if not words:
                continue
            for i in range(0, max(1, len(words) - chunk_words + 1), stride):
                piece = " ".join(words[i : i + chunk_words])
                chunks.append({
                    "page_start": int(pno),
                    "page_end": int(pno),
                    "text": piece,
                })
        return chunks

    # Cross-page windows: build a token stream with page mapping
    tokens: List[str] = []
    token_pages: List[int] = []
    for pno, text in items:
        words = re.split(r"\s+", text.strip()) if text else []
        if not words:
            continue
        tokens.extend(words)
        token_pages.extend([int(pno)] * len(words))

    if not tokens:
        return chunks

    total = len(tokens)
    for i in range(0, max(1, total - chunk_words + 1), stride):
        sl = slice(i, i + chunk_words)
        piece_tokens = tokens[sl]
        piece = " ".join(piece_tokens)
        pages_in_window = token_pages[sl]
        p_start = min(pages_in_window)
        p_end = max(pages_in_window)
        chunks.append({
            "page_start": p_start,
            "page_end": p_end,
            "text": piece,
        })
    return chunks


def top_k_chunks_for_claim(
    claim: str, chunks: List[Dict[str, Any]], k: int = 5
) -> List[Dict[str, Any]]:
    """Return the best matching text chunks for a claim.

    Parameters
    ----------
    claim: str
        The statement to match against the corpus.
    chunks: List[Dict[str, Any]]
        Candidate text chunks produced by :func:`chunk_pages_to_windows`.
    k: int, optional
        Number of results to return. Must be positive.

    Returns
    -------
    List[Dict[str, Any]]
        A list of the top ``k`` chunks with ``page_range``, ``text`` and
        ``score`` keys.

    Raises
    ------
    ValueError
        If ``k`` is non-positive.
    """

    if k <= 0:
        raise ValueError("k must be positive")

    corpus = [c["text"] for c in chunks]
    ranked = process.extract(claim, corpus, scorer=fuzz.token_set_ratio, limit=k)
    results: List[Dict[str, Any]] = []
    for (_, score, idx) in ranked:
        c = chunks[idx]
        results.append({
            "page_range": f"{c['page_start']}" if c['page_start']==c['page_end'] else f"{c['page_start']}-{c['page_end']}",
            "text": c["text"],
            "score": int(score)
        })
    return results
