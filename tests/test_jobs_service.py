"""Transitions d'état des jobs sur une vraie base PostgreSQL (base `analyse_test`).

Ignoré si la base n'est pas joignable : `docker compose up -d postgres` pour l'activer.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, text

from src.jobs.database import SessionLocal, engine, init_db
from src.jobs.models import Job
from src.jobs.service import JobService


def postgres_disponible() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not postgres_disponible(),
    reason="PostgreSQL injoignable (docker compose up -d postgres)",
)


@pytest.fixture
def service():
    """File vide au début de chaque test, pour que l'ordre FIFO soit vérifiable."""
    init_db()
    session = SessionLocal()
    session.execute(delete(Job))
    session.commit()
    try:
        yield JobService(session)
    finally:
        session.close()


def test_un_job_cree_est_pending(service):
    job = service.create_job({"job_type": "simulate"})

    assert job.status == "PENDING"
    assert job.started_at is None
    assert job.finished_at is None
    assert job.result is None


def test_relire_un_job_par_son_identifiant(service):
    cree = service.create_job({"job_type": "simulate"})

    relu = service.get_job(cree.id)

    assert relu is not None
    assert relu.id == cree.id
    assert relu.payload["job_type"] == "simulate"


def test_identifiant_inconnu_retourne_none(service):
    assert service.get_job(uuid.uuid4()) is None


def test_cycle_complet_jusqu_a_completed(service):
    cree = service.create_job({"job_type": "simulate"})

    pris = service.take_next_job()
    assert pris is not None
    assert pris.status == "RUNNING"
    assert pris.started_at is not None

    termine = service.mark_completed(pris, {"pages_loaded": 2})

    assert termine.status == "COMPLETED"
    assert termine.result == {"pages_loaded": 2}
    assert termine.error_message is None
    assert termine.finished_at >= termine.started_at
    assert termine.id == cree.id


def test_cycle_complet_jusqu_a_failed(service):
    service.create_job({"job_type": "fail"})

    pris = service.take_next_job()
    assert pris is not None

    echoue = service.mark_failed(pris, "Échec simulé.")

    assert echoue.status == "FAILED"
    assert echoue.error_message == "Échec simulé."
    assert echoue.finished_at is not None


def test_take_next_job_sert_les_jobs_dans_l_ordre_de_creation(service):
    premier = service.create_job({"job_type": "simulate", "marqueur": "premier"})
    service.create_job({"job_type": "simulate", "marqueur": "second"})

    pris = service.take_next_job()

    assert pris.id == premier.id


def test_take_next_job_retourne_none_quand_la_file_est_vide(service):
    assert service.take_next_job() is None
