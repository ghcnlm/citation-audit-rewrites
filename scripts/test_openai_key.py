import os, sys, yaml, pathlib

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
        r = client.chat.completions.create(
            model=test_model,
            messages=[{"role":"user","content":"ping"}],
            max_tokens=5,
            temperature=0
        )
        print("OK with model:", test_model)
    except Exception as e1:
        if fallback != test_model:
            print(f"Primary model '{test_model}' failed: {e1}\nTrying fallback:", fallback)
            r = client.chat.completions.create(
                model=fallback,
                messages=[{"role":"user","content":"ping"}],
                max_tokens=5,
                temperature=0
            )
            print("OK with fallback:", fallback)
        else:
            raise
except Exception as e:
    print("ERROR:", type(e).__name__, e)
    sys.exit(1)