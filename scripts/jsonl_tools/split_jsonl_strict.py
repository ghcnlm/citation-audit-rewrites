import json, re, pathlib

p = pathlib.Path("outputs/adjudication_inputs.jsonl")
raw = p.read_text(encoding="utf-8")

# Split on objects (even if concatenated)
chunks = re.findall(r"\{.*?\}(?=\s*\{|\s*$)", raw, flags=re.S)

objs = []
for i, ch in enumerate(chunks, 1):
    try:
        objs.append(json.loads(ch))
    except Exception as e:
        print(f"Line {i} failed: {e}")

outpath = pathlib.Path("outputs/adjudication_inputs.jsonl")
outpath.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in objs), encoding="utf-8")
print(f"Strict split: wrote {len(objs)} records to {outpath}")
