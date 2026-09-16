"""Règles métier des jobs : l’API enregistre un travail, elle ne l’exécute pas."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.jobs.models import Job, JobStatus
from src.jobs.repository import JobRepository


class JobService:
    def __init__(self, session: Session) -> None:
        self._repo = JobRepository(session)

    def create_job(self, payload: dict) -> Job:
        job = Job(status=JobStatus.PENDING.value, payload=payload)
        return self._repo.add(job)

    def get_job(self, job_id: uuid.UUID) -> Job | None:
        return self._repo.get_by_id(job_id)
