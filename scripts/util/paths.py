from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_REVIEWS_DIR = REPO_ROOT / "pilot_inputs" / "reviews"
INPUT_PDF_DIR     = REPO_ROOT / "pilot_inputs" / "sources_pdf"
OUTPUT_DIR        = REPO_ROOT / "outputs"
HISTORY_DIR       = OUTPUT_DIR / "history"

CANONICAL_CSV     = OUTPUT_DIR / "ccp_registry_enriched_FIXED.csv"
LEGACY_ENRICHED   = OUTPUT_DIR / "ccp_registry_enriched.csv"     # backward-compat
LEGACY_BASE       = OUTPUT_DIR / "ccp_registry.csv"              # if present

# Make sure dirs exist when imported
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)