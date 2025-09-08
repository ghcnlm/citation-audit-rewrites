import pathlib, re
from docx import Document

def collapse_ws(s): 
    import re
    return re.sub(r"\s+", " ", s or "").strip()

def detect_heading_level(paragraph):
    try:
        style = paragraph.style
        if style is not None:
            name = getattr(style, "name", "") or ""
            m = re.search(r"heading\s*(\d+)", name, flags=re.I)
            if m:
                return int(m.group(1))
            sid = getattr(style, "style_id", "") or ""
            m2 = re.search(r"heading\s*(\d+)", sid, flags=re.I)
            if m2:
                return int(m2.group(1))
        p = paragraph._p
        pPr = getattr(p, "pPr", None)
        if pPr is not None:
            el = pPr._element
            vals = el.xpath(
                './/w:outlineLvl/@w:val',
                namespaces={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            )
            if vals:
                return int(vals[0]) + 1
    except Exception:
        return None
    return None

docx_path = pathlib.Path("pilot_inputs/reviews/4_1.docx")
d = Document(str(docx_path))
rq = None
h = []
for p in d.paragraphs:
    txt = collapse_ws(p.text)
    if not txt: 
        continue
    lvl = detect_heading_level(p)
    if lvl == 1 and not rq:
        rq = txt
    if lvl in (2,3,4):
        h.append((lvl, txt))

print("Heading 1 (research question):", rq)
print("H2/H3/H4 count:", len(h))
for lv, t in h[:12]:
    print(f"H{lv}: {t}")
