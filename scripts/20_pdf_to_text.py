import os, yaml
from pathlib import Path
from audit_lib.pdf_utils import pdf_to_text_with_page_markers

CONFIG = yaml.safe_load(open("config/config.yaml","r",encoding="utf-8"))
PDF_DIR = CONFIG["paths"]["pdf_dir"]
OUT_DIR = CONFIG["paths"]["sources_text_dir"]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for pdf in Path(PDF_DIR).glob("*.pdf"):
        out = Path(OUT_DIR) / (pdf.stem + ".txt")
        try:
            text = pdf_to_text_with_page_markers(str(pdf))
            out.write_text(text, encoding="utf-8")
            print(f"[OK] {pdf.name} -> {out.name}")
        except Exception as e:
            print(f"[ERR] {pdf.name}: {e}")

if __name__ == "__main__":
    main()
