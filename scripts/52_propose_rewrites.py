# scripts/52_propose_rewrites.py
# -*- coding: utf-8 -*-
"""
Generate evidence-based rewrites for UNSUPPORTED_FAIL and update the SAME file:
outputs/adjudications_with_rewrites.csv  (in-place).
Optionally also emit outputs/proposed_rewrites.csv with --emit-proposed.
"""

import csv, json, sys, argparse
from pathlib import Path
from typing import Dict, List, Any
from jinja2 import Template
import yaml

# Make sure we can import from src/
sys.path.insert(0, str(Path("src").resolve()))
from audit_lib.llm import _load_file, openai_call  # your existing helper

# ---------- Config ----------
CFG = yaml.safe_load(open("config/config.yaml","r",encoding="utf-8"))

OUT_DIR = Path(CFG["paths"]["outputs_dir"])
ENRICHED = OUT_DIR / "ccp_registry_enriched.csv"
INPUTS_JSONL = OUT_DIR / "adjudication_inputs.jsonl"
CONSOLIDATED = OUT_DIR / "adjudications_with_rewrites.csv"

PROMPTS_DIR = Path("prompts")
SYSTEM_PATH = PROMPTS_DIR / "rewriter_system.txt"
USER_TMPL   = PROMPTS_DIR / "rewriter_user.jinja"
SCHEMA_PATH = PROMPTS_DIR / "rewriter_json_schema.json"

MODEL = (CFG.get("rewriter", {}) or {}).get("model", CFG["llm"]["model"])
TEMP  = float((CFG.get("rewriter", {}) or {}).get("temperature", CFG["llm"]["temperature"]))
MAX_EXCERPTS = int((CFG.get("rewriter", {}) or {}).get("max_excerpts", 6))

# ---------- IO helpers ----------
def read_csv_dict(path: Path) -> List[Dict[str,str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: List[Dict[str,Any]], cols: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def read_inputs_jsonl(path: Path) -> Dict[str,Dict]:
    m: Dict[str,Dict] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s: continue
            obj = json.loads(s)
            cid = str(obj.get("claim_id",""))
            if cid: m[cid] = obj
    return m

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="Max UNSUPPORTED_FAIL rows to process")
    ap.add_argument("--only-review", type=str, default="", help="Process a single review_id")
    ap.add_argument("--emit-proposed", action="store_true", help="Also write outputs/proposed_rewrites.csv")
    args = ap.parse_args()

    # Preconditions
    if not CONSOLIDATED.exists():
        print(f"ERROR: {CONSOLIDATED} not found. Run 50_adjudicate.py first.", file=sys.stderr)
        sys.exit(2)
    if not ENRICHED.exists():
        print(f"ERROR: {ENRICHED} not found. Run enrichment first.", file=sys.stderr)
        sys.exit(2)
    if not INPUTS_JSONL.exists():
        print(f"ERROR: {INPUTS_JSONL} not found. Ensure retrieval produced it.", file=sys.stderr)
        sys.exit(2)
    for p in (SYSTEM_PATH, USER_TMPL, SCHEMA_PATH):
        if not p.exists():
            print(f"ERROR: Missing prompt file: {p}. Create it under prompts/ as instructed.", file=sys.stderr)
            sys.exit(2)

    consolidated = read_csv_dict(CONSOLIDATED)
    enriched_rows = read_csv_dict(ENRICHED)
    enriched = {(r.get("review_id",""), r.get("claim_id","")): r for r in enriched_rows}
    inputs_by_claim = read_inputs_jsonl(INPUTS_JSONL)

    system_prompt = _load_file(SYSTEM_PATH)
    user_template = Template(_load_file(str(USER_TMPL)))
    schema = json.loads(_load_file(SCHEMA_PATH))

    targets = [r for r in consolidated if r.get("verdict","") == "UNSUPPORTED_FAIL"]
    if args.only_review:
        targets = [r for r in targets if r.get("review_id","") == args.only_review]
    if args.limit and len(targets) > args.limit:
        targets = targets[:args.limit]

    # Index consolidated by (review_id, claim_id) to update rows in-place
    index = {(r.get("review_id",""), r.get("claim_id","")): i for i, r in enumerate(consolidated)}
    proposed_rows = []

    for row in targets:
        rid = row.get("review_id",""); cid = row.get("claim_id","")
        enr = enriched.get((rid, cid), {})
        inp = inputs_by_claim.get(cid, {})

        evidence = (inp.get("evidence", []) or [])[:MAX_EXCERPTS]
        ctx = dict(
            research_question=enr.get("research_question",""),
            section_title=enr.get("section_title") or enr.get("section_canonical",""),
            claim_text=enr.get("claim_text","") or row.get("claim_text",""),
            citation_author=inp.get("citation_author", row.get("citation_author","")),
            citation_year=inp.get("citation_year", row.get("citation_year","")),
            source_pdf_path=inp.get("source_pdf_path", row.get("source_pdf_path","")),
            evidence=evidence
        )

        # Render + call LLM
        user_msg = user_template.render(**ctx)
        try:
            res = openai_call(MODEL, system_prompt, user_msg, schema) or {}
        except Exception as e:
            res = {"proposed_rewrite":"", "page_anchor":"", "notes":f"LLM error: {e}", "risk_flags":["llm_error"]}

        # Update in-place
        idx = index[(rid, cid)]
        consolidated[idx]["proposed_rewrite"] = (res.get("proposed_rewrite") or "").strip()
        consolidated[idx]["page_anchor"] = (res.get("page_anchor") or "").strip()
        consolidated[idx]["rewrite_notes"] = res.get("notes","")
        rf = res.get("risk_flags", [])
        if isinstance(rf, str): rf = [rf]
        consolidated[idx]["rewrite_flags"] = ";".join(rf or [])

        proposed_rows.append({
            "review_id": rid, "claim_id": cid,
            "proposed_rewrite": consolidated[idx]["proposed_rewrite"],
            "page_anchor": consolidated[idx]["page_anchor"],
            "source_pdf_path": consolidated[idx].get("source_pdf_path",""),
            "section_title": ctx["section_title"],
            "research_question": ctx["research_question"],
            "notes": consolidated[idx]["rewrite_notes"],
            "risk_flags": consolidated[idx]["rewrite_flags"],
        })

    # Write back the SAME consolidated file (preserve original column order)
    cols = list(consolidated[0].keys()) if consolidated else []
    write_csv(CONSOLIDATED, consolidated, cols)
    print(f"[OK] updated in-place -> {CONSOLIDATED}")

    if args.emit_proposed:
        proposed = OUT_DIR / "proposed_rewrites.csv"
        write_csv(proposed, proposed_rows,
                  ["review_id","claim_id","proposed_rewrite","page_anchor","source_pdf_path",
                   "section_title","research_question","notes","risk_flags"])
        print(f"[OK] wrote -> {proposed}")

if __name__ == "__main__":
    main()