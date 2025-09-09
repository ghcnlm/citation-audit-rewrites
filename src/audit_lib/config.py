# src/audit_lib/config.py
"""Configuration loader with caching and basic validation."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "config.yaml"

# Required config structure for minimal operation
REQUIRED_KEYS: Dict[str, List[str]] = {
    "paths": ["outputs_dir", "reviews_dir", "sources_text_dir"],
    "retrieval": ["chunk_words", "chunk_stride", "top_k"],
}


class ConfigError(ValueError):
    """Raised when required configuration values are missing."""


@lru_cache(maxsize=1)
def load_config() -> Dict:
    """Load and cache config/config.yaml with basic validation."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config file: {CONFIG_PATH}")
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    for section, keys in REQUIRED_KEYS.items():
        if section not in cfg:
            raise ConfigError(f"Missing required section '{section}' in {CONFIG_PATH}")
        missing = [k for k in keys if k not in cfg.get(section, {})]
        if missing:
            raise ConfigError(
                f"Missing required key(s) {missing} in section '{section}' of {CONFIG_PATH}"
            )
    return cfg
