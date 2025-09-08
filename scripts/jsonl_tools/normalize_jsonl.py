import json, pathlib, re, math

p = pathlib.Path("outputs/adjudication_inputs.jsonl")
raw = p.read_text(encoding="utf-8")

def try_parse_full_document(text):
    try:
        return json.loads(text)
    except Exception:
        return None

def emit_lines(objs):
    out = "\n".join(json.dumps(o, ensure_ascii=False) for o in objs)
    p.write_text(out, encoding="utf-8")
    return len(objs)

# 2a) Try parsing the whole file as a single JSON value
doc = try_parse_full_document(raw)

if isinstance(doc, list):
    # It's a JSON array of objects -> write each on its own line
    n = emit_lines(doc)
    print(f"Normalized: wrote {n} JSONL lines from JSON array.")
elif isinstance(doc, dict):
    # Look for common list keys
    for key in ("records", "items", "data", "lines"):
        if isinstance(doc.get(key), list):
            n = emit_lines(doc[key])
            print(f"Normalized: wrote {n} JSONL lines from top-level dict['{key}'].")
            break
    else:
        # Not a list-bearing dict. Fall back to regex chunking.
        chunks = re.findall(r"\{.*?\}(?=\s*\{|\s*$)", raw, flags=re.S)
        if chunks:
            objs = []
            for ch in chunks:
                try:
                    objs.append(json.loads(ch))
                except Exception:
                    pass
            n = emit_lines(objs)
            print(f"Normalized via regex: wrote {n} JSONL lines from concatenated objects.")
        else:
            # Just write back a single object per line if it's an object
            p.write_text(json.dumps(doc, ensure_ascii=False)+"\n", encoding="utf-8")
            print("Normalized: single JSON object written as one-line JSONL.")
else:
    # Not parseable as one document: split on brace chunks
    chunks = re.findall(r"\{.*?\}(?=\s*\{|\s*$)", raw, flags=re.S)
    objs = []
    for ch in chunks:
        try:
            objs.append(json.loads(ch))
        except Exception:
            pass
    if objs:
        n = emit_lines(objs)
        print(f"Normalized raw chunks: wrote {n} JSONL lines.")
    else:
        # last resort: nothing usable
        print("ERROR: could not normalize adjudication_inputs.jsonl")
