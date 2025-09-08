import os, json
from typing import Dict, Any, List
from jinja2 import Template
def _load_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
def render_user_prompt(tmpl_path: str, claim_text: str, review_context: str, source_author: str, source_year: str, source_pdf_path: str, evidence: List[Dict[str,str]]) -> str:
    tmpl = Template(_load_file(tmpl_path))
    return tmpl.render(
        claim_text=claim_text,
        review_context=review_context,
        source_author=source_author,
        source_year=source_year,
        source_pdf_path=source_pdf_path,
        evidence=evidence
    )
def openai_call(model: str, system_prompt: str, user_prompt: str, json_schema: Dict[str,Any], temperature: float=0.0, max_tokens: int=800) -> Dict[str,Any]:
    try:
        from openai import OpenAI
        client = OpenAI()
        try:
            resp = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type":"json_object"}
            )
            text = resp.output_text
        except Exception:
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role":"system","content": system_prompt},
                    {"role":"user","content": user_prompt}
                ],
                response_format={"type":"json_object"},
                max_tokens=max_tokens
            )
            text = resp.choices[0].message.content
        return json.loads(text)
    except Exception as e:
        return {"verdict":"UNSUPPORTED_FAIL","rationale":f"LLM error: {e}","evidence_span":"","required_fix":None,"risk_flags":["llm_error"]}
