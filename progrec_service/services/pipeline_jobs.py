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


def retry_pipeline_job(job_id: str) -> PipelineJob:
    with SessionLocal() as session:
        repo = PipelineJobRepository(session)
        original = repo.get_job(job_id)
        if original is None:
            raise ValueError(f"job {job_id} not found")
        replacement = PipelineJob(
            id=create_job_id(),
            supersedes_job_id=original.id,
            job_type=original.job_type,
            runtime_profile_id=original.runtime_profile_id,
            request_payload=dict(original.request_payload),
            status="queued",
            progress_stage="validating_input",
            progress_message="Replacement job accepted and queued.",
            attempt_count=original.attempt_count + 1,
        )
        repo.add_job(replacement)
        session.commit()
    return replacement


def get_pipeline_result(job_id: str) -> dict[str, object] | None:
    with SessionLocal() as session:
        repo = PipelineJobRepository(session)
        result = repo.get_result(job_id)
    if result is None:
        return None
    return {
        "job_id": result.job_id,
        "result": result.result_payload,
        "summary": result.summary_payload,
        "artifacts": result.artifacts_payload,
    }
