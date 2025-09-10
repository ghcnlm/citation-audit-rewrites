#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
52_propose_rewrites.py
Propose rewrites for problematic claims based on adjudication output.

Inputs:
  - outputs/adjudications_with_rewrites.csv
  - outputs/ccp_registry_enriched.csv (for research_question / context)
  - prompts/rewriter_system.txt
  - prompts/rewriter_user.jinja
  - prompts/rewriter_json_schema.json

Output:
  - updates outputs/adjudications_with_rewrites.csv (fills proposed_rewrite / rewrite_notes / rewrite_flags)
"""

from __future__ import annotations
from pathlib import Path
import json, os, sys, yaml, re
import pandas as pd
from jinja2 import Environment, BaseLoader

try:
    from openai import OpenAI
except Exception:
    print("OpenAI SDK is required. Run: pip install openai>=1.3.0")
    sys.exit(2)

ROOT   = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))

OUT_DIR = Path(CONFIG["paths"]["outputs_dir"])
PROMPTS = ROOT / "prompts"

MODEL      = CONFIG["llm"]["model"]
TEMP       = float(CONFIG["llm"].get("temperature", 0.0))
MAX_OUTTOK = int(CONFIG["llm"].get("max_output_tokens", 800))

WR_CSV   = OUT_DIR / "adjudications_with_rewrites.csv"
ENRICHED = OUT_DIR / "ccp_registry_enriched.csv"

SYSTEM_TXT  = (PROMPTS / "rewriter_system.txt").read_text(encoding="utf-8")
USER_TMPL   = (PROMPTS / "rewriter_user.jinja").read_text(encoding="utf-8")
JSON_SCHEMA = json.loads((PROMPTS / "rewriter_json_schema.json").read_text(encoding="utf-8"))

env = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True)
user_template = env.from_string(USER_TMPL)

NEGATIVE_VERDICTS = {"UNSUPPORTED_FAIL", "AMBIGUOUS_REVIEW", "PARTIAL_PASS", "SUPPORTED_PASS_WITH_FIX"}

def clean_and_parse_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}

def normalize_rewrite(d: dict) -> dict:
    d = d or {}
    pr = d.get("proposed_rewrite", "") or ""
    rn = d.get("rewrite_notes", "") or ""
    rf = d.get("rewrite_flags", [])
    if isinstance(rf, str):
        rf = [rf] if rf else []
    return {"proposed_rewrite": pr, "rewrite_notes": rn, "rewrite_flags": rf}

def call_llm(client: OpenAI, user_prompt: str) -> dict:
    # Try Responses API first
    try:
        resp = client.responses.create(
            model=MODEL,
            temperature=TEMP,
            max_output_tokens=MAX_OUTTOK,
            input=[
                {"role": "system", "content": SYSTEM_TXT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "rewrite", "schema": JSON_SCHEMA},
            },
        )
        parsed = clean_and_parse_json(getattr(resp, "output_text", "") or "")
        out = normalize_rewrite(parsed)
        if out["proposed_rewrite"]:
            return out
    except TypeError:
        pass
    except Exception:
        pass

    # Fallback: Chat Completions JSON mode
    try:
        comp = client.chat.completions.create(
            model=MODEL,
            temperature=TEMP,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_TXT + "\nReturn ONLY a single JSON object; no prose."},
                {"role": "user", "content": user_prompt},
            ],
        )
        parsed = clean_and_parse_json(comp.choices[0].message.content)
        out = normalize_rewrite(parsed)
        if out["proposed_rewrite"]:
            return out
    except Exception:
        pass

    # Last resort: plain chat
    try:
        comp = client.chat.completions.create(
            model=MODEL,
            temperature=TEMP,
            messages=[
                {"role": "system", "content": SYSTEM_TXT + "\nRespond ONLY with a JSON object containing proposed_rewrite, rewrite_notes, rewrite_flags (array)."},
                {"role": "user", "content": user_prompt},
            ],
        )
        parsed = clean_and_parse_json(comp.choices[0].message.content)
        return normalize_rewrite(parsed)
    except Exception:
        return {"proposed_rewrite":"","rewrite_notes":"","rewrite_flags":[]}

def main(limit: int | None = None):
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set.")
        sys.exit(2)

    if not WR_CSV.exists():
        print(f"Missing {WR_CSV}. Run 50_adjudicate.py first.")
        sys.exit(2)

    wr = pd.read_csv(WR_CSV, dtype=str).fillna("")
    rq = pd.read_csv(ENRICHED, dtype=str).fillna("") if ENRICHED.exists() else pd.DataFrame()
    if not rq.empty:
        cols = [c for c in ["review_id","claim_id","research_question"] if c in rq.columns]
        rq = rq[cols].copy()
        wr = wr.merge(rq, how="left", on=["review_id","claim_id"]) if "claim_id" in wr.columns else wr

    need = (
        (wr["proposed_rewrite"].str.len() == 0) &
        (
            wr["required_fix"].str.len() > 0
            | wr["verdict"].isin(NEGATIVE_VERDICTS)
        )
    )
    todo = wr[need].copy()
    if limit:
        todo = todo.head(limit)

    if todo.empty:
        print("[INFO] Nothing to rewrite.")
        return

    client = OpenAI()
    updates = []
    for _, r in todo.iterrows():
        ctx = {
            "claim_text": r.get("claim_text",""),
            "verdict": r.get("verdict",""),
            "required_fix": r.get("required_fix",""),
            "risk_flags": r.get("risk_flags",""),
            "research_question": r.get("research_question",""),
            "citation_author": r.get("citation_author",""),
            "citation_year": r.get("citation_year",""),
        }
        user_prompt = user_template.render(**ctx)
        data = call_llm(client, user_prompt)
        updates.append((
            r.name,
            data.get("proposed_rewrite",""),
            data.get("rewrite_notes",""),
            ";".join(data.get("rewrite_flags", []))
        ))

    for idx, pr, rn, rf in updates:
        wr.loc[idx, "proposed_rewrite"] = pr
        wr.loc[idx, "rewrite_notes"] = rn
        wr.loc[idx, "rewrite_flags"] = rf

    wr.to_csv(WR_CSV, index=False, encoding="utf-8")
    print(f"[OK] updated {WR_CSV} | rewrites added: {len(updates)}")

if __name__ == "__main__":
    lim = None
    if len(sys.argv) >= 2 and sys.argv[1].isdigit():
        lim = int(sys.argv[1])
    main(limit=lim)
