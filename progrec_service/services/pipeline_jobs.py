from __future__ import annotations

import uuid
from datetime import datetime

from progrec_service.db.models import PipelineJob
from progrec_service.db.repositories.pipeline_jobs import PipelineJobRepository
from progrec_service.db.session import SessionLocal
from progrec_service.runtime.result_mapper import normalize_result_package


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


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _request_summary(payload: dict[str, object]) -> str:
    if payload.get("student_id"):
        return f"Recommendations for student {payload['student_id']}"
    profile = dict(payload.get("student_profile") or {})
    name = profile.get("name") or profile.get("student_id")
    topic = profile.get("research_topic") or profile.get("research_direction") or profile.get("interests")
    if name and topic:
        return f"Recommendations for {name}: {topic}"
    if name:
        return f"Recommendations for {name}"
    if topic:
        return f"Recommendations for {topic}"
    return "Recommendation run"


def _is_retryable(record: PipelineJob) -> bool:
    return record.status in {"failed", "retryable"}


def _updated_at(record: PipelineJob, latest_event_at: datetime | None) -> datetime | None:
    return latest_event_at or record.finished_at or record.started_at or record.queued_at


def serialize_pipeline_job(record: PipelineJob, *, latest_event_at: datetime | None) -> dict[str, object]:
    updated_at = _updated_at(record, latest_event_at)
    return {
        "job_id": record.id,
        "status": record.status,
        "progress_stage": record.progress_stage,
        "progress_message": record.progress_message,
        "created_at": _iso(record.queued_at),
        "updated_at": _iso(updated_at),
        "last_event_at": _iso(latest_event_at),
        "started_at": _iso(record.started_at),
        "finished_at": _iso(record.finished_at),
        "attempt_count": record.attempt_count,
        "is_retryable": _is_retryable(record),
        "request_summary": _request_summary(dict(record.request_payload or {})),
        "runtime_profile_id": record.runtime_profile_id,
        "supersedes_job_id": record.supersedes_job_id,
        "error_code": record.error_code,
        "error_message": record.error_message,
    }


def list_pipeline_jobs(*, limit: int = 50) -> list[dict[str, object]]:
    with SessionLocal() as session:
        repo = PipelineJobRepository(session)
        records = repo.list_jobs(limit=limit)
        return [
            serialize_pipeline_job(record, latest_event_at=repo.latest_event_at(record.id))
            for record in records
        ]


def get_pipeline_job(job_id: str) -> PipelineJob | None:
    with SessionLocal() as session:
        repo = PipelineJobRepository(session)
        return repo.get_job(job_id)


def get_pipeline_job_detail(job_id: str) -> dict[str, object] | None:
    with SessionLocal() as session:
        repo = PipelineJobRepository(session)
        record = repo.get_job(job_id)
        if record is None:
            return None
        return serialize_pipeline_job(record, latest_event_at=repo.latest_event_at(record.id))


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
        "result": normalize_result_package(dict(result.result_payload or {})),
        "raw_result": result.result_payload,
        "summary": result.summary_payload,
        "artifacts": result.artifacts_payload,
    }
