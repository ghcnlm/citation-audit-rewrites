import json, math, pathlib, sys

p = pathlib.Path("outputs/adjudication_inputs.jsonl")
if not p.exists():
    print("ERROR: outputs/adjudication_inputs.jsonl not found.")
    sys.exit(1)

raw = p.read_text(encoding="utf-8", errors="replace")

# --- brace-balanced extractor that respects strings/escapes ---
objs = []
i = 0
n = len(raw)
depth = 0
start = None
in_str = False
esc = False

while i < n:
    ch = raw[i]
    if in_str:
        if esc:
            esc = False
        elif ch == '\\\\':
            esc = True
        elif ch == '"':
            in_str = False
    else:
        if ch == '"':
            in_str = True
        elif ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    chunk = raw[start:i+1]
                    try:
                        # Python will parse NaN as float('nan'); we normalize later.
                        obj = json.loads(chunk)
                        objs.append(obj)
                    except Exception:
                        pass
                    start = None
    i += 1

if not objs:
    print("Failed to extract any JSON objects.")
    sys.exit(2)

# --- normalize NaN -> None recursively ---
def norm(x):
    if isinstance(x, float) and math.isnan(x):
        return None
    if isinstance(x, list):
        return [norm(v) for v in x]
    if isinstance(x, dict):
        return {k: norm(v) for k, v in x.items()}
    return x

objs = [norm(o) for o in objs]

# Write strict JSONL (no NaN allowed)
out_lines = []
for o in objs:
    out_lines.append(json.dumps(o, ensure_ascii=False, allow_nan=False))
out = "\n".join(out_lines)

p.write_text(out, encoding="utf-8")
print(f"Extracted and normalized -> {len(objs)} JSON objects written as JSONL.")
