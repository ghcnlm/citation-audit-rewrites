import json, sys, os
from typing import Iterable, Dict, Any

CANDIDATE_ARRAY_KEYS = [
    "records","items","data","rows","results","entries",
    "docs","objects","payload"
]

def _compact(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def _detect_rows(obj: Any):
    if isinstance(obj, list):
        if all(isinstance(x, dict) for x in obj):
            return obj
        raise ValueError("Top-level list exists but not all elements are JSON objects.")
    if isinstance(obj, dict):
        for k in CANDIDATE_ARRAY_KEYS:
            if k in obj and isinstance(obj[k], list) and all(isinstance(x, dict) for x in obj[k]):
                return obj[k]
        list_fields = [v for v in obj.values() if isinstance(v, list) and all(isinstance(x, dict) for x in v)]
        if len(list_fields) == 1:
            return list_fields[0]
        if obj and all(isinstance(v, dict) for v in obj.values()):
            return list(obj.values())
    raise ValueError("Could not detect a list of JSON objects inside the top-level data structure.")

def _brace_split(text: str):
    objs, depth, start, in_str, esc = [], 0, None, False, False
    for i, ch in enumerate(text):
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue
            if ch == "{":
                if depth == 0: start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    objs.append(text[start:i+1]); start = None
    return objs

def main(path: str, out_path: str):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    rows = None
    try:
        loaded = json.loads(raw)
        rows = _detect_rows(loaded)
    except Exception:
        pass

    if rows is None:
        objs = _brace_split(raw)
        if objs:
            parsed = []
            for idx, o in enumerate(objs, 1):
                try:
                    d = json.loads(o)
                except Exception as e:
                    raise ValueError(f"Fallback parse failed on object #{idx}: {e}") from e
                if not isinstance(d, dict):
                    raise ValueError(f"Fallback parse found non-object at #{idx}.")
                parsed.append(d)
            rows = parsed

    if rows is None:
        raise SystemExit("ERROR: Could not recover records from input. Aborting.")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as w:
        for rec in rows:
            w.write(_compact(rec) + "\n")

    print(f"OK: Wrote {len(rows)} JSON objects to {out_path}")

    valid = 0
    with open(out_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            s = line.strip()
            if not s: continue
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    valid += 1
                else:
                    raise ValueError("line is not a JSON object")
            except Exception as e:
                raise SystemExit(f"Validation failed on line {i}: {e}")
    print(f"Validation: {valid} valid lines, 0 invalid.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.fix_adjudication_jsonl <path> [out_path]")
        sys.exit(2)
    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) >= 3 else in_path
    if os.path.abspath(in_path) == os.path.abspath(out_path):
        import shutil
        bak = in_path + ".bak"
        shutil.copyfile(in_path, bak)
        print(f"Backup written to {bak}")
    main(in_path, out_path)
