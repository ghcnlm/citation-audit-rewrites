import json, pathlib, sys

src = pathlib.Path("outputs/adjudication_inputs.jsonl")
if not src.exists():
    print("ERROR: outputs/adjudication_inputs.jsonl not found.")
    sys.exit(1)

data = src.read_text(encoding="utf-8")

objs = []
start = None
brace = 0
in_str = False
esc = False

for i, ch in enumerate(data):
    if in_str:
        if esc:
            esc = False
        elif ch == '\\\\':
            esc = True
        elif ch == '"':
            in_str = False
        continue
    else:
        if ch == '"':
            in_str = True
            if start is None:
                # if we see a quote before '{', ignore until we hit '{'
                pass
        elif ch == '{':
            if brace == 0:
                start = i
            brace += 1
        elif ch == '}':
            if brace > 0:
                brace -= 1
                if brace == 0 and start is not None:
                    chunk = data[start:i+1]
                    objs.append(chunk)
                    start = None

# Write a normalized JSONL (one object per line), verifying each chunk
out_path = src  # overwrite same file
good = 0
bad = 0
with out_path.open("w", encoding="utf-8", newline="\n") as f:
    for chunk in objs:
        try:
            obj = json.loads(chunk)
        except Exception as e:
            bad += 1
            continue
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        good += 1

print(f"Found chunks: {len(objs)}  Wrote valid: {good}  Skipped invalid: {bad}")
