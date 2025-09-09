import logging
import os
import sys
import yaml
import pathlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load model from config.yaml (falls back to gpt-4o-mini for the test)
cfg = yaml.safe_load(open("config/config.yaml", "r", encoding="utf-8"))
model = (cfg.get("llm", {}) or {}).get("model") or "gpt-4o"
test_model = model

# For a quick ping, if your account doesn't have gpt-4o, try mini automatically
fallback = "gpt-4o-mini"

try:
    from openai import OpenAI
    client = OpenAI()  # reads OPENAI_API_KEY / base URL from env
    try:
        client.chat.completions.create(
            model=test_model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
            temperature=0,
        )
        logger.info("OK with model: %s", test_model)
    except Exception as e1:
        if fallback != test_model:
            logger.warning(
                "Primary model '%s' failed: %s\nTrying fallback: %s",
                test_model,
                e1,
                fallback,
            )
            client.chat.completions.create(
                model=fallback,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                temperature=0,
            )
            logger.info("OK with fallback: %s", fallback)
        else:
            raise
except Exception as e:
    logger.error("ERROR: %s %s", type(e).__name__, e)
    sys.exit(1)