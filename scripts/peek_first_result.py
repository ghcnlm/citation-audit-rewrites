import json
import logging
import pathlib
import sys
import importlib

sys.path.insert(0, str(pathlib.Path("src").resolve()))
from audit_lib.llm import _load_file, LLMClient
from jinja2 import Template

M = importlib.import_module("scripts.50_adjudicate")

SYSTEM_PATH = getattr(M, "SYSTEM_PATH", pathlib.Path("prompts/adjudicator_system.txt"))
USER_TMPL   = getattr(M, "USER_TMPL",   pathlib.Path("prompts/adjudicator_user.jinja"))
SCHEMA_PATH = getattr(M, "SCHEMA_PATH", pathlib.Path("prompts/adjudicator_json_schema.json"))
MODEL       = getattr(M, "MODEL")

# Basic logging config for a quick preview script
logging.basicConfig(level=logging.INFO)

with open("outputs/adjudication_inputs.jsonl", "r", encoding="utf-8") as f:
    line = next(l for l in f if l.strip())
obj = json.loads(line)

system_prompt = _load_file(SYSTEM_PATH)
tmpl = Template(_load_file(str(USER_TMPL)))
user_prompt = tmpl.render(
    claim_text=obj["claim_text"],
    review_context="",
    citation_text=obj.get("citation_text",""),
    citation_type=obj.get("citation_type",""),
    is_secondary=obj.get("is_secondary", False),
    primary_mentioned_author=obj.get("primary_mentioned_author",""),
    primary_mentioned_year=obj.get("primary_mentioned_year",""),
    stated_page=obj.get("stated_page",""),
    source_author=obj["citation_author"],
    source_year=obj["citation_year"],
    source_pdf_path=obj["source_pdf_path"],
    evidence=obj["evidence"][:3]
)
schema = json.loads(_load_file(SCHEMA_PATH))
client = LLMClient(model=MODEL)
res = client.json_call(system_prompt, user_prompt, schema)
logging.info("Returned keys: %s", list(res.keys()))
logging.info(json.dumps(res, ensure_ascii=False, indent=2))