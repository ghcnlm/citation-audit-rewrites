import json, math, pathlib, sys

p = pathlib.Path("outputs/adjudication_inputs.jsonl")
if not p.exists():
    print("adjudication_inputs.jsonl not found")
    sys.exit(1)

raw = p.read_text(encoding="utf-8", errors="replace")

objs, i, n, depth, start, in_str, esc = [], 0, len(raw), 0, None, False, False
while i < n:
    ch = raw[i]
    if in_str:
        if esc:
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            in_str = False
    else:
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    chunk = raw[start:i+1]
                    try:
                        obj = json.loads(chunk)
                        objs.append(obj)
                    except Exception as e:
                        print("Bad chunk skipped:", e)
                    start = None
    i += 1

if not objs:
    print("No JSON objects extracted")
    sys.exit(2)

def clean_nan(x):
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    if isinstance(x, dict):
        return {k: clean_nan(v) for k,v in x.items()}
    if isinstance(x, list):
        return [clean_nan(v) for v in x]
    return x

objs = [clean_nan(o) for o in objs]
out = "\n".join(json.dumps(o, ensure_ascii=False) for o in objs)
p.write_text(out, encoding="utf-8")

print(f"Wrote {len(objs)} JSON objects back to", p)
