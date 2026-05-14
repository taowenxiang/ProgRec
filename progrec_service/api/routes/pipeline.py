from __future__ import annotations

from fastapi import APIRouter, HTTPException

import progrec_service.queue as pipeline_queue
from progrec_service.services.pipeline_jobs import (
    create_pipeline_job,
    get_pipeline_job,
    get_pipeline_result,
    retry_pipeline_job,
)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/jobs", status_code=201)
def create_job(payload: dict[str, object]) -> dict[str, object]:
    record = create_pipeline_job(payload)
    pipeline_queue.enqueue_job(record.id)
    return {"job_id": record.id, "status": record.status}


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    record = get_pipeline_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "job_id": record.id,
        "status": record.status,
        "progress_stage": record.progress_stage,
        "progress_message": record.progress_message,
        "attempt_count": record.attempt_count,
    }


@router.get("/jobs/{job_id}/result")
def get_job_result(job_id: str) -> dict[str, object]:
    record = get_pipeline_job(job_id)
    if record is None or record.status != "succeeded":
        raise HTTPException(status_code=409, detail="job result is not ready")
    result = get_pipeline_result(job_id)
    if result is None:
        raise HTTPException(status_code=409, detail="job result is not ready")
    return result


@router.post("/jobs/{job_id}/retry", status_code=201)
def retry_job(job_id: str) -> dict[str, object]:
    try:
        replacement = retry_pipeline_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    pipeline_queue.enqueue_job(replacement.id)
    return {"job_id": replacement.id, "status": replacement.status}
