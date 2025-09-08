import re, json, pathlib

p = pathlib.Path("outputs/adjudication_inputs.jsonl")
raw = p.read_text(encoding="utf-8")

# Split into { ... } blocks
chunks = re.findall(r"\{.*?\}(?=\s*\{|\s*$)", raw, flags=re.S)
print(f"Found {len(chunks)} JSON-like chunks")

objs = []
for i, ch in enumerate(chunks, 1):
    try:
        # replace NaN/Infinity which are not valid JSON
        fixed = ch.replace("NaN", "null").replace("Infinity","null")
        objs.append(json.loads(fixed))
    except Exception as e:
        print(f"Chunk {i} failed: {e}")

# Write back as JSONL
out = "\n".join(json.dumps(o, ensure_ascii=False) for o in objs)
p.write_text(out, encoding="utf-8")
print(f"Normalized JSONL: wrote {len(objs)} records to {p}")
