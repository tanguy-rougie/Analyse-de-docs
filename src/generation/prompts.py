"""Prompt templates for grounded technical Q&A."""

from __future__ import annotations


SYSTEM_RAG = """Tu es un assistant technique pour des ingénieurs. Réponds en t'appuyant \
uniquement sur le contexte fourni ci-dessous. Si le contexte ne permet pas de répondre, \
dis-le clairement et n'invente pas de faits. Cite les sources (fichier, page) quand c'est pertinent."""


def format_context_blocks(chunks: list[tuple[str, dict]]) -> str:
    """Build a single context string with source labels."""
    parts: list[str] = []
    for i, (text, meta) in enumerate(chunks, start=1):
        src = meta.get("source", "?")
        page = meta.get("page", "?")
        stem = meta.get("file_stem", "")
        label = f"[{i}] {stem or src} — p. {page}"
        parts.append(f"{label}\n{text.strip()}")
    return "\n\n---\n\n".join(parts)


def build_messages(question: str, context: str) -> list[dict[str, str]]:
    """OpenAI/Ollama chat message list."""
    user = (
        "Contexte documentaire :\n\n"
        f"{context}\n\n"
        f"Question : {question}\n\n"
        "Réponse concise, en français si la question est en français :"
    )
    return [
        {"role": "system", "content": SYSTEM_RAG},
        {"role": "user", "content": user},
    ]
