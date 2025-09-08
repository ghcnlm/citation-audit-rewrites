# scripts/fix_enriched_csv.py
import re, unicodedata, os, sys, glob
import pandas as pd
from pathlib import Path

CSV_IN  = sys.argv[1] if len(sys.argv) > 1 else "outputs/ccp_registry_enriched.csv"
CSV_OUT = sys.argv[2] if len(sys.argv) > 2 else "outputs/ccp_registry_enriched_FIXED.csv"

PDF_DIR = Path("pilot_inputs/sources_pdf")

# --- helpers ---------------------------------------------------------------

def ascii_norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").strip()
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s

def clean_author_token(raw: str) -> str:
    """Normalize a citation_author to a keyable first-author surname."""
    if not raw: return ""
    s = ascii_norm(raw)
    # Canonicalize dash variants & whitespace
    s = s.replace("–", "-").replace("—", "-").replace("‐", "-")
    s = re.sub(r"\s+", " ", s).strip()

    # Common producer typos / variants
    s = s.replace("CLEARAA", "CLEAR-AA")

    # Drop possessives and trailing garbage like “’s”
    s = re.sub(r"[’']s\b", "", s)

    # Remove leading phrases that leaked from prose (“Theory and Kirkhart’s”, etc.)
    # Keep only the first authorish token cluster (allowing hyphens)
    # If we have “A & B” or “A and B”, keep A (first author)
    s = re.split(r"\s+(?:&|and)\s+", s)[0]

    # Kill “et al.” if it’s there
    s = re.sub(r"\bet\s+al\.?\b", "", s, flags=re.I).strip()

    # If it still has commas, keep leftmost (often “Surname, Initials”)
    s = s.split(",")[0].strip()

    # Keep a single surname-ish token (letters/hyphen only)
    m = re.search(r"[A-Za-z\-]+", s)
    return m.group(0).lower() if m else ""

def clean_year(y) -> str:
    if pd.isna(y): return ""
    m = re.search(r"(19|20)\d{2}", str(y))
    return m.group(0) if m else ""

def rel_pdf(pathlike: str) -> str:
    """Normalize to forward-slash relative path inside pilot_inputs/sources_pdf."""
    if not pathlike: return ""
    name = os.path.basename(pathlike)
    return f"pilot_inputs/sources_pdf/{name}"

def build_pdf_index(pdf_dir: Path):
    """
    Index available PDFs as:
      key: (author_key, year) -> list of filenames
    author_key = first surname (lowercased) from filename prefix before '_' if possible.
    """
    idx = {}
    for p in glob.glob(str(pdf_dir / "*.pdf")):
        name = os.path.basename(p)
        stem = os.path.splitext(name)[0]  # e.g., Chirau_2022
        s = ascii_norm(stem)
        # Extract year from suffix
        ym = re.search(r"(19|20)\d{2}", s)
        year = ym.group(0) if ym else ""
        # Extract author key as leftmost token before year or underscore
        left = s.split("_")[0]
        akey = clean_author_token(left)
        if not akey:
            continue
        idx.setdefault((akey, year), []).append(name)
    return idx

def choose_pdf(author_key: str, year: str, idx) -> str:
    """
    Strict: require exact (author_key, year) match.
    If multiple, return the shortest name (deterministic).
    If none, return "".
    """
    if not author_key or not year:
        return ""
    cands = idx.get((author_key, year), [])
    if not cands:
        return ""
    # deterministic pick
    cands = sorted(cands, key=len)
    return cands[0]

# Optional explicit overrides for known tricky mappings or different stems.
OVERRIDES = {
    # author_key|year -> filename
    "chirau|2022": "Chirau_2022.pdf",
    "masvaure|2022": "Masvaure_2022.pdf",
    "alkin|2017": "Alkin_2017.pdf",
    "johnson|2009": "Johnson_2009.pdf",
    "clear-aa|2020": "CLEAR_AA_2020.pdf",
}

def apply_overrides(author_key: str, year: str) -> str:
    return OVERRIDES.get(f"{author_key}|{year}", "")

# --- run -------------------------------------------------------------------

df = pd.read_csv(CSV_IN, dtype=str).fillna("")

# Build inventory of PDFs actually present
pdf_idx = build_pdf_index(PDF_DIR)
present_files = {n for lst in pdf_idx.values() for n in lst}

# Add diagnostics columns
df["author_key"] = df["citation_author"].map(clean_author_token)
df["year_key"]   = df["citation_year"].map(clean_year)
df["mapping_note"] = ""

# Normalize existing paths to relative, forward-slash
df["source_pdf_path"] = df["source_pdf_path"].map(rel_pdf)

# Try strict author+year match, with overrides first
fixed_paths = []
notes = []

for i, row in df.iterrows():
    akey = row["author_key"]
    ykey = row["year_key"]

    # Skip if no citation info
    if not akey or not ykey:
        fixed_paths.append(row["source_pdf_path"])
        notes.append(row["mapping_note"])
        continue

    # 1) Try override table
    over = apply_overrides(akey, ykey)
    if over and over in present_files:
        fixed_paths.append(f"pilot_inputs/sources_pdf/{over}")
        notes.append("override")
        continue

    # 2) Strict index match
    chosen = choose_pdf(akey, ykey, pdf_idx)
    if chosen:
        fixed_paths.append(f"pilot_inputs/sources_pdf/{chosen}")
        # If original pointed to a different year, flag it
        orig = os.path.basename(row["source_pdf_path"])
        if orig and orig != chosen:
            notes.append(f"corrected_from:{orig}")
        else:
            notes.append("")
    else:
        # No exact file—leave blank and flag for manual
        fixed_paths.append("")
        notes.append("no_exact_author_year_pdf")

df["source_pdf_path"] = fixed_paths
df["mapping_note"] = notes

# Clean CLEARAA typos in citation_author
df.loc[df["citation_author"].str.contains(r"\bCLEARAA\b", case=False, regex=True), "citation_author"] = "CLEAR-AA"

# Standardize backslashes that might remain anywhere
for col in ["source_pdf_path"]:
    df[col] = df[col].str.replace("\\", "/", regex=False)

# Write out
df.to_csv(CSV_OUT, index=False)
print(f"wrote: {CSV_OUT}")

# Also emit a small QA report to console
bad = df[df["mapping_note"].isin(["no_exact_author_year_pdf", "override", "corrected_from:"+df["source_pdf_path"].map(os.path.basename)])]
print("\n=== QA summary ===")
print(df["mapping_note"].value_counts())
print("\nExamples needing manual mapping:")
print(df.loc[df["mapping_note"]=="no_exact_author_year_pdf", ["claim_id","citation_text","citation_author","citation_year"]].head(20).to_string(index=False))