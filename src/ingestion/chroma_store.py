"""Persist chunked documents to a local ChromaDB collection."""

from __future__ import annotations

import hashlib
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from langchain_core.documents import Document

from src.ingestion.config import IngestionConfig

# Index HNSW en similarité cosinus (top-k = plus proche en cosinus).
# Une collection créée avant ce réglage garde l’ancienne métrique : ré-ingérer avec --reset.
CHROMA_HNSW_METADATA = {"hnsw:space": "cosine"}


def _chunk_id(source: str, page: int, chunk_index: int) -> str:
    payload = f"{source}\n{page}\n{chunk_index}".encode("utf-8")
    return "c_" + hashlib.sha256(payload).hexdigest()


def _get_client(persist_dir: str) -> chromadb.PersistentClient:
    path = Path(persist_dir)
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def get_collection(
    config: IngestionConfig,
    collection_name: str,
    *,
    reset: bool = False,
):
    """Return a Chroma collection with SentenceTransformer embeddings."""
    client = _get_client(config.chroma_persist_dir)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=config.embedding_model,
    )
    if reset:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=ef,
        metadata=CHROMA_HNSW_METADATA,
    )


def add_documents(
    collection,
    documents: list[Document],
    *,
    batch_size: int = 256,
) -> int:
    """Add LangChain documents to the collection in batches. Returns count added."""
    if not documents:
        return 0
    total = 0
    for start in range(0, len(documents), batch_size):
        batch = documents[start : start + batch_size]
        ids = [
            _chunk_id(
                str(d.metadata["source"]),
                int(d.metadata["page"]),
                int(d.metadata["chunk_index"]),
            )
            for d in batch
        ]
        texts = [d.page_content for d in batch]
        metadatas = [
            {
                "source": str(d.metadata["source"]),
                "page": int(d.metadata["page"]),
                "chunk_index": int(d.metadata["chunk_index"]),
                "file_stem": str(d.metadata.get("file_stem", "")),
            }
            for d in batch
        ]
        collection.add(ids=ids, documents=texts, metadatas=metadatas)
        total += len(batch)
    return total
