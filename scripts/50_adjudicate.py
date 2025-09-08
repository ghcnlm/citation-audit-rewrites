# scripts/50_adjudicate.py
# -*- coding: utf-8 -*-
"""
Adjudicate claims -> write ONLY outputs/adjudications_with_rewrites.csv (no adjudications.csv).
Columns include empty rewrite fields that 52_propose_rewrites.py will fill in-place.
"""

import csv, json, sys
from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Template
import yaml
from tqdm import tqdm

sys.path.insert(0, str(Path("src").resolve()))
from audit_lib.llm import _load_file, openai_call  # uses your existing helpers

CFG = yaml.safe_load(open("config/config.yaml","r",encoding="utf-8"))

OUT_DIR = Path(CFG["paths"]["outputs_dir"])
INPUTS_JSONL = OUT_DIR / "adjudication_inputs.jsonl"
PROMPTS_DIR = Path("prompts")

SYSTEM_PATH = PROMPTS_DIR / "adjudicator_system.txt"
USER_TMPL   = PROMPTS_DIR / "adjudicator_user.jinja"
SCHEMA_PATH = PROMPTS_DIR / "adjudicator_json_schema.json"

MODEL = CFG["llm"]["model"]
TEMP  = float(CFG["llm"]["temperature"])

CONSOLIDATED = OUT_DIR / "adjudications_with_rewrites.csv"

BASE_COLS = [
    "review_id","section","claim_id","claim_text",
    "citation_author","citation_year","source_pdf_path",
    "verdict","rationale","evidence_span","required_fix","risk_flags"
]
REWRITE_COLS = ["proposed_rewrite","page_anchor","rewrite_notes","rewrite_flags"]
ALL_COLS = BASE_COLS + REWRITE_COLS

def read_inputs(path: Path) -> List[Dict[str,Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            rows.append(json.loads(s))
    return rows

def main():
    if not INPUTS_JSONL.exists():
        print(f"ERROR: {INPUTS_JSONL} not found. Ensure retrieval produced it.", file=sys.stderr)
        sys.exit(2)

    system_prompt = _load_file(SYSTEM_PATH)
    user_template = Template(_load_file(str(USER_TMPL)))
    schema = json.loads(_load_file(SCHEMA_PATH))

    inputs = read_inputs(INPUTS_JSONL)
    out_rows: List[Dict[str,Any]] = []

    for x in tqdm(inputs, desc="Adjudicating"):
        ctx = dict(
            claim_text=x.get("claim_text",""),
            citation_text=x.get("citation_text",""),
            citation_type=x.get("citation_type",""),
            is_secondary=x.get("is_secondary", False),
            primary_mentioned_author=x.get("primary_mentioned_author") or "",
            primary_mentioned_year=x.get("primary_mentioned_year") or "",
            stated_page=x.get("stated_page") or "",
            source_author=x.get("citation_author",""),
            source_year=x.get("citation_year",""),
            source_pdf_path=x.get("source_pdf_path",""),
            evidence=x.get("evidence", []) or []
        )
        user_prompt = user_template.render(**ctx)

        try:
            res = openai_call(MODEL, system_prompt, user_prompt, schema)
        except Exception as e:
            # On failure, emit UNSUPPORTED with a flag so pipeline continues
            res = {
                "verdict": "UNSUPPORTED_FAIL",
                "rationale": f"LLM error: {e}",
                "evidence_span": "",
                "required_fix": None,
                "risk_flags": ["llm_error"]
            }

        row = {
            "review_id": x.get("review_id",""),
            "section": x.get("section",""),
            "claim_id": x.get("claim_id",""),
            "claim_text": x.get("claim_text",""),
            "citation_author": x.get("citation_author",""),
            "citation_year": x.get("citation_year",""),
            "source_pdf_path": x.get("source_pdf_path",""),
            "verdict": res.get("verdict",""),
            "rationale": res.get("rationale",""),
            "evidence_span": res.get("evidence_span",""),
            "required_fix": (res.get("required_fix") if res.get("required_fix") is not None else ""),
            "risk_flags": ";".join(res.get("risk_flags", []) if isinstance(res.get("risk_flags", []), list) else [str(res.get("risk_flags"))]),
            # rewrite fields start empty
            "proposed_rewrite": "",
            "page_anchor": "",
            "rewrite_notes": "",
            "rewrite_flags": ""
        }
        out_rows.append(row)

    CONSOLIDATED.parent.mkdir(parents=True, exist_ok=True)
    with open(CONSOLIDATED, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ALL_COLS)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print(f"[OK] wrote consolidated adjudications -> {CONSOLIDATED}")

if __name__ == "__main__":
    main()