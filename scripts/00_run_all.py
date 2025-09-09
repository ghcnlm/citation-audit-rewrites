import sys
import subprocess
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

def run(cmd, cwd=REPO_ROOT):
    print(f"\n>>> {cmd}")
    res = subprocess.run(cmd, cwd=cwd, shell=True)
    if res.returncode != 0:
        raise SystemExit(res.returncode)

def main():
    # 1) Extract & enrich (your existing script; file path safest on Windows)
    extractor = REPO_ROOT / "scripts" / "11_extract_and_enrich_DIRECT.py"
    if extractor.exists():
        run(f'"{PY}" "{extractor}"')
    else:
        print("WARNING: extractor not found; skipping 11_extract_and_enrich_DIRECT.py")

    # 2) Build canonical artifact (+ back-compat copy)
    builder = REPO_ROOT / "scripts" / "99_build_enriched_fixed.py"
    run(f'"{PY}" "{builder}"')

    # 3) Adjudicate (unchanged)
    adj = REPO_ROOT / "50_adjudicate.py"
    if adj.exists():
        run(f'"{PY}" "{adj}"')
    else:
        print("WARNING: 50_adjudicate.py not found; skipping")

    # 4) Propose rewrites (unchanged)
    rew = REPO_ROOT / "52_propose_rewrites.py"
    if rew.exists():
        run(f'"{PY}" "{rew}"')
    else:
        print("WARNING: 52_propose_rewrites.py not found; skipping")

    print("\nAll steps finished.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())