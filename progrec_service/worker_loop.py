from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from progrec_service.config import settings
from progrec_service.db.models import PipelineJob, PipelineResult, WorkerEvent, utcnow
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


def _record_stage(
    *,
    repo: PipelineJobRepository,
    job: PipelineJob,
    stage: str,
    message: str,
) -> None:
    job.progress_stage = stage
    job.progress_message = message
    repo.add_event(
        WorkerEvent(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            job_id=job.id,
            event_type="stage_changed",
            payload={"stage": stage, "message": message},
        )
    )


def _mark_failed(job_id: str, error: Exception) -> dict[str, object]:
    with SessionLocal() as session:
        repo = PipelineJobRepository(session)
        job = repo.get_job(job_id)
        if job is not None:
            job.status = "failed"
            job.progress_stage = "completed"
            job.progress_message = "Pipeline execution failed."
            job.finished_at = utcnow()
            job.error_code = "pipeline_runtime_error"
            job.error_message = str(error)
            repo.add_event(
                WorkerEvent(
                    id=f"evt_{uuid.uuid4().hex[:12]}",
                    job_id=job_id,
                    event_type="failed",
                    payload={"error_code": job.error_code, "error_message": job.error_message},
                )
            )
            session.commit()
    return {
        "status": "failed",
        "error_code": "pipeline_runtime_error",
        "error_message": str(error),
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
            job.started_at = utcnow()
            repo.add_event(
                WorkerEvent(
                    id=f"evt_{uuid.uuid4().hex[:12]}",
                    job_id=job_id,
                    event_type="started",
                    payload={"job_id": job_id},
                )
            )
            _record_stage(
                repo=repo,
                job=job,
                stage="preparing_runtime",
                message="Preparing runtime resources.",
            )
            session.commit()

    with tempfile.TemporaryDirectory(prefix="progrec_worker_job_") as tmp_dir:
        try:
            with SessionLocal() as session:
                repo = PipelineJobRepository(session)
                job = repo.get_job(job_id)
                if job is not None:
                    _record_stage(
                        repo=repo,
                        job=job,
                        stage="running_skill3",
                        message="Finding mentor candidates.",
                    )
                    _record_stage(
                        repo=repo,
                        job=job,
                        stage="running_skill4",
                        message="Expanding project and teammate recommendations.",
                    )
                    _record_stage(
                        repo=repo,
                        job=job,
                        stage="running_skill5",
                        message="Ranking final recommendation package.",
                    )
                    session.commit()
            result = pipeline_runner.run_pipeline_job(
                repo_root=settings.progrec_repo_root,
                temp_dir=Path(tmp_dir),
                job_payload=job_payload,
            )
            execution_path = "in_process"
        except Exception as primary_error:
            with SessionLocal() as session:
                repo = PipelineJobRepository(session)
                job = repo.get_job(job_id)
                if job is not None:
                    repo.add_event(
                        WorkerEvent(
                            id=f"evt_{uuid.uuid4().hex[:12]}",
                            job_id=job_id,
                            event_type="fallback_to_cli",
                            payload={"error_message": str(primary_error)},
                        )
                    )
                    session.commit()
            try:
                result = cli_fallback.run_pipeline_job_via_cli(
                    repo_root=settings.progrec_repo_root,
                    job_payload=job_payload,
                )
                execution_path = "cli_fallback"
            except Exception as fallback_error:
                return _mark_failed(job_id, fallback_error)

    summary = result_mapper.summarize_pipeline_result(result)

    with SessionLocal() as session:
        repo = PipelineJobRepository(session)
        job = repo.get_job(job_id)
        if job is not None:
            _record_stage(
                repo=repo,
                job=job,
                stage="writing_artifacts",
                message="Writing recommendation result package.",
            )
            job.status = "succeeded"
            job.progress_stage = "completed"
            job.progress_message = "Pipeline execution finished."
            job.finished_at = utcnow()
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
