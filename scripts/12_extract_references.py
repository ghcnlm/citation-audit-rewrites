import os, yaml
from pathlib import Path
from docx import Document
from audit_lib.refs import index_references
import pandas as pd

CONFIG = yaml.safe_load(open("config/config.yaml","r",encoding="utf-8"))
REVIEWS_DIR = CONFIG["paths"]["reviews_dir"]
OUT_DIR = CONFIG["paths"]["outputs_dir"]

OUT_PATH = Path(OUT_DIR)/"references_index.csv"

def load_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        doc = Document(str(path))
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        return path.read_text(encoding="utf-8", errors="ignore")

def main():
    rows = []
    for f in Path(REVIEWS_DIR).glob("*"):
        if f.suffix.lower() not in {".docx",".md",".txt"}:
            continue
        text = load_text(f)
        rid = f.stem
        rows.extend(index_references(text, rid))
    if rows:
        pd.DataFrame(rows).to_csv(OUT_PATH, index=False)
        print(f"[OK] wrote {OUT_PATH}")
    else:
        print("No references detected. Ensure a 'References' heading exists and entries follow 'Surname, X. (Year)' format.")

if __name__ == "__main__":
    main()
