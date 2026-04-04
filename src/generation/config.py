"""LLM provider settings from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default).strip()


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class GenerationConfig:
    """Which LLM backend to call and model ids."""

    provider: str  # "openai" | "mistral" | "ollama"
    openai_model: str
    mistral_base_url: str
    mistral_model: str
    ollama_base_url: str
    ollama_model: str
    ollama_http_timeout: float

    @classmethod
    def from_env(cls) -> GenerationConfig:
        return cls(
            provider=_env_str("LLM_PROVIDER", "openai").lower(),
            openai_model=_env_str("OPENAI_MODEL", "gpt-4o-mini"),
            mistral_base_url=_env_str(
                "MISTRAL_BASE_URL",
                "https://api.mistral.ai/v1",
            ),
            mistral_model=_env_str("MISTRAL_MODEL", "mistral-small-latest"),
            ollama_base_url=_env_str("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            ollama_model=_env_str("OLLAMA_MODEL", "llama3.2"),
            ollama_http_timeout=_env_float("OLLAMA_HTTP_TIMEOUT", 600.0),
        )
