import pathlib, sys, json

p = pathlib.Path("outputs/adjudication_inputs.jsonl")
if not p.exists():
    print("ERROR: outputs/adjudication_inputs.jsonl not found.")
    sys.exit(1)

raw = p.read_text(encoding="utf-8", errors="replace")

# Extract balanced JSON objects even if they're jammed together on one line.
# This parser tracks quotes and escapes so braces inside strings don't break it.
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
                    # try parse; if it fails, skip silently
                    try:
                        obj = json.loads(chunk)
                        objs.append(obj)
                    except Exception:
                        pass
                    start = None
    i += 1

if not objs:
    print("Failed to extract any JSON objects.")
    sys.exit(2)

out = "\\n".join(json.dumps(o, ensure_ascii=False) for o in objs)
p.write_text(out, encoding="utf-8")
print(f"Extracted {len(objs)} JSON objects -> rewrote as JSONL.")
