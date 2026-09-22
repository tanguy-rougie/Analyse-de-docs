"""Traitement d'un job : ingestion réelle via le pipeline existant, ou traitement simulé."""

from __future__ import annotations

import logging
import time

from src.ingestion.pipeline import ingest
from src.jobs.database import SessionLocal
from src.jobs.models import Job
from src.jobs.service import JobService
from src.worker.config import WorkerConfig

logger = logging.getLogger(__name__)


def _run_ingest(payload: dict) -> dict:
    """Appelle le pipeline d'ingestion inchangé : PDF -> chunks -> embeddings -> ChromaDB."""
    input_dir = payload.get("input_dir") or "./Documents"
    collection = payload.get("collection") or "technical_docs"
    reset = bool(payload.get("reset", False))
    logger.info("Ingestion de %s vers la collection %s (reset=%s)", input_dir, collection, reset)
    return ingest(input_dir, collection, reset=reset)


def process_job(job: Job, config: WorkerConfig) -> dict | None:
    """Exécute le job selon son type. Retourne un résumé JSON ou None."""
    payload = job.payload or {}
    job_type = payload.get("job_type", "simulate")

    if job_type == "ingest":
        return _run_ingest(payload)

    if job_type == "simulate":
        logger.info("Traitement simulé de %ss", config.simulated_duration)
        time.sleep(config.simulated_duration)
        return None

    if job_type == "fail":
        raise RuntimeError("Échec simulé pour observer l'état FAILED.")

    raise ValueError(f"job_type inconnu : {job_type!r}")


def run_once(config: WorkerConfig) -> bool:
    """Traite au plus un job. Retourne False si la file est vide."""
    session = SessionLocal()
    try:
        service = JobService(session)
        job = service.take_next_job()
        if job is None:
            return False

        logger.info("Job %s -> RUNNING", job.id)
        try:
            result = process_job(job, config)
        except Exception as exc:
            service.mark_failed(job, str(exc))
            logger.warning("Job %s -> FAILED (%s)", job.id, exc)
            return True

        service.mark_completed(job, result)
        logger.info("Job %s -> COMPLETED %s", job.id, result or "")
        return True
    finally:
        session.close()
