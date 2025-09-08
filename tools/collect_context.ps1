$ErrorActionPreference = "SilentlyContinue"

# Ensure folders
New-Item -ItemType Directory -Force -Path context_pack,context_pack\SCRIPTS,context_pack\CONFIG_SAMPLES | Out-Null

# Snapshot marker
$snapshot = "snapshot_{0:yyyy-MM-dd}" -f (Get-Date)
$snapshot | Out-File -Encoding UTF8 context_pack\SNAPSHOT.txt

# ENVIRONMENT (tools & versions)
$envLines = @()
$envLines += "OS: $([System.Environment]::OSVersion.VersionString)"
$envLines += "Shell: PowerShell $($PSVersionTable.PSVersion)"
try { $envLines += (python -V) } catch {}
try { $envLines += (node -v) } catch {}
try { $envLines += (npm -v) } catch {}
try { $envLines += (poetry --version) } catch {}
try { $envLines += (conda --version) } catch {}
$envLines -join "`n" | Out-File -Encoding UTF8 context_pack\ENVIRONMENT.md

# Dependencies (best-effort)
try { pip freeze | Out-File -Encoding UTF8 context_pack\DEPENDENCIES.txt } catch {}
try { poetry export -f requirements.txt --without-hashes -o context_pack\DEPENDENCIES.poetry.txt } catch {}
try { conda env export --no-builds | Out-File -Encoding UTF8 context_pack\ENVIRONMENT.conda.yml } catch {}
try { npm ls --depth=0 | Out-File -Encoding UTF8 context_pack\DEPENDENCIES.npm.txt } catch {}

# ENTRYPOINT hints
# 1) Python __main__ guards
Get-ChildItem -Recurse -Include *.py -File |
  Select-String -Pattern 'if\s+__name__\s*==\s*["'']__main__["'']' |
  ForEach-Object { "$($_.Path):$($_.LineNumber): $($_.Line.Trim())" } |
  Out-File -Encoding UTF8 context_pack\ENTRYPOINTS.main_guards.txt

# 2) console_scripts / entry_points in pyproject/setup.cfg
Get-ChildItem -Path . -Include pyproject.toml,setup.cfg -File |
  ForEach-Object {
    "## FILE: $($_.FullName)"
    Get-Content $_.FullName
  } | Out-File -Encoding UTF8 context_pack\ENTRYPOINTS.python.txt

# 3) Makefile targets
if (Test-Path .\Makefile) {
  (Get-Content .\Makefile | Select-String -Pattern '^[A-Za-z0-9_.-]+:' ) |
    ForEach-Object { $_.Line } |
    Out-File -Encoding UTF8 context_pack\ENTRYPOINTS.make.txt
}

# 4) GitHub Actions workflow headers
if (Test-Path .github\workflows) {
  Get-ChildItem .github\workflows -Filter *.yml -File -Recurse |
    ForEach-Object {
      "## FILE: $($_.FullName)"
      (Get-Content $_.FullName | Select-String -Pattern '^(on:|jobs:)').Line
    } | Out-File -Encoding UTF8 context_pack\ENTRYPOINTS.github_actions.txt
}

# 5) npm scripts (dump package.json if present)
if (Test-Path .\package.json) {
  Get-Content .\package.json | Out-File -Encoding UTF8 context_pack\ENTRYPOINTS.npm.json
}

# README_CONTEXT.md
@"
# Snapshot Overview
- **Snapshot ID**: $snapshot
- **Commit SHA**: (fill after you push)
- **Primary entrypoints**: e.g., `python -m scripts.11_extract_and_enrich_DIRECT`, `python scripts/50_adjudicate.py`
- **How to run (happy path)**: one command, minimal flags
- **Typical errors**: brief bullets (e.g., missing PDFs, bad paths)
- **Must-see files**: list key scripts/configs to inspect first
"@ | Out-File -Encoding UTF8 context_pack\README_CONTEXT.md

# CODEMAP.md
@"
# CODEMAP (brief roles)
- `scripts/` — extract/enrich/adjudicate steps
- `configs/` — sanitized YAML/TOML/.env examples
- `outputs/` — (excluded) generated CSV/JSON; see schemas in docs
- `tests/` — (if present) unit/integration tests

See also: CODEMAP.tree (broad) and CODEMAP.raw (git-tracked).
"@ | Out-File -Encoding UTF8 context_pack\CODEMAP.md

# PIPELINE.md
@"
# Pipeline / Workflow
## Stages (data/control flow)
1) Ingest → inputs: `pilot_inputs/reviews/*.docx`, `pilot_inputs/sources_pdf/*.pdf` → outputs: extracted claims & citations
2) Enrich/Transform → resolve PDF names, normalize citations → outputs: `outputs/ccp_registry_enriched.csv`
3) Validate/Adjudicate → check support status; label FAIL/PASS → outputs: adjudication CSV/JSON
4) Propose Rewrites → generate evidence-based rewrites for UNSUPPORTED_FAIL → outputs: `outputs/*_FIXED.csv`

## Entrypoints / Orchestration
- CLI/Module: `python -m scripts.11_extract_and_enrich_DIRECT`, `python scripts/50_adjudicate.py`
- Make (if present): `make audit`
- CI (if present): `.github/workflows/*.yml` stages

## Notes
- Data & large artifacts excluded from VCS; share schemas or small samples only.
"@ | Out-File -Encoding UTF8 context_pack\PIPELINE.md

# PRIVACY_REDACTIONS.md
@"
Exclude secrets (.env, tokens, keys), PII, and proprietary datasets.
Provide sanitized templates under CONFIG_SAMPLES/ (e.g., .env.example, config.yaml.example).
"@ | Out-File -Encoding UTF8 context_pack\PRIVACY_REDACTIONS.md

Write-Host "Context pack files created."
