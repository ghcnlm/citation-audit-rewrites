# scripts/00_run_all.py
from __future__ import annotations
import sys
import importlib.util
import subprocess

def have(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None

def runm(mod: str, *args: str) -> None:
    cmd = [sys.executable, "-m", mod] + list(args)
    print(">>> " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)

def main() -> int:
    # 1) Extract + enrich (optional)
    if have("scripts.11_extract_and_enrich_DIRECT"):
        runm("scripts.11_extract_and_enrich_DIRECT")
    else:
        print("[WARN] scripts/11_extract_and_enrich_DIRECT.py not found; skipping")

    # 2) Canonical builder (required for schema + source_pdf fill)
    try:
        runm("scripts.99_build_enriched_fixed")
    except subprocess.CalledProcessError as e:
        print("[ERROR] canonical build failed; see traceback above")
        return e.returncode

    # 3) Adjudication (optional)
    if have("scripts.50_adjudicate"):
        try:
            runm("scripts.50_adjudicate")
        except subprocess.CalledProcessError as e:
            print("[WARN] adjudication failed; continuing")
    else:
        print("[WARN] scripts/50_adjudicate.py not found; skipping")

    # 4) Rewrite proposals (optional)
    if have("scripts.52_propose_rewrites"):
        try:
            runm("scripts.52_propose_rewrites")
        except subprocess.CalledProcessError as e:
            print("[WARN] rewrite proposals failed; continuing")
    else:
        print("[WARN] scripts/52_propose_rewrites.py not found; skipping")

    print("[OK] run-all complete")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())