"""FastAPI web UI for RAG questions."""

from __future__ import annotations

import os
from pathlib import Path

from src.env import load_env

load_env()

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.retrieval.rag import answer_question

STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_COLLECTION = os.environ.get("RAG_COLLECTION", "technical_docs").strip() or "technical_docs"

app = FastAPI(title="Analyse-de-docs", description="Interroger la documentation technique en langage naturel.")

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question en langage naturel.")
    verbose: bool = False


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]
    used_reranking: bool
    chunk_details: list[dict] | None = None


@app.get("/")
def index() -> FileResponse:
    html = STATIC_DIR / "index.html"
    if not html.is_file():
        raise HTTPException(status_code=500, detail="Interface web introuvable.")
    return FileResponse(html)


@app.post("/api/ask", response_model=AskResponse)
def ask(body: AskRequest) -> AskResponse:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide.")

    try:
        result = answer_question(
            question,
            DEFAULT_COLLECTION,
            include_chunk_details=body.verbose,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return AskResponse(
        answer=result.answer,
        sources=result.sources,
        used_reranking=result.used_reranking,
        chunk_details=result.chunk_details,
    )
