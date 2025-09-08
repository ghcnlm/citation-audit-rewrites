import json, re, pathlib, sys

p = pathlib.Path("outputs/adjudication_inputs.jsonl")
if not p.exists():
    print("ERROR: outputs/adjudication_inputs.jsonl not found.")
    sys.exit(1)

raw = p.read_text(encoding="utf-8").strip()

records = []
def try_add(obj):
    if isinstance(obj, dict):
        records.append(obj)
    elif isinstance(obj, list):
        for x in obj:
            if isinstance(x, dict):
                records.append(x)

# Case A: already JSONL (multiple lines)
lines = raw.splitlines()
if len(lines) > 1:
    ok = 0
    for ln in lines:
        s = ln.strip()
        if not s: 
            continue
        try:
            records.append(json.loads(s))
            ok += 1
        except Exception:
            pass
    if ok == len([ln for ln in lines if ln.strip()]):
        # already good, just rewrite normalized
        out = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
        p.write_text(out, encoding="utf-8")
        print(f"Normalized JSONL: {len(records)} records.")
        sys.exit(0)
    else:
        # fallthrough to smart parsing
        records = []

# Case B: full JSON array
if raw.startswith("["):
    try:
        try_add(json.loads(raw))
        if records:
            out = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
            p.write_text(out, encoding="utf-8")
            print(f"Converted JSON array -> JSONL: {len(records)} records.")
            sys.exit(0)
    except Exception:
        pass

# Case C: concatenated objects like "{}{}{}" on one line (or with whitespace)
chunks = re.findall(r"\{.*?\}(?=\s*\{|\s*$)", raw, flags=re.S)
if chunks:
    ok=0
    for ch in chunks:
        try:
            records.append(json.loads(ch))
            ok+=1
        except Exception:
            # try to strip trailing commas inside objects
            ch2 = re.sub(r",\s*([}\]])", r"\1", ch)
            try:
                records.append(json.loads(ch2))
                ok+=1
            except Exception:
                pass
    if ok:
        out = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
        p.write_text(out, encoding="utf-8")
        print(f"Split concatenated objects -> JSONL: {len(records)} records.")
        sys.exit(0)

# Case D: last-ditch — try to remove BOM & stray trailing commas and parse as array
clean = raw.encode("utf-8-sig").decode("utf-8-sig")
clean = re.sub(r",\s*([}\]])", r"\1", clean)
if clean.startswith("["):
    try:
        try_add(json.loads(clean))
        if records:
            out = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
            p.write_text(out, encoding="utf-8")
            print(f"Recovered JSON array with cleanup -> JSONL: {len(records)} records.")
            sys.exit(0)
    except Exception:
        pass

print("Failed to repair adjudication_inputs.jsonl; still not valid.")
sys.exit(2)
