"""Traitement d'un job : pour l'instant simulé, pas encore branché sur l'ingestion RAG."""

from __future__ import annotations

import logging
import time

from src.jobs.database import SessionLocal
from src.jobs.models import Job
from src.jobs.service import JobService
from src.worker.config import WorkerConfig

logger = logging.getLogger(__name__)


def process_job(job: Job, config: WorkerConfig) -> None:
    """Simule un traitement long. L'appel au pipeline d'ingestion viendra plus tard."""
    payload = job.payload or {}
    job_type = payload.get("job_type", "simulate")
    if job_type == "fail":
        raise RuntimeError("Échec simulé pour observer l'état FAILED.")
    logger.info("Traitement simulé de %ss (job_type=%s)", config.simulated_duration, job_type)
    time.sleep(config.simulated_duration)


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
            process_job(job, config)
        except Exception as exc:
            service.mark_failed(job, str(exc))
            logger.warning("Job %s -> FAILED (%s)", job.id, exc)
            return True

        service.mark_completed(job)
        logger.info("Job %s -> COMPLETED", job.id)
        return True
    finally:
        session.close()
