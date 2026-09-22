"""Retrieval from ChromaDB and optional CrossEncoder reranking."""

from __future__ import annotations

__all__ = ["answer_question"]


def __getattr__(name: str):
    if name == "answer_question":
        from src.retrieval.rag import answer_question

        return answer_question
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
