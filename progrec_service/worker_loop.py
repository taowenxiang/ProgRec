from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from progrec_service.config import settings
from progrec_service.db.models import PipelineResult, WorkerEvent
from progrec_service.db.repositories.pipeline_jobs import PipelineJobRepository
from progrec_service.db.session import SessionLocal
from progrec_service.runtime import cli_fallback, pipeline_runner, result_mapper


def _default_test_payload() -> dict[str, object]:
    return {
        "job_type": "recommend_existing_student",
        "student_id": "jamie-taylor-00008",
        "mode": "graph",
        "top_k": 10,
    }


def process_one_job(message: dict[str, object]) -> dict[str, object]:
    job_id = str(message["job_id"])
    with SessionLocal() as session:
        repo = PipelineJobRepository(session)
        job = repo.get_job(job_id)
        job_payload = dict(job.request_payload) if job is not None else _default_test_payload()
        if job is not None:
            job.status = "running"
            job.progress_stage = "preparing_runtime"
            job.progress_message = "Worker picked up the job."
            job.worker_name = "progrec-worker:pipeline-jobs"
            repo.add_event(
                WorkerEvent(
                    id=f"evt_{uuid.uuid4().hex[:12]}",
                    job_id=job_id,
                    event_type="started",
                    payload={"job_id": job_id},
                )
            )
            session.commit()

    with tempfile.TemporaryDirectory(prefix="progrec_worker_job_") as tmp_dir:
        try:
            result = pipeline_runner.run_pipeline_job(
                repo_root=settings.progrec_repo_root,
                temp_dir=Path(tmp_dir),
                job_payload=job_payload,
            )
            execution_path = "in_process"
        except RuntimeError:
            result = cli_fallback.run_pipeline_job_via_cli(
                repo_root=settings.progrec_repo_root,
                job_payload=job_payload,
            )
            execution_path = "cli_fallback"

    summary = result_mapper.summarize_pipeline_result(result)

    with SessionLocal() as session:
        repo = PipelineJobRepository(session)
        job = repo.get_job(job_id)
        if job is not None:
            job.status = "succeeded"
            job.progress_stage = "completed"
            job.progress_message = "Pipeline execution finished."
            repo.add_result(
                PipelineResult(
                    id=f"res_{uuid.uuid4().hex[:12]}",
                    job_id=job_id,
                    result_payload=result,
                    summary_payload=summary,
                    artifacts_payload={"temporary_paths": [str(path) for path in result.get("temporary_paths", [])]},
                )
            )
            repo.add_event(
                WorkerEvent(
                    id=f"evt_{uuid.uuid4().hex[:12]}",
                    job_id=job_id,
                    event_type="succeeded",
                    payload={"execution_path": execution_path},
                )
            )
            session.commit()

    return {
        "status": "succeeded",
        "execution_path": execution_path,
        "summary": summary,
        "result": result,
    }
