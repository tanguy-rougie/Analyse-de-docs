"""End-to-end RAG: retrieve → optional rerank → LLM."""

from __future__ import annotations

from dataclasses import dataclass

from src.generation.config import GenerationConfig
from src.generation.llm_client import generate_rag_answer
from src.generation.prompts import build_messages, format_context_blocks
from src.ingestion.config import IngestionConfig
from src.retrieval.chroma_retriever import retrieve
from src.retrieval.config import RetrievalConfig
from src.retrieval.reranker import CrossEncoderReranker


@dataclass
class RagResult:
    answer: str
    sources: list[dict]
    used_reranking: bool
    chunk_details: list[dict] | None = None


def answer_question(
    question: str,
    collection_name: str,
    *,
    ingestion_config: IngestionConfig | None = None,
    retrieval_config: RetrievalConfig | None = None,
    generation_config: GenerationConfig | None = None,
    reranker: CrossEncoderReranker | None = None,
    include_chunk_details: bool = False,
) -> RagResult:
    """
    Run retrieval (Chroma), optional CrossEncoder rerank, then LLM generation.
    """
    icfg = ingestion_config or IngestionConfig.from_env()
    rcfg = retrieval_config or RetrievalConfig.from_env()
    gcfg = generation_config or GenerationConfig.from_env()

    hits = retrieve(
        question,
        collection_name,
        k=rcfg.retrieve_k,
        config=icfg,
    )
    used_rerank = False
    if rcfg.use_reranking and hits:
        rk = reranker or CrossEncoderReranker(rcfg.cross_encoder_model)
        hits = rk.rerank(question, hits, top_n=rcfg.rerank_top_n)
        used_rerank = True
    else:
        hits = hits[: rcfg.rerank_top_n]

    pairs = [(h.text, h.metadata) for h in hits]
    context = format_context_blocks(pairs) if pairs else "(Aucun extrait pertinent indexé.)"
    messages = build_messages(question, context)
    answer = generate_rag_answer(messages, gcfg)

    sources: list[dict] = []
    for h in hits:
        sources.append(
            {
                "source": h.metadata.get("source"),
                "page": h.metadata.get("page"),
                "file_stem": h.metadata.get("file_stem"),
                "distance": h.distance,
                "cosine_similarity": h.cosine_similarity,
            }
        )

    chunk_details: list[dict] | None = None
    if include_chunk_details:
        chunk_details = []
        for h in hits:
            preview = h.text.strip()
            if len(preview) > 500:
                preview = preview[:500] + "…"
            chunk_details.append(
                {
                    "text_preview": preview,
                    "source": h.metadata.get("source"),
                    "page": h.metadata.get("page"),
                    "file_stem": h.metadata.get("file_stem"),
                    "distance": h.distance,
                    "cosine_similarity": h.cosine_similarity,
                }
            )

    return RagResult(
        answer=answer,
        sources=sources,
        used_reranking=used_rerank,
        chunk_details=chunk_details,
    )
