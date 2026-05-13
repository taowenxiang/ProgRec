from __future__ import annotations

from fastapi import APIRouter

from progrec_service.services.pipeline_jobs import create_job_id

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/jobs")
def create_job(payload: dict[str, object]) -> dict[str, object]:
    return {"job_id": create_job_id(), "status": "queued"}
