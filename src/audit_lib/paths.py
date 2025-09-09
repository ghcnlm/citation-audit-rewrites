# src/audit_lib/paths.py
from __future__ import annotations

from pathlib import Path
import pandas as pd

# Resolve repo root from this file's location (src/audit_lib/.../paths.py → repo root)
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"

def find_enriched_path() -> Path:
    """Return the best available enriched registry path."""
    candidates = [
        OUT / "ccp_registry_enriched.csv",
        OUT / "ccp_registry_enriched_FIXED.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    # Last resort: any enriched-like file under outputs
    for p in OUT.glob("**/ccp_registry_enriched*.csv"):
        return p
    raise FileNotFoundError("No enriched registry found in outputs/.")

def find_adjudications_path() -> Path:
    """Return the adjudications_with_rewrites.csv path (authoritative)."""
    p = OUT / "adjudications_with_rewrites.csv"
    if p.exists():
        return p
    raise FileNotFoundError(
        "adjudications_with_rewrites.csv not found in outputs/ "
        "(run scripts/50_adjudicate.py first)."
    )

def load_enriched() -> pd.DataFrame:
    """Load enriched registry as strings, non-dropping."""
    p = find_enriched_path()
    return pd.read_csv(p, dtype=str, keep_default_na=False)

def load_adjudications() -> pd.DataFrame:
    """Load adjudications_with_rewrites as strings."""
    p = find_adjudications_path()
    return pd.read_csv(p, dtype=str, keep_default_na=False)
