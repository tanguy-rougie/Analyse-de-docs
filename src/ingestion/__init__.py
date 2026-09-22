"""PDF ingestion: load, chunk, embed, persist to ChromaDB."""

from src.ingestion.pipeline import ingest

__all__ = ["ingest"]
