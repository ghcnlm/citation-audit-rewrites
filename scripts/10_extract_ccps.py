import os, re, uuid, yaml, pandas as pd
from pathlib import Path
from typing import List

from docx import Document
from audit_lib.text_utils import split_sentences, has_numbers, is_causal_or_normative
from audit_lib.citations import parse_citations
from audit_lib.models import Citation

CONFIG = yaml.safe_load(open("config/config.yaml","r",encoding="utf-8"))

REVIEWS_DIR = CONFIG["paths"]["reviews_dir"]
OUTPUTS_DIR = CONFIG["paths"]["outputs_dir"]
PDF_DIR = CONFIG["paths"]["pdf_dir"]

CCP_PATH = os.path.join(OUTPUTS_DIR, "ccp_registry.csv")
REFS_INDEX = Path(OUTPUTS_DIR)/"references_index.csv"

FIELDNAMES = ["review_id","section","claim_id","claim_text","is_quote","has_numbers","is_causal_or_normative",
              "citation_text","citation_type","citation_author","citation_year","is_secondary",
              "primary_mentioned_author","primary_mentioned_year","stated_page","in_reference_list",
              "source_pdf_path","priority"]

def load_text_from_file(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        doc = Document(str(path))
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        return Path(path).read_text(encoding="utf-8", errors="ignore")

def infer_sections(lines):
    section = "unknown"
    for line in lines:
        t = line.strip()
        if not t:
            continue
        if t.startswith("#"):
            section = t.lstrip("#").strip().lower()
        elif t.isupper() and len(t.split()) <= 8:
            section = t.lower()
        elif t.endswith(":") and len(t.split()) <= 8:
            section = t[:-1].strip().lower()
        yield section, t

def priority_flag(is_quote, has_nums, is_causal):
    return "High" if (is_quote or has_nums or is_causal) else "Low"

def build_refs_lookup():
    if not REFS_INDEX.exists():
        return set()
    df = pd.read_csv(REFS_INDEX)
    df["first_author_norm"] = df["first_author"].str.strip().str.lower()
    df["year_norm"] = df["year"].astype(str).str.strip().str.lower()
    return set(zip(df["first_author_norm"], df["year_norm"]))

def first_author_key(author_str: str) -> str:
    a = author_str.split("&")[0].split("and")[0].strip()
    a = a.split(",")[0].strip()
    return a.split()[0].lower()

def main():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    refs_set = build_refs_lookup()
    rows = []
    for f in Path(REVIEWS_DIR).glob("*"):
        if f.suffix.lower() not in {".docx",".md",".txt"}:
            continue
        text = load_text_from_file(f)
        lines = text.splitlines()
        current_review_id = f.stem
        for section, line in infer_sections(lines):
            for sent in split_sentences(line):
                cits: List[Citation] = parse_citations(sent)
                if not cits: 
                    continue
                is_quote = bool(re.search(r'["“”\']', sent))
                nums = has_numbers(sent)
                causal = is_causal_or_normative(sent)
                for cit in cits:
                    claim_id = str(uuid.uuid4())[:8]
                    fa_key = first_author_key(cit.author)
                    yr_key = cit.year.lower()
                    in_refs = (fa_key, yr_key) in refs_set if refs_set else ""
                    pdf_guess = os.path.join(
                        PDF_DIR,
                        f"{cit.author.split(',')[0].replace(' ','_')}_{cit.year}.pdf",
                    )
                    rows.append(
                        {
                            "review_id": current_review_id,
                            "section": section,
                            "claim_id": claim_id,
                            "claim_text": sent.strip(),
                            "is_quote": is_quote,
                            "has_numbers": nums,
                            "is_causal_or_normative": causal,
                            "citation_text": cit.citation_text,
                            "citation_type": cit.citation_type,
                            "citation_author": cit.author,
                            "citation_year": cit.year,
                            "is_secondary": bool(cit.is_secondary),
                            "primary_mentioned_author": cit.primary_mentioned_author or "",
                            "primary_mentioned_year": cit.primary_mentioned_year or "",
                            "stated_page": cit.stated_page or "",
                            "in_reference_list": in_refs,
                            "source_pdf_path": pdf_guess if os.path.exists(pdf_guess) else "",
                            "priority": priority_flag(is_quote, nums, causal),
                        }
                    )
    if rows:
        pd.DataFrame(rows, columns=FIELDNAMES).to_csv(CCP_PATH, index=False)
        print(f"[OK] wrote {CCP_PATH}")
    else:
        print("No citations found. Check formats or improve parsing rules.")

if __name__ == "__main__":
    main()