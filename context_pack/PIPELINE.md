# Pipeline / Workflow
## Stages (data/control flow)
1) Ingest → inputs: pilot_inputs/reviews/*.docx, pilot_inputs/sources_pdf/*.pdf → outputs: extracted claims & citations
2) Enrich/Transform → resolve PDF names, normalize citations → outputs: outputs/ccp_registry_enriched.csv
3) Validate/Adjudicate → check support status; label FAIL/PASS → outputs: adjudication CSV/JSON
4) Propose Rewrites → generate evidence-based rewrites for UNSUPPORTED_FAIL → outputs: outputs/*_FIXED.csv

## Entrypoints / Orchestration
- CLI/Module: python -m scripts.11_extract_and_enrich_DIRECT, python scripts/50_adjudicate.py
- Make (if present): make audit
- CI (if present): .github/workflows/*.yml stages

## Notes
- Data & large artifacts excluded from VCS; share schemas or small samples only.
