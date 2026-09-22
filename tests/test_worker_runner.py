"""Aiguillage du worker selon job_type, sans base de données ni indexation réelle."""

from __future__ import annotations

import pytest

from src.jobs.models import Job
from src.worker import runner
from src.worker.config import WorkerConfig

CONFIG = WorkerConfig(poll_interval=0.0, simulated_duration=0.0)


def make_job(payload: dict) -> Job:
    """Job non persisté : process_job ne touche pas à la base."""
    return Job(payload=payload)


def test_ingest_appelle_le_pipeline_avec_les_champs_du_job(monkeypatch):
    appels = []

    def faux_ingest(input_dir, collection, *, reset):
        appels.append((input_dir, collection, reset))
        return {"pages_loaded": 3, "chunks_written": 7}

    monkeypatch.setattr(runner, "ingest", faux_ingest)

    job = make_job(
        {
            "job_type": "ingest",
            "input_dir": "./Documents",
            "collection": "technical_docs",
            "reset": True,
        }
    )
    resultat = runner.process_job(job, CONFIG)

    assert appels == [("./Documents", "technical_docs", True)]
    assert resultat == {"pages_loaded": 3, "chunks_written": 7}


def test_ingest_utilise_les_valeurs_par_defaut(monkeypatch):
    appels = []
    monkeypatch.setattr(
        runner,
        "ingest",
        lambda input_dir, collection, *, reset: appels.append((input_dir, collection, reset)) or {},
    )

    runner.process_job(make_job({"job_type": "ingest"}), CONFIG)

    assert appels == [("./Documents", "technical_docs", False)]


def test_simulate_ne_produit_aucun_resultat():
    assert runner.process_job(make_job({"job_type": "simulate"}), CONFIG) is None


def test_simulate_est_le_type_par_defaut():
    assert runner.process_job(make_job({}), CONFIG) is None


def test_fail_leve_une_erreur():
    with pytest.raises(RuntimeError):
        runner.process_job(make_job({"job_type": "fail"}), CONFIG)


def test_type_inconnu_leve_une_erreur():
    with pytest.raises(ValueError, match="job_type inconnu"):
        runner.process_job(make_job({"job_type": "inexistant"}), CONFIG)
