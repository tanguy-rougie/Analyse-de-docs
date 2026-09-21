"""Les tests tournent sur une base dédiée, jamais sur celle de développement.

`DATABASE_URL` est redirigé vers `analyse_test` avant l'import de `src.jobs.database`,
qui construit son engine au chargement du module.
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

DEV_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://analyse:analyse@localhost:5432/analyse",
)
TEST_DATABASE_NAME = "analyse_test"


def _with_database(url: str, database: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path=f"/{database}"))


def _create_test_database() -> None:
    """Crée la base de test si elle n'existe pas (no-op si PostgreSQL est absent)."""
    import psycopg

    admin_url = _with_database(DEV_DATABASE_URL, "postgres").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=3) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DATABASE_NAME,)
        ).fetchone()
        if not exists:
            connection.execute(f'CREATE DATABASE "{TEST_DATABASE_NAME}"')


try:
    _create_test_database()
except Exception:
    pass  # PostgreSQL injoignable : les tests qui en dépendent seront ignorés.

os.environ["DATABASE_URL"] = _with_database(DEV_DATABASE_URL, TEST_DATABASE_NAME)
