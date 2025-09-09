# scripts/80_generate_corrections.py
# Back-compat wrapper: delegates to the canonical corrections builder.
from __future__ import annotations
from pathlib import Path
import runpy

if __name__ == "__main__":
    target = Path(__file__).resolve().with_name("90_build_corrections_list.py")
    runpy.run_path(str(target), run_name="__main__")
