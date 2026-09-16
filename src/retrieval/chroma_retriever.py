"""Query Chroma for similar chunks (same embedding model as ingestion).

Avec ``hnsw:space: cosine`` (voir ``chroma_store.CHROMA_HNSW_METADATA``), Chroma
renvoie une *distance cosinus* où, pour des embeddings normalisés :

    distance = 1 - cos_similarity

donc ``cosine_similarity = 1 - distance`` (plus le score est proche de 1, plus le
passage est aligné avec la requête). Ré-ingérer avec ``--reset`` si la collection
a été créée sous une autre métrique.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.ingestion.chroma_store import get_collection
from src.ingestion.config import IngestionConfig


def chroma_cosine_distance_to_similarity(distance: float | None) -> float | None:
    """Convertit la distance cosinus Chroma en similarité cosinus dans [0, 1] typiquement."""
    if distance is None:
        return None
    return 1.0 - float(distance)


@dataclass
class RetrievedChunk:
    """One hit from the vector store."""

    text: str
    metadata: dict
    distance: float | None
    cosine_similarity: float | None = None


def retrieve(
    query: str,
    collection_name: str,
    *,
    k: int,
    config: IngestionConfig | None = None,
) -> list[RetrievedChunk]:
    """Top-k retrieval par similarité cosinus (ordre Chroma = distance croissante)."""
    cfg = config or IngestionConfig.from_env()
    collection = get_collection(cfg, collection_name, reset=False)
    n = max(1, k)
    raw = collection.query(query_texts=[query], n_results=n)
    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]
    out: list[RetrievedChunk] = []
    for i, text in enumerate(docs):
        if not text:
            continue
        meta = dict(metas[i]) if i < len(metas) and metas[i] else {}
        dist = float(dists[i]) if i < len(dists) and dists[i] is not None else None
        cos_sim = chroma_cosine_distance_to_similarity(dist)
        out.append(
            RetrievedChunk(
                text=text,
                metadata=meta,
                distance=dist,
                cosine_similarity=cos_sim,
            )
        )
    return out
