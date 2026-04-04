"""RAG retrieval settings (env)."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class RetrievalConfig:
    """How many chunks to pull from Chroma and optional reranking."""

    retrieve_k: int
    rerank_top_n: int
    use_reranking: bool
    cross_encoder_model: str

    @classmethod
    def from_env(cls) -> RetrievalConfig:
        return cls(
            # Mode RAG basique par défaut : top-k Chroma seul (pas de rerank), même k avant/après troncature.
            retrieve_k=_env_int("RETRIEVE_K", 5),
            rerank_top_n=_env_int("RERANK_TOP_N", 5),
            use_reranking=_env_bool("USE_RERANKING", False),
            cross_encoder_model=_env_str(
                "CROSS_ENCODER_MODEL",
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
            ),
        )
