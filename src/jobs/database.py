"""Connexion PostgreSQL partagée (engine + sessions)."""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg://analyse:analyse@localhost:5432/analyse"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL).strip() or DEFAULT_DATABASE_URL


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_session() -> Generator[Session, None, None]:
    """Dépendance FastAPI : une session par requête HTTP, fermée ensuite."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Crée les tables manquantes. Suffisant tant que le schéma jobs reste simple (pas d’Alembic)."""
    from src.jobs import models as _models  # noqa: F401

    Base.metadata.create_all(bind=engine)
