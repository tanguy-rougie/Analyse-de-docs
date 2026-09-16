"""Accès aux données jobs : seules les requêtes SQL vivent ici."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.jobs.models import Job


class JobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, job: Job) -> Job:
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        return self._session.get(Job, job_id)
