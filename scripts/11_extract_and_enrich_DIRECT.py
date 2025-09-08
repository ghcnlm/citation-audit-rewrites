# scripts/11_extract_and_enrich_DIRECT.py
# -*- coding: utf-8 -*-
"""
Run the existing extractor WITHOUT leaving raw outputs, then enrich in-memory:
  1) Backup config/config.yaml
  2) Write a TEMP config that redirects outputs_dir to a temp folder
  3) Run `python -m scripts.10_extract_ccps` (extractor) -> temp/ccp_registry.csv
  4) Read temp raw CSV
  5) Enrich (docx headings + PDF resolver) and write ONLY outputs/ccp_registry_enriched.csv
  6) Clean up temp and restore real config.yaml
"""

from __future__ import annotations
import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

import yaml

# import our enrichment library
sys.path.insert(0, str(Path("src").resolve()))
from audit_lib.enrich import enrich_registry_rows, write_enriched_csv  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

def _read_csv(path: Path) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def main():
    if not CONFIG_FILE.exists():
        raise SystemExit(f"ERROR: {CONFIG_FILE} not found")

    # Load the real config
    real_cfg = yaml.safe_load(open(CONFIG_FILE, "r", encoding="utf-8"))
    real_outputs_dir = REPO_ROOT / real_cfg["paths"]["outputs_dir"]
    real_reviews_dir = REPO_ROOT / real_cfg["paths"]["reviews_dir"]
    real_pdf_dir = REPO_ROOT / real_cfg["paths"]["pdf_dir"]

    # Create a temp working directory to capture the raw registry
    tmp_root = Path(tempfile.mkdtemp(prefix="ccp_tmp_"))
    try:
        tmp_outputs = tmp_root / "outputs"
        tmp_outputs.mkdir(parents=True, exist_ok=True)

        # Prepare a TEMP config.yaml that points outputs_dir to tmp_outputs
        temp_cfg = dict(real_cfg)
        temp_cfg_paths = dict(temp_cfg.get("paths", {}))
        temp_cfg_paths["outputs_dir"] = str(tmp_outputs)
        temp_cfg["paths"] = temp_cfg_paths

        # Backup real config and write the temp config
        backup_path = CONFIG_DIR / "config.yaml.bak"
        shutil.copy2(CONFIG_FILE, backup_path)
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as wf:
                yaml.safe_dump(temp_cfg, wf, sort_keys=False, allow_unicode=True)

            # Run the existing extractor against the TEMP config
            print("[RUN] extractor → temp outputs")
            subprocess.run(
                [sys.executable, "-m", "scripts.10_extract_ccps"],
                cwd=str(REPO_ROOT),
                check=True,
            )
        finally:
            shutil.copy2(backup_path, CONFIG_FILE)
            backup_path.unlink(missing_ok=True)

        # Read the TEMP raw registry
        tmp_raw = tmp_outputs / "ccp_registry.csv"
        if not tmp_raw.exists():
            raise SystemExit(
                f"ERROR: Expected {tmp_raw} not found. Ensure scripts/10_extract_ccps.py writes ccp_registry.csv."
            )
        raw_rows = _read_csv(tmp_raw)

        # Enrich in-memory and write ONLY the real enriched file (pass pdf_dir!)
        enriched_rows = enrich_registry_rows(raw_rows, REPO_ROOT / real_reviews_dir, REPO_ROOT / real_pdf_dir)
        real_enriched = REPO_ROOT / real_outputs_dir / "ccp_registry_enriched.csv"
        write_enriched_csv(enriched_rows, real_enriched)
        print(f"[OK] wrote enriched registry -> {real_enriched}")

    finally:
        try:
            shutil.rmtree(tmp_root)
        except Exception:
            pass

if __name__ == "__main__":
    main()