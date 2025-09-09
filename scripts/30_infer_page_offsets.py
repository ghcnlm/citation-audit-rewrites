# scripts/30_infer_page_offsets.py
from __future__ import annotations

import re
import yaml
import pandas as pd
from pathlib import Path
from audit_lib.pdf_utils import split_pages
from audit_lib.paths import load_enriched  # NEW central loader

CONFIG = yaml.safe_load(open("config/config.yaml", "r", encoding="utf-8"))
TEXT_DIR = Path(CONFIG["paths"]["sources_text_dir"])
OUT_DIR = Path(CONFIG["paths"]["outputs_dir"])

OFFSETS = OUT_DIR / "page_offsets.csv"

def _truthy(x) -> bool:
    s = str(x).strip().lower()
    return s in ("1", "true", "yes", "y")

def normalize_quotes(s: str) -> str:
    return s.replace("“", "\"").replace("”", "\"").replace("’", "'").replace("‘", "'")

def find_quote_page(pages: dict, quote: str):
    q = normalize_quotes(quote.strip())
    for pno, ptext in pages.items():
        if normalize_quotes(ptext).find(q) != -1:
            return pno
    return None

def main():
    # Load canonical enriched registry (603 rows in your current dataset)
    df = load_enriched()

    # Filter: only quote claims with a non-empty stated_page
    df = df[_truthy(df["is_quote"]) & (df["stated_page"].astype(str).str.len() > 0)]

    rows = []
    for pdf_path, g in df.groupby("source_pdf_path"):
        if not isinstance(pdf_path, str) or not pdf_path or not Path(pdf_path).exists():
            continue

        txt_path = Path(TEXT_DIR) / (Path(pdf_path).stem + ".txt")
        if not txt_path.exists():
            continue

        txt = txt_path.read_text(encoding="utf-8", errors="ignore")
        pages = split_pages(txt)

        offsets = []
        for _, r in g.iterrows():
            m = re.search(r'["“](.+?)["”]', str(r["claim_text"]))
            if not m:
                continue
            quote = m.group(1)
            found_page = find_quote_page(pages, quote)
            if found_page is None:
                continue
            m2 = re.match(r"(\d+)", str(r["stated_page"]))
            if not m2:
                continue
            stated = int(m2.group(1))
            try:
                offsets.append(stated - int(found_page))
            except Exception:
                continue

        if offsets:
            offsets_sorted = sorted(offsets)
            mid = len(offsets_sorted) // 2
            if len(offsets_sorted) % 2 == 1:
                off = offsets_sorted[mid]
            else:
                off = (offsets_sorted[mid - 1] + offsets_sorted[mid]) // 2

            rows.append({
                "source_pdf_path": pdf_path,
                "logical_minus_pdf_offset": off,
                "n_examples": len(offsets)
            })

    if rows:
        pd.DataFrame(rows).to_csv(OFFSETS, index=False)
        print(f"[OK] wrote offsets -> {OFFSETS}")
    else:
        print("No offsets inferred (insufficient quotes with stated pages or matches not found).")

if __name__ == "__main__":
    main()
    