"""Accès aux données jobs : seules les requêtes SQL vivent ici."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.jobs.models import Job, JobStatus


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

    def get_oldest_pending(self) -> Job | None:
        """Le plus ancien job en attente (file FIFO)."""
        stmt = (
            select(Job)
            .where(Job.status == JobStatus.PENDING.value)
            .order_by(Job.created_at.asc())
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def save(self, job: Job) -> Job:
        """Écrit en base les modifications faites sur un job déjà chargé."""
        self._session.commit()
        self._session.refresh(job)
        return job
