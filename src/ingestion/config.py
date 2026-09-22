"""Ingestion settings from env with sensible defaults."""

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


@dataclass(frozen=True)
class IngestionConfig:
    """Configuration for the ingestion pipeline."""

    chroma_persist_dir: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    ingest_batch_size: int

    @classmethod
    def from_env(cls) -> IngestionConfig:
        return cls(
            chroma_persist_dir=_env_str("CHROMA_PERSIST_DIR", "./chroma_db"),
            embedding_model=_env_str(
                "EMBEDDING_MODEL",
                "BAAI/bge-small-en-v1.5",
            ),
            chunk_size=_env_int("CHUNK_SIZE", 512),
            chunk_overlap=_env_int("CHUNK_OVERLAP", 50),
            ingest_batch_size=_env_int("INGEST_BATCH_SIZE", 256),
        )


# Default: BGE small supports 512 tokens; aligns with assignment chunk size.
