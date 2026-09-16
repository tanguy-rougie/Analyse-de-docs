"""Contrôleur santé : l’API tourne-t-elle, PostgreSQL répond-il ?"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.jobs.database import get_session

router = APIRouter()


@router.get("/health")
def health(session: Session = Depends(get_session)):
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "postgres": str(exc)},
        )
    return {"status": "ok", "postgres": "ok"}
