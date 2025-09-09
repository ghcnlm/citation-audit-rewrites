# scripts/40_retrieve_candidates.py
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd
import yaml

from audit_lib.pdf_utils import split_pages
from audit_lib.retrieval import chunk_pages_to_windows, top_k_chunks_for_claim

CONFIG = yaml.safe_load(open("config/config.yaml", "r", encoding="utf-8"))

TEXT_DIR: Path = Path(CONFIG["paths"]["sources_text_dir"])
OUT_DIR: Path = Path(CONFIG["paths"]["outputs_dir"])

CHUNK_W = int(CONFIG["retrieval"]["chunk_words"])
STRIDE = int(CONFIG["retrieval"]["chunk_stride"])
TOPK = int(CONFIG["retrieval"]["top_k"])

ENRICHED = OUT_DIR / "ccp_registry_enriched.csv"
ENRICHED_FIXED = OUT_DIR / "ccp_registry_enriched_FIXED.csv"
OFFSETS = OUT_DIR / "page_offsets.csv"
CANDIDATES_JSONL = OUT_DIR / "adjudication_inputs.jsonl"

TRUEY = {"1", "true", "t", "y", "yes"}


def as_bool(val) -> bool:
    s = str(val).strip().lower()
    return s in TRUEY or (isinstance(val, (int, float)) and bool(val))


def normalize_quotes(s: str) -> str:
    return (
        s.replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("‘", "'")
    )


def _pick_enriched() -> Optional[Path]:
    if ENRICHED.exists():
        return ENRICHED
    if ENRICHED_FIXED.exists():
        return ENRICHED_FIXED
    return None


def load_source_text(pdf_path: str) -> str:
    if not pdf_path:
        return ""
    stem = Path(pdf_path).stem
    txt_path = TEXT_DIR / f"{stem}.txt"
    if not txt_path.exists():
        return ""
    return txt_path.read_text(encoding="utf-8", errors="ignore")


def find_exact_quote_pages(pages: Dict[int, str], claim_text: str) -> List[int]:
    pages_with_quote: Set[int] = set()
    if not claim_text:
        return []
    for m in re.finditer(r'[\"“](.+?)[\"”]', claim_text):
        q = normalize_quotes(m.group(1))
        for pno, ptext in pages.items():
            if normalize_quotes(ptext).find(q) != -1:
                pages_with_quote.add(int(pno))
    return sorted(pages_with_quote)


def main():
    src = _pick_enriched()
    if not src:
        print("Missing enriched registry (expected outputs/ccp_registry_enriched*.csv).")
        return

    df = pd.read_csv(src, dtype=str).fillna("")

    offsets: Dict[str, int] = {}
    if OFFSETS.exists():
        odf = pd.read_csv(OFFSETS, dtype={"logical_minus_pdf_offset": int}).fillna("")
        for _, r in odf.iterrows():
            try:
                offsets[str(r["source_pdf_path"])] = int(r["logical_minus_pdf_offset"])
            except Exception:
                pass

    with open(CANDIDATES_JSONL, "w", encoding="utf-8") as fout:
        for _, row in df.iterrows():
            pdf_path = row.get("source_pdf_path", "")
            if not pdf_path:
                continue

            txt = load_source_text(pdf_path)
            if not txt:
                continue

            pages = split_pages(txt)
            chunks = chunk_pages_to_windows(pages, chunk_words=CHUNK_W, stride=STRIDE)

            candidate_chunks: List[Dict] = []
            used_idx: Set[int] = set()

            def add_page_chunks(target_pages: List[int], max_add: int = TOPK):
                added = 0
                for idx, ch in enumerate(chunks):
                    if idx in used_idx:
                        continue
                    # window overlaps any target page
                    if any(ch["page_start"] <= p <= ch["page_end"] for p in target_pages):
                        candidate_chunks.append(
                            {
                                "page_range": f"{ch['page_start']}"
                                if ch["page_start"] == ch["page_end"]
                                else f"{ch['page_start']}-{ch['page_end']}",
                                "text": ch["text"],
                                "score": 100,  # heuristic "exact-ish" anchor
                            }
                        )
                        used_idx.add(idx)
                        added += 1
                        if added >= max_add:
                            return

            # 1) Exact quote match anchors (only when actually a quote)
            if as_bool(row.get("is_quote", "")):
                exact_pages = find_exact_quote_pages(pages, str(row.get("claim_text", "")))
                if exact_pages:
                    add_page_chunks(exact_pages, max_add=TOPK)

            # 2) Stated page mapped via inferred offset
            stated = str(row.get("stated_page", "")).strip()
            off = offsets.get(str(pdf_path))
            m = re.search(r"(\d+)", stated) if stated else None
            if m and (off is not None):
                mapped_pdf_page = int(m.group(1)) - int(off)
                if mapped_pdf_page in pages:
                    add_page_chunks([mapped_pdf_page], max_add=max(1, TOPK - len(candidate_chunks)))

            # 3) Fuzzy BM25 (or similar) retrieval to fill remaining slots
            if len(candidate_chunks) < TOPK:
                rem = TOPK - len(candidate_chunks)
                fuzzy = top_k_chunks_for_claim(str(row.get("claim_text", "")), chunks, k=rem)
                candidate_chunks.extend(fuzzy)

            payload = {
                "review_id": row.get("review_id", ""),
                "section": row.get("section", ""),
                "claim_id": row.get("claim_id", ""),
                "claim_text": row.get("claim_text", ""),
                "citation_text": row.get("citation_text", ""),
                "citation_type": row.get("citation_type", ""),
                "is_secondary": as_bool(row.get("is_secondary", "")),
                "primary_mentioned_author": row.get("primary_mentioned_author", ""),
                "primary_mentioned_year": row.get("primary_mentioned_year", ""),
                "stated_page": row.get("stated_page", ""),
                "citation_author": row.get("citation_author", ""),
                "citation_year": row.get("citation_year", ""),
                "source_pdf_path": pdf_path,
                "evidence": candidate_chunks[:TOPK],
            }
            fout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(f"[OK] wrote candidates to {CANDIDATES_JSONL}")


if __name__ == "__main__":
    main()
