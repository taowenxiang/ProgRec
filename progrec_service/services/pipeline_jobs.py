from __future__ import annotations

import uuid

from progrec_service.db.models import PipelineJob
from progrec_service.db.repositories.pipeline_jobs import PipelineJobRepository
from progrec_service.db.session import SessionLocal


def create_job_id() -> str:
    return f"job_{uuid.uuid4().hex[:12]}"


def create_job_record(payload: dict[str, object]) -> PipelineJob:
    return PipelineJob(
        id=create_job_id(),
        job_type=str(payload["job_type"]),
        runtime_profile_id=payload.get("runtime_profile_id"),
        request_payload=payload,
        status="queued",
        progress_stage="validating_input",
        progress_message="Job accepted and queued.",
        attempt_count=1,
    )


def create_pipeline_job(payload: dict[str, object]) -> PipelineJob:
    record = create_job_record(payload)
    with SessionLocal() as session:
        repo = PipelineJobRepository(session)
        repo.add_job(record)
        session.commit()
    return record


def get_pipeline_job(job_id: str) -> PipelineJob | None:
    with SessionLocal() as session:
        repo = PipelineJobRepository(session)
        return repo.get_job(job_id)
