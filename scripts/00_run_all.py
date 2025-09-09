# scripts/00_run_all.py
# Orchestrates the pipeline end-to-end from the canonical enriched registry.
# Python 3.10+. Requires pandas, pyyaml.

from __future__ import annotations
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
OUT = ROOT / "outputs"

def run_module(modname: str, *args: str) -> None:
    """Run a module like 'scripts.50_adjudicate'."""
    cmd = [sys.executable, "-m", modname]
    if args:
        cmd += list(args)
    subprocess.check_call(cmd)

def main():
    OUT.mkdir(exist_ok=True)

    # 0) (Optional) Extractor if you still use it. Ignore failure if already done.
    try:
        run_module("scripts.11_extract_and_enrich_DIRECT")
    except Exception as e:
        print("[WARN] extractor step skipped:", e)

    # 1) Adjudications for ALL enriched rows (603 in current dataset)
    run_module("scripts.50_adjudicate")

    # 2) Proposed rewrites (non-dropping; fills only for UNSUPPORTED_FAIL)
    run_module("scripts.52_propose_rewrites")

    # 3) Canonical corrections list
    run_module("scripts.90_build_corrections_list")

    print("\n[OK] Pipeline complete. See outputs/ for artifacts.")

if __name__ == "__main__":
    main()
