from typing import Dict
from pypdf import PdfReader
def pdf_to_text_with_page_markers(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    out_lines = []
    for i, page in enumerate(reader.pages, start=1):
        out_lines.append(f"<<<PAGE={i}>>>")
        text = page.extract_text() or ""
        out_lines.append(text.strip())
    return "\n".join(out_lines)
def split_pages(text_with_markers: str) -> Dict[int, str]:
    pages = {}
    current_page = None
    buf = []
    for line in text_with_markers.splitlines():
        if line.startswith("<<<PAGE=") and line.endswith(">>>"):
            if current_page is not None:
                pages[current_page] = "\n".join(buf).strip()
                buf = []
            current_page = int(line.replace("<<<PAGE=", "").replace(">>>", ""))
        else:
            buf.append(line)
    if current_page is not None:
        pages[current_page] = "\n".join(buf).strip()
    return pages
