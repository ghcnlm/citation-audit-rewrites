# Snapshot Overview
- **Snapshot ID**: snapshot_2025-09-08
- **Commit SHA**: 2412c31
- **Primary entrypoints**: python -m scripts.11_extract_and_enrich_DIRECT ; python scripts/50_adjudicate.py
- **How to run (happy path)**: one command, minimal flags
- **Typical errors**: Missing PDFs in pilot_inputs/sources_pdf ; Citation mismatch errors
- **Must-see files**: scripts/11_extract_and_enrich_DIRECT.py ; scripts/50_adjudicate.py ; scripts/52_propose_rewrites.py ; outputs/ccp_registry_enriched.csv