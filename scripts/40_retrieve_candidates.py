# scripts/40_retrieve_candidates.py
from __future__ import annotations

import json
import re
import yaml
import pandas as pd
from pathlib import Path
from audit_lib.pdf_utils import split_pages
from audit_lib.retrieval import chunk_pages_to_windows, top_k_chunks_for_claim
from audit_lib.paths import load_enriched  # NEW central loader

CONFIG = yaml.safe_load(open("config/config.yaml", "r", encoding="utf-8"))
TEXT_DIR = Path(CONFIG["paths"]["sources_text_dir"])
OUT_DIR = Path(CONFIG["paths"]["outputs_dir"])
CHUNK_W = CONFIG["retrieval"]["chunk_words"]
STRIDE = CONFIG["retrieval"]["chunk_stride"]
TOPK = CONFIG["retrieval"]["top_k"]

CANDIDATES_JSONL = Path(OUT_DIR) / "adjudication_inputs.jsonl"
OFFSETS = Path(OUT_DIR) / "page_offsets.csv"

def _truthy(x) -> bool:
    s = str(x).strip().lower()
    return s in ("1", "true", "yes", "y")

def normalize_quotes(s: str) -> str:
    return s.replace("“", "\"").replace("”", "\"").replace("’", "'").replace("‘", "'")

def load_source_text(pdf_path: str) -> str:
    stem = Path(pdf_path).stem
    txt_path = Path(TEXT_DIR) / f"{stem}.txt"
    if not txt_path.exists():
        return ""
    return txt_path.read_text(encoding="utf-8", errors="ignore")

def find_exact_quote_pages(pages: dict, claim_text: str):
    pages_with_quote = set()
    for m in re.finditer(r'["“](.+?)["”]', claim_text):
        q = normalize_quotes(m.group(1))
        for pno, ptext in pages.items():
            if normalize_quotes(ptext).find(q) != -1:
                pages_with_quote.add(pno)
    return sorted(pages_with_quote)

def main():
    df = load_enriched()

    offsets = {}
    if OFFSETS.exists():
        odf = pd.read_csv(OFFSETS, dtype=str).fillna("")
        for _, r in odf.iterrows():
            try:
                offsets[str(r["source_pdf_path"])] = int(r["logical_minus_pdf_offset"])
            except Exception:
                continue

    with open(CANDIDATES_JSONL, "w", encoding="utf-8") as fout:
        for _, row in df.iterrows():
            pdf_path = row["source_pdf_path"]
            if not isinstance(pdf_path, str) or not pdf_path:
                continue
            txt = load_source_text(pdf_path)
            if not txt:
                continue

            pages = split_pages(txt)
            chunks = chunk_pages_to_windows(pages, chunk_words=CHUNK_W, stride=STRIDE)

            candidate_chunks = []
            used_idx = set()

            def add_page_chunks(target_pages, max_add=TOPK):
                added = 0
                for idx, ch in enumerate(chunks):
                    if idx in used_idx:
                        continue
                    if any(ch["page_start"] <= p <= ch["page_end"] for p in target_pages):
                        candidate_chunks.append({
                            "page_range": f"{ch['page_start']}" if ch['page_start'] == ch['page_end']
                                           else f"{ch['page_start']}-{ch['page_end']}",
                            "text": ch["text"],
                            "score": 100
                        })
                        used_idx.add(idx)
                        added += 1
                        if added >= max_add:
                            return

            if _truthy(row.get("is_quote", "")):
                exact_pages = find_exact_quote_pages(pages, str(row["claim_text"]))
            else:
                exact_pages = []

            if exact_pages:
                add_page_chunks(exact_pages, max_add=TOPK)

            stated = str(row.get("stated_page") or "").strip()
            off = offsets.get(str(pdf_path), None)
            if stated and off is not None and stated.split("-")[0].isdigit():
                mapped_pdf_page = int(stated.split("-")[0]) - int(off)
                if mapped_pdf_page in pages:
                    add_page_chunks([mapped_pdf_page],
                                    max_add=max(1, TOPK - len(candidate_chunks)))

            if len(candidate_chunks) < TOPK:
                rem = TOPK - len(candidate_chunks)
                fuzzy = top_k_chunks_for_claim(str(row["claim_text"]), chunks, k=rem)
                candidate_chunks.extend(fuzzy)

            payload = {
                "review_id": row["review_id"],
                "section": row["section"],
                "claim_id": row["claim_id"],
                "claim_text": row["claim_text"],
                "citation_text": row.get("citation_text", ""),
                "citation_type": row.get("citation_type", ""),
                "is_secondary": _truthy(row.get("is_secondary", "")),
                "primary_mentioned_author": row.get("primary_mentioned_author", ""),
                "primary_mentioned_year": row.get("primary_mentioned_year", ""),
                "stated_page": row.get("stated_page", ""),
                "citation_author": row.get("citation_author", ""),
                "citation_year": row.get("citation_year", ""),
                "source_pdf_path": row["source_pdf_path"],
                "evidence": candidate_chunks[:TOPK]
            }
            fout.write(json.dumps(payload, ensure_ascii=False) + "\n")

    print(f"[OK] wrote candidates to {CANDIDATES_JSONL}")

if __name__ == "__main__":
    main()
