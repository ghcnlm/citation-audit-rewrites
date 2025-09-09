#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
51_batch_llm_adjudicate.py
Create adjudication decisions with the LLM, robust to SDK capabilities.

Inputs:
  - outputs/adjudication_inputs.jsonl
  - prompts/adjudicator_system.txt
  - prompts/adjudicator_user.jinja
  - prompts/adjudicator_json_schema.json (via config.adjudication.json_schema_path)

Outputs:
  - outputs/adjudication_results.jsonl  (raw per-claim model JSON)
  - outputs/adjudications.csv           (tabular, ready for 50_adjudicate.py)
"""

from __future__ import annotations
from pathlib import Path
import json, os, sys, time, yaml, re
from typing import Dict, Any, Iterable, List
import pandas as pd
from jinja2 import Environment, BaseLoader

try:
    from openai import OpenAI
except Exception:
    print("OpenAI SDK is required. Run: pip install openai>=1.3.0")
    sys.exit(2)

ROOT   = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))

OUT_DIR    = Path(CONFIG["paths"]["outputs_dir"])
PROMPTS    = ROOT / "prompts"
MODEL      = CONFIG["llm"]["model"]
TEMP       = float(CONFIG["llm"].get("temperature", 0.0))
MAX_OUTTOK = int(CONFIG["llm"].get("max_output_tokens", 800))

SCHEMA_FP   = ROOT / CONFIG["adjudication"]["json_schema_path"]
SYSTEM_TXT  = (PROMPTS / "adjudicator_system.txt").read_text(encoding="utf-8")
USER_TMPL   = (PROMPTS / "adjudicator_user.jinja").read_text(encoding="utf-8")
JSON_SCHEMA = json.loads(SCHEMA_FP.read_text(encoding="utf-8"))

INPUTS_JSONL  = OUT_DIR / "adjudication_inputs.jsonl"
RESULTS_JSONL = OUT_DIR / "adjudication_results.jsonl"
ADJUDICATIONS = OUT_DIR / "adjudications.csv"

env = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True)
user_template = env.from_string(USER_TMPL)

def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Bad JSONL line {i}: {e}\nFirst 200 chars: {line[:200]}")

def render_user_prompt(item: Dict[str, Any]) -> str:
    # Make sure the user prompt itself tells the model to output only JSON when we use chat fallback.
    return user_template.render(**item)

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """
    Extract a JSON object from text (handles code fences and extra prose).
    """
    if not text:
        return {}
    # Strip code fences if present
    text = text.strip()
    if text.startswith("```"):
        # remove fencing and any leading language label
        text = re.sub(r"^```(json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Fallback: grab first {...} block
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        frag = m.group(0)
        try:
            return json.loads(frag)
        except Exception:
            pass
    return {}

def default_result() -> Dict[str, Any]:
    return {
        "verdict": "",
        "rationale": "",
        "evidence_span": "",
        "required_fix": "",
        "risk_flags": [],
        "page_anchor": "",
    }

def normalize_result(d: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(d, dict):
        d = {}
    out = default_result()
    out.update({k: d.get(k, out[k]) for k in out.keys()})
    # normalize risk flags to list -> semicolon join later
    rf = out.get("risk_flags", [])
    if isinstance(rf, str):
        rf = [rf] if rf else []
    out["risk_flags"] = rf
    for k, v in out.items():
        if v is None:
            out[k] = "" if k != "risk_flags" else []
    return out

def to_row(item: Dict[str, Any], resp: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "review_id": item.get("review_id",""),
        "section": item.get("section",""),
        "claim_id": item.get("claim_id",""),
        "claim_text": item.get("claim_text",""),
        "citation_author": item.get("citation_author",""),
        "citation_year": item.get("citation_year",""),
        "source_pdf_path": item.get("source_pdf_path",""),

        "verdict": resp.get("verdict",""),
        "rationale": resp.get("rationale",""),
        "evidence_span": resp.get("evidence_span",""),
        "required_fix": resp.get("required_fix",""),
        "risk_flags": ";".join(resp.get("risk_flags", [])),
        "page_anchor": resp.get("page_anchor",""),

        # downstream fields left blank; 52_* will fill
        "proposed_rewrite": "",
        "rewrite_notes": "",
        "rewrite_flags": "",
    }

def call_llm(client: OpenAI, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Try Responses API with schema -> fallback to Chat Completions JSON mode.
    Returns normalized dict.
    """
    # 1) Try Responses API + schema
    try:
        resp = client.responses.create(
            model=MODEL,
            temperature=TEMP,
            max_output_tokens=MAX_OUTTOK,
            input=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "adjudication", "schema": JSON_SCHEMA},
            },
        )
        parsed = clean_and_parse_json(getattr(resp, "output_text", "") or "")
        norm = normalize_result(parsed)
        if any(norm.values()) and norm.get("verdict", ""):
            return norm
    except TypeError as e:
        # Older SDK without response_format on responses.create
        pass
    except Exception:
        pass

    # 2) Fallback: Chat Completions with JSON mode
    try:
        # Add strong instruction: JSON only, no prose
        chat_messages = []
        chat_messages.append({"role": "system", "content": SYSTEM_TXT + "\nReturn ONLY a single JSON object; no prose."})
        # messages is a list of dicts with role+content already; append the user one(s)
        for m in messages:
            if m.get("role") == "user":
                chat_messages.append(m)

        comp = client.chat.completions.create(
            model=MODEL,
            temperature=TEMP,
            response_format={"type": "json_object"},
            messages=chat_messages,
        )
        content = comp.choices[0].message.content
        parsed = clean_and_parse_json(content)
        norm = normalize_result(parsed)
        if any(norm.values()) and norm.get("verdict", ""):
            return norm
    except Exception:
        pass

    # 3) As a last resort, do plain chat (no JSON mode) and parse loosely
    try:
        comp = client.chat.completions.create(
            model=MODEL,
            temperature=TEMP,
            messages=[
                {"role": "system", "content": SYSTEM_TXT + "\nRespond ONLY with a JSON object matching the keys: verdict, rationale, evidence_span, required_fix, risk_flags (array), page_anchor."},
                *[m for m in messages if m.get("role") == "user"],
            ],
        )
        content = comp.choices[0].message.content
        parsed = clean_and_parse_json(content)
        norm = normalize_result(parsed)
        return norm
    except Exception:
        return normalize_result({})

def main(limit: int | None = None, resume: bool = True):
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set.")
        sys.exit(2)
    if not INPUTS_JSONL.exists():
        print(f"Missing {INPUTS_JSONL}. Run 40_retrieve_candidates.py first.")
        sys.exit(2)

    client = OpenAI()

    # resume support: but only skip keys that already have a non-empty verdict
    done_keys = set()
    if resume and RESULTS_JSONL.exists():
        for obj in iter_jsonl(RESULTS_JSONL):
            k = obj.get("key")
            res = obj.get("result", {})
            v = (res or {}).get("verdict", "")
            if k and isinstance(v, str) and v.strip():
                done_keys.add(k)

    n_total = n_done = n_skipped = 0
    rows: List[Dict[str, Any]] = []
    rmode = "a" if RESULTS_JSONL.exists() else "w"

    with RESULTS_JSONL.open(rmode, encoding="utf-8") as fout:
        for item in iter_jsonl(INPUTS_JSONL):
            n_total += 1
            k = f"{item.get('review_id','')}|{item.get('section','')}|{item.get('claim_id','')}"
            if k in done_keys:
                n_skipped += 1
                continue
            if limit and n_done >= limit:
                break

            user_prompt = render_user_prompt(item)
            messages = [
                {"role": "system", "content": SYSTEM_TXT},
                {"role": "user", "content": user_prompt},
            ]

            data = call_llm(client, messages)
            fout.write(json.dumps({"key": k, "result": data}, ensure_ascii=False) + "\n")
            rows.append(to_row(item, data))
            n_done += 1
            if n_done % 10 == 0:
                print(f"[prog] adjudicated {n_done}")
            time.sleep(0.05)

    df_new = pd.DataFrame(rows)
    if ADJUDICATIONS.exists():
        old = pd.read_csv(ADJUDICATIONS, dtype=str).fillna("")
        keycols = ["review_id","section","claim_id"]
        # Put NEW first so new results override old blanks
        allp = pd.concat([df_new, old], ignore_index=True)
        allp = allp.drop_duplicates(subset=keycols, keep="first")
    else:
        allp = df_new

    allp.to_csv(ADJUDICATIONS, index=False, encoding="utf-8")
    print(f"[OK] wrote {ADJUDICATIONS} ({len(allp)} rows)  |  scanned={n_total} skipped={n_skipped} new={n_done}")

if __name__ == "__main__":
    lim = None
    if len(sys.argv) >= 2 and sys.argv[1].isdigit():
        lim = int(sys.argv[1])
    main(limit=lim, resume=True)
