import re
HEAD_RE = re.compile(r"^\s*(references|bibliography)\s*$", re.I)
ENTRY_RE = re.compile(r"^\s*([A-Z][A-Za-z'’\-]+)[^()]*\(\s*(\d{4}[a-z]?)\s*\)")
def extract_references_blocks(text: str) -> str:
    lines = text.splitlines()
    started = False
    buf = []
    for ln in lines:
        if not started and HEAD_RE.match(ln):
            started = True
            continue
        if started:
            buf.append(ln)
    return "\n".join(buf)
def index_references(text: str, review_id: str):
    block = extract_references_blocks(text)
    out = []
    for line in block.splitlines():
        m = ENTRY_RE.match(line.strip())
        if m:
            first_author, year = m.groups()
            out.append({
                "review_id": review_id,
                "first_author": first_author.strip(),
                "year": year.strip(),
                "raw_line": line.strip()
            })
    return out
