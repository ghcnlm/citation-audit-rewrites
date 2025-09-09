import re
import sys
import glob
import datetime as dt
from pathlib import Path
from typing import Optional, List, Tuple

import pandas as pd

from scripts.util.paths import (
    INPUT_PDF_DIR,
    OUTPUT_DIR,
    HISTORY_DIR,
    CANONICAL_CSV,
    LEGACY_ENRICHED,
    LEGACY_BASE,
)
from scripts.util.schema import REQUIRED_ENRICHED_COLUMNS
from scripts.util.guards import ensure_columns, safe_write_csv

# ---------- Helpers to normalize/guess PDF filenames ----------

VALID_PDF_EXTS = (".pdf",)

def _norm_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\bet\s+al\.?,?\b", "", s, flags=re.I)  # remove 'et al.'
    s = s.replace("-", "_")                             # hyphen→underscore
    s = re.sub(r"[^\w\._]+", "_", s)                    # non-word→underscore
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def _extract_year(s: str) -> str:
    m = re.search(r"(19|20)\d{2}", s or "")
    return m.group(0) if m else ""

def _list_all_pdfs() -> List[Path]:
    files = []
    for ext in VALID_PDF_EXTS:
        files.extend(INPUT_PDF_DIR.glob(f"*{ext}"))
    return files

def _candidate_basenames(citation_text: str) -> List[str]:
    lead = (citation_text or "").split(",")[0]
    lead_n = _norm_text(lead)
    year = _extract_year(citation_text) or ""
    cands = []
    if year:
        cands.append(f"{lead_n}_{year}")
    cands.append(lead_n)
    return cands

def _best_match(cands: List[str], files: List[Path]) -> Optional[str]:
    if not files:
        return None
    # exact match first
    basenames = {f.stem.lower(): f.name for f in files}
    for c in cands:
        if c.lower() in basenames:
            return basenames[c.lower()]
    # loose match: choose file whose normalized stem shares most tokens with candidate
    def tnorm(x: str) -> List[str]:
        return [t for t in re.split(r"[_\W]+", _norm_text(x).lower()) if t]
    best: Tuple[int, Optional[str]] = (0, None)
    for cand in cands:
        c_tokens = set(tnorm(cand))
        for f in files:
            f_tokens = set(tnorm(f.stem))
            score = len(c_tokens & f_tokens)
            if score > best[0]:
                best = (score, f.name)
    return best[1]

def guess_pdf_from_citation(citation_text: str) -> Optional[str]:
    cands = _candidate_basenames(citation_text)
    files = _list_all_pdfs()
    return _best_match(cands, files)

def fill_source_pdf(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "source_pdf" not in out.columns:
        out["source_pdf"] = ""
    mask_blank = out["source_pdf"].isna() | (out["source_pdf"].astype(str).str.strip() == "")
    if "citation_text" not in out.columns:
        # nothing we can do, just solidify blanks to ""
        out["source_pdf"] = out["source_pdf"].fillna("")
        return out
    out.loc[mask_blank, "source_pdf"] = out.loc[mask_blank, "citation_text"].map(guess_pdf_from_citation)
    out["source_pdf"] = out["source_pdf"].fillna("")
    return out

# ---------- Minimal derivations for required columns ----------

def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in REQUIRED_ENRICHED_COLUMNS:
        if col not in out.columns:
            # initialize sensible defaults
            if col in ("is_quote", "has_numbers", "is_causal_or_normative"):
                out[col] = False
            else:
                out[col] = ""
    # derive is_quote / has_numbers if missing or blanky
    if "claim_text" in out.columns:
        ct = out["claim_text"].fillna("")
        if "is_quote" in out.columns and out["is_quote"].dtype != bool:
            out["is_quote"] = out["is_quote"].astype(str).str.lower().isin(["true", "1", "yes"])
        if "has_numbers" in out.columns and out["has_numbers"].dtype != bool:
            out["has_numbers"] = out["has_numbers"].astype(str).str.lower().isin(["true", "1", "yes"])
        # If still default False, try heuristic
        out.loc[out["is_quote"] == False, "is_quote"] = ct.str.contains(r"[“”\"']", regex=True)
        out.loc[out["has_numbers"] == False, "has_numbers"] = ct.str.contains(r"\d", regex=True)
    return out

# ---------- Read inputs intelligently ----------

def read_best_available() -> pd.DataFrame:
    """
    Preference order:
      1) outputs/ccp_registry_enriched.csv (already enriched intermediate)
      2) outputs/ccp_registry.csv        (base; we’ll ensure/augment required cols)
    """
    if LEGACY_ENRICHED.exists():
        return pd.read_csv(LEGACY_ENRICHED, encoding="utf-8")
    if LEGACY_BASE.exists():
        return pd.read_csv(LEGACY_BASE, encoding="utf-8")
    raise FileNotFoundError(
        "No input CSVs found. Expected one of:\n"
        f" - {LEGACY_ENRICHED}\n - {LEGACY_BASE}\n"
        "Run your extractor first."
    )

# ---------- Main ----------

def main() -> int:
    df = read_best_available()
    df = ensure_required_columns(df)
    df = fill_source_pdf(df)

    # Final contract check
    ensure_columns(df, REQUIRED_ENRICHED_COLUMNS, where="99_build_enriched_fixed")

    # Write canonical CSV
    safe_write_csv(df, str(CANONICAL_CSV))

    # Backward-compat shim (one line keeps downstream working unchanged)
    safe_write_csv(df, str(LEGACY_ENRICHED))

    # Timestamped history copy
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    history_path = HISTORY_DIR / f"ccp_registry_enriched_FIXED_{stamp}.csv"
    safe_write_csv(df, str(history_path))

    # Optional: Parquet if pyarrow is installed
    try:
        df.to_parquet(str(CANONICAL_CSV).replace(".csv", ".parquet"), index=False)
    except Exception:
        pass

    print(f"Wrote canonical: {CANONICAL_CSV}")
    print(f"Backward-compat: {LEGACY_ENRICHED}")
    print(f"History copy:    {history_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())