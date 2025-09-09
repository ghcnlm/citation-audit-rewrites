from audit_lib.retrieval import chunk_pages_to_windows, top_k_chunks_for_claim


def test_top_k_chunks_for_claim_ranks_relevant_chunks():
    pages = {
        1: "the quick brown fox",
        2: "jumps over the lazy dog",
    }
    chunks = chunk_pages_to_windows(pages)
    claim = "lazy dog"
    results = top_k_chunks_for_claim(claim, chunks, k=1)
    assert results[0]["page_range"] == "2"
    assert results[0]["score"] >= 0
