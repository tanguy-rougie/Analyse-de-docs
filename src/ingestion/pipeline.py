"""Orchestrate PDF load → token chunking → Chroma persistence."""

from __future__ import annotations

from pathlib import Path

from src.ingestion.chunker import chunk_pages
from src.ingestion.chroma_store import add_documents, get_collection
from src.ingestion.config import IngestionConfig
from src.ingestion.pdf_loader import load_all_pdfs


def ingest(
    input_dir: str | Path,
    collection_name: str,
    *,
    reset: bool = False,
    config: IngestionConfig | None = None,
) -> dict:
    """
    Ingest all PDFs from input_dir into a Chroma collection.

    Returns a small summary dict: pages_loaded, chunks_written, collection, persist_dir.
    """
    cfg = config or IngestionConfig.from_env()
    path = Path(input_dir)

    pages = load_all_pdfs(path)
    if not pages:
        raise ValueError(
            f"No PDF pages found under {path.resolve()!s}. "
            "Add .pdf files (non-recursive) or check the path."
        )

    chunks = chunk_pages(
        pages,
        cfg.embedding_model,
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
    )

    collection = get_collection(cfg, collection_name, reset=reset)
    n = add_documents(collection, chunks, batch_size=cfg.ingest_batch_size)

    return {
        "pages_loaded": len(pages),
        "chunks_written": n,
        "collection": collection_name,
        "persist_dir": str(Path(cfg.chroma_persist_dir).resolve()),
    }
