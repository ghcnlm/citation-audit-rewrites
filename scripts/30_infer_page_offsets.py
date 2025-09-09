# scripts/30_infer_page_offsets.py
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import yaml

from audit_lib.pdf_utils import split_pages

CONFIG = yaml.safe_load(open("config/config.yaml", "r", encoding="utf-8"))
TEXT_DIR: Path = Path(CONFIG["paths"]["sources_text_dir"])
OUT_DIR: Path = Path(CONFIG["paths"]["outputs_dir"])

ENRICHED = OUT_DIR / "ccp_registry_enriched.csv"
ENRICHED_FIXED = OUT_DIR / "ccp_registry_enriched_FIXED.csv"
OFFSETS = OUT_DIR / "page_offsets.csv"


def _pick_enriched() -> Optional[Path]:
    """Prefer enriched; fallback to enriched_FIXED if present."""
    if ENRICHED.exists():
        return ENRICHED
    if ENRICHED_FIXED.exists():
        return ENRICHED_FIXED
    return None


TRUEY = {"1", "true", "t", "y", "yes"}
FALSEY = {"0", "false", "f", "n", "no", ""}


def as_bool(val) -> bool:
    if isinstance(val, (int, float)):
        return bool(val)
    s = str(val).strip().lower()
    if s in TRUEY:
        return True
    if s in FALSEY:
        return False
    # Fall back: any non-empty string becomes True
    return len(s) > 0


def normalize_quotes(s: str) -> str:
    return (
        s.replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("‘", "'")
    )


def quoted_spans(text: str) -> List[str]:
    """Return all substrings inside straight or curly quotes."""
    spans: List[str] = []
    for m in re.finditer(r'[\"“](.+?)[\"”]', text or ""):
        spans.append(m.group(1))
    return spans


def parse_first_int(s: str) -> Optional[int]:
    if not s:
        return None
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None


def find_quote_page(pages: Dict[int, str], quote: str) -> Optional[int]:
    """Return first page number containing quote (normalized)."""
    q = normalize_quotes(quote.strip())
    if not q:
        return None
    for pno, ptext in pages.items():
        if normalize_quotes(ptext).find(q) != -1:
            return pno
    return None


def median_int(seq: Iterable[int]) -> Optional[int]:
    arr = sorted(seq)
    n = len(arr)
    if n == 0:
        return None
    mid = n // 2
    if n % 2 == 1:
        return arr[mid]
    return (arr[mid - 1] + arr[mid]) // 2


def main():
    src = _pick_enriched()
    if not src:
        print("Missing enriched registry (expected outputs/ccp_registry_enriched*.csv).")
        return

    df = pd.read_csv(src, dtype=str).fillna("")
    # Only keep rows that are quotes and have a stated page
    df["is_quote_bool"] = df["is_quote"].map(as_bool)
    df = df[(df["is_quote_bool"]) & (df["stated_page"].str.len() > 0)]

    rows_out = []
    for pdf_path, g in df.groupby("source_pdf_path"):
        if not isinstance(pdf_path, str) or not pdf_path.strip():
            continue

        stem = Path(pdf_path).stem
        txt_path = TEXT_DIR / f"{stem}.txt"
        if not txt_path.exists():
            continue

        txt = txt_path.read_text(encoding="utf-8", errors="ignore")
        pages = split_pages(txt)  # {int page_no: str page_text}
        offsets_for_pdf: List[int] = []

        for _, r in g.iterrows():
            claim_text = str(r.get("claim_text", ""))
            quotes = quoted_spans(claim_text)
            if not quotes:
                continue

            found_page: Optional[int] = None
            for q in quotes:
                found_page = find_quote_page(pages, q)
                if found_page is not None:
                    break
            if found_page is None:
                continue

            stated = parse_first_int(str(r.get("stated_page", "")))
            if stated is None:
                continue

            offsets_for_pdf.append(stated - int(found_page))

        med = median_int(offsets_for_pdf)
        if med is not None:
            rows_out.append(
                {
                    "source_pdf_path": pdf_path,
                    "logical_minus_pdf_offset": int(med),
                    "n_examples": len(offsets_for_pdf),
                }
            )

    if rows_out:
        pd.DataFrame(rows_out).to_csv(OFFSETS, index=False)
        print(f"[OK] wrote offsets -> {OFFSETS}")
    else:
        print("No offsets inferred (insufficient matches).")


if __name__ == "__main__":
    main()
