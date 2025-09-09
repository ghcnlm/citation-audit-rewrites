from typing import Iterable, Dict, Any
import pandas as pd

def ensure_columns(df: pd.DataFrame, required: Iterable[str], *, where: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"[{where}] Missing required columns: {missing}")

def coerce_dtypes(df: pd.DataFrame, dtypes: Dict[str, Any]) -> pd.DataFrame:
    out = df.copy()
    for col, typ in dtypes.items():
        if col in out.columns:
            try:
                out[col] = out[col].astype(typ)
            except Exception:
                # best-effort; keep original if coercion fails
                pass
    return out

def safe_write_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False, encoding="utf-8")