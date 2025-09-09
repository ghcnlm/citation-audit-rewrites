from pathlib import Path
import pandas as pd
from .paths import CANONICAL_CSV

def read_enriched_fixed() -> pd.DataFrame:
    if Path(str(CANONICAL_CSV).replace(".csv", ".parquet")).exists():
        return pd.read_parquet(str(CANONICAL_CSV).replace(".csv", ".parquet"))
    if CANONICAL_CSV.exists():
        return pd.read_csv(CANONICAL_CSV, encoding="utf-8")
    raise FileNotFoundError(
        "Missing canonical artifact. Run: python scripts/99_build_enriched_fixed.py"
    )