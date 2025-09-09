from typing import Any, Dict, List
from rapidfuzz import fuzz, process
import re
def chunk_pages_to_windows(pages: Dict[int,str], chunk_words=180, stride=90) -> List[Dict[str,Any]]:
    chunks = []
    for pno, text in pages.items():
        words = re.split(r"\s+", text.strip())
        if not words:
            continue
        for i in range(0, max(1, len(words)-chunk_words+1), stride):
            piece = " ".join(words[i:i+chunk_words])
            chunks.append({
                "page_start": pno,
                "page_end": pno,
                "text": piece
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
