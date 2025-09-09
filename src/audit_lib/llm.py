"""LLM client utilities.

This module provides helpers for rendering Jinja templates and a thin
``LLMClient`` wrapper around provider SDKs.  The client supports basic retry
logic with exponential backoff, provider/model selection via environment
variables or ``config/config.yaml``, and emits standard ``logging`` messages.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from jinja2 import Template


logger = logging.getLogger(__name__)


def _load_file(path: str | Path) -> str:
    """Load a UTF-8 text file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def render_user_prompt(
    tmpl_path: str,
    claim_text: str,
    review_context: str,
    source_author: str,
    source_year: str,
    source_pdf_path: str,
    evidence: List[Dict[str, str]],
) -> str:
    tmpl = Template(_load_file(tmpl_path))
    return tmpl.render(
        claim_text=claim_text,
        review_context=review_context,
        source_author=source_author,
        source_year=source_year,
        source_pdf_path=source_pdf_path,
        evidence=evidence,
    )


class LLMClientError(Exception):
    """Base exception for LLM client failures."""


class LLMProviderError(LLMClientError):
    """Raised when the configured provider is unsupported."""


class LLMResponseError(LLMClientError):
    """Raised when the provider returns an error after retries."""


class LLMClient:
    """Thin client wrapper for LLM providers.

    Parameters may be supplied directly, via environment variables, or via
    ``config/config.yaml``.  ``LLM_PROVIDER``/``LLM_MODEL`` environment
    variables take precedence over config values.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        config_path: Optional[str | Path] = "config/config.yaml",
        max_retries: int = 3,
        backoff: float = 1.0,
    ) -> None:
        cfg_provider: Optional[str] = None
        cfg_model: Optional[str] = None

        if config_path and Path(config_path).exists():
            try:
                cfg = yaml.safe_load(open(config_path, "r", encoding="utf-8"))
                llm_cfg = (cfg.get("llm") or {})
                cfg_provider = llm_cfg.get("provider")
                cfg_model = llm_cfg.get("model")
            except Exception as exc:  # pragma: no cover - config optional
                logger.warning("Failed to load config %s: %s", config_path, exc)

        self.provider = (
            provider
            or os.getenv("LLM_PROVIDER")
            or cfg_provider
            or "openai"
        )
        self.model = (
            model or os.getenv("LLM_MODEL") or cfg_model or "gpt-4o"
        )
        self.max_retries = max_retries
        self.backoff = backoff

        if self.provider == "openai":
            from openai import OpenAI

            self._client = OpenAI()  # reads API key/base URL from env
        else:  # pragma: no cover - only openai currently supported
            raise LLMProviderError(f"Unsupported provider: {self.provider}")

    # ------------------------------------------------------------------
    def json_call(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: Dict[str, Any],
        *,
        temperature: float = 0.0,
        max_tokens: int = 800,
    ) -> Dict[str, Any]:
        """Return a JSON response from the model.

        Retries are attempted with exponential backoff.  ``LLMResponseError`` is
        raised if all attempts fail.
        """

        for attempt in range(1, self.max_retries + 1):
            try:
                if self.provider == "openai":
                    try:
                        resp = self._client.responses.create(
                            model=self.model,
                            input=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            response_format={"type": "json_object"},
                        )
                        text = resp.output_text
                    except Exception:
                        resp = self._client.chat.completions.create(
                            model=self.model,
                            temperature=temperature,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            response_format={"type": "json_object"},
                            max_tokens=max_tokens,
                        )
                        text = resp.choices[0].message.content

                    return json.loads(text)

                raise LLMProviderError(
                    f"Unsupported provider during call: {self.provider}"
                )

            except Exception as exc:  # catch provider SDK errors
                if attempt == self.max_retries:
                    logger.error(
                        "LLM request failed after %s attempts", attempt, exc_info=True
                    )
                    raise LLMResponseError(str(exc)) from exc

                sleep_s = self.backoff * (2 ** (attempt - 1))
                logger.warning(
                    "LLM request failed (attempt %s/%s): %s; retrying in %.1fs",
                    attempt,
                    self.max_retries,
                    exc,
                    sleep_s,
                )
                time.sleep(sleep_s)


# Backwards compatible helper -------------------------------------------------
def openai_call(
    model: str,
    system_prompt: str,
    user_prompt: str,
    json_schema: Dict[str, Any],
    temperature: float = 0.0,
    max_tokens: int = 800,
) -> Dict[str, Any]:
    """Compatibility wrapper around :class:`LLMClient`.

    Raises ``LLMClientError`` on failure.
    """

    client = LLMClient(provider="openai", model=model)
    return client.json_call(
        system_prompt,
        user_prompt,
        json_schema,
        temperature=temperature,
        max_tokens=max_tokens,
    )


__all__ = [
    "LLMClient",
    "LLMClientError",
    "LLMProviderError",
    "LLMResponseError",
    "_load_file",
    "render_user_prompt",
    "openai_call",
]

