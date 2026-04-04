"""CrossEncoder reranking of retrieved passages."""

from __future__ import annotations

from sentence_transformers import CrossEncoder

from src.retrieval.chroma_retriever import RetrievedChunk


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: CrossEncoder | None = None

    @property
    def model(self) -> CrossEncoder:
        if self._model is None:
            self._model = CrossEncoder(self._model_name)
        return self._model

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []
        pairs = [[query, c.text] for c in chunks]
        scores = self.model.predict(pairs)
        if hasattr(scores, "tolist"):
            scores = scores.tolist()
        ranked = sorted(
            zip(scores, chunks, strict=True),
            key=lambda x: x[0],
            reverse=True,
        )
        n = max(1, min(top_n, len(ranked)))
        return [c for _, c in ranked[:n]]
