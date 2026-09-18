"""Règles métier des jobs : l’API enregistre un travail, elle ne l’exécute pas."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.jobs.models import Job, JobStatus, utcnow
from src.jobs.repository import JobRepository


class JobService:
    def __init__(self, session: Session) -> None:
        self._repo = JobRepository(session)

    def create_job(self, payload: dict) -> Job:
        job = Job(status=JobStatus.PENDING.value, payload=payload)
        return self._repo.add(job)

    def get_job(self, job_id: uuid.UUID) -> Job | None:
        return self._repo.get_by_id(job_id)

    # Méthodes utilisées par le worker (l'API n'y touche pas).

    def take_next_job(self) -> Job | None:
        """Passe le plus ancien job PENDING en RUNNING, ou None si la file est vide."""
        job = self._repo.get_oldest_pending()
        if job is None:
            return None
        job.status = JobStatus.RUNNING.value
        job.started_at = utcnow()
        return self._repo.save(job)

    def mark_completed(self, job: Job) -> Job:
        job.status = JobStatus.COMPLETED.value
        job.error_message = None
        job.finished_at = utcnow()
        return self._repo.save(job)

    def mark_failed(self, job: Job, error_message: str) -> Job:
        job.status = JobStatus.FAILED.value
        job.error_message = error_message
        job.finished_at = utcnow()
        return self._repo.save(job)
