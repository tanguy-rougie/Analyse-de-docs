"""Contrôleur jobs : crée et lit des jobs ; le traitement sera fait par un worker plus tard."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.jobs.database import get_session
from src.jobs.models import Job
from src.jobs.service import JobService

router = APIRouter()


class CreateJobRequest(BaseModel):
    job_type: str = Field(default="simulate", description="ingest, simulate ou fail.")
    input_dir: str = Field(default="./Documents")
    collection: str = Field(default="technical_docs")
    reset: bool = False


class JobResponse(BaseModel):
    id: uuid.UUID
    status: str
    payload: dict
    result: dict | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


def _to_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        status=job.status,
        payload=job.payload or {},
        result=job.result,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def get_job_service(session: Session = Depends(get_session)) -> JobService:
    return JobService(session)


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    body: CreateJobRequest,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    job = service.create_job(body.model_dump())
    return _to_response(job)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: uuid.UUID,
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job introuvable.")
    return _to_response(job)
