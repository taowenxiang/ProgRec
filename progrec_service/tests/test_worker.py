from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from progrec_service.db.models import PipelineJob
from progrec_service.db.repositories.pipeline_jobs import PipelineJobRepository
from progrec_service.db.session import SessionLocal
from progrec_service.worker import main, worker_name
from progrec_service.worker_loop import process_one_job


class TestWorkerExecution(unittest.TestCase):
    def _create_job(self) -> str:
        job_id = f"job_worker_{uuid.uuid4().hex[:8]}"
        with SessionLocal() as session:
            repo = PipelineJobRepository(session)
            repo.add_job(
                PipelineJob(
                    id=job_id,
                    job_type="recommend_existing_student",
                    runtime_profile_id=None,
                    request_payload={
                        "job_type": "recommend_existing_student",
                        "student_id": "jamie-taylor-00008",
                    },
                    status="queued",
                    progress_stage="validating_input",
                    progress_message="Queued",
                    attempt_count=1,
                )
            )
            session.commit()
        return job_id

    def test_process_one_job_marks_success_and_maps_results(self) -> None:
        with patch(
            "progrec_service.runtime.pipeline_runner.run_pipeline_job",
            return_value={
                "skill5_result": {
                    "recommendations": {"mentors": [{"id": "m1"}], "projects": [], "teammates": []}
                },
                "temporary_paths": [],
            },
        ):
            outcome = process_one_job({"job_id": "job_001"})
        self.assertEqual(outcome["status"], "succeeded")
        self.assertEqual(outcome["summary"]["mentor_count"], 1)

    def test_process_one_job_records_user_facing_stage_events(self) -> None:
        job_id = self._create_job()
        with patch(
            "progrec_service.runtime.pipeline_runner.run_pipeline_job",
            return_value={
                "skill5_result": {
                    "recommendations": {"mentors": [], "projects": [], "teammates": []}
                },
                "temporary_paths": [],
            },
        ):
            outcome = process_one_job({"job_id": job_id})

        self.assertEqual(outcome["status"], "succeeded")
        with SessionLocal() as session:
            repo = PipelineJobRepository(session)
            job = repo.get_job(job_id)
            self.assertEqual(job.progress_stage, "completed")
            event_types = [event.event_type for event in job.events]
            stages = [event.payload.get("stage") for event in job.events if event.event_type == "stage_changed"]
        self.assertIn("stage_changed", event_types)
        self.assertIn("running_skill3", stages)
        self.assertIn("running_skill4", stages)
        self.assertIn("running_skill5", stages)
        self.assertIn("writing_artifacts", stages)

    def test_process_one_job_falls_back_to_cli_when_primary_runner_raises(self) -> None:
        with patch("progrec_service.runtime.pipeline_runner.run_pipeline_job", side_effect=RuntimeError("primary failed")):
            with patch(
                "progrec_service.runtime.cli_fallback.run_pipeline_job_via_cli",
                return_value={
                    "skill5_result": {"recommendations": {"mentors": [], "projects": [], "teammates": []}},
                    "temporary_paths": [],
                },
            ):
                outcome = process_one_job({"job_id": "job_002"})
        self.assertEqual(outcome["status"], "succeeded")
        self.assertEqual(outcome["execution_path"], "cli_fallback")

    def test_process_one_job_persists_failure_contract_when_all_execution_fails(self) -> None:
        job_id = self._create_job()
        with patch("progrec_service.runtime.pipeline_runner.run_pipeline_job", side_effect=RuntimeError("primary failed")):
            with patch(
                "progrec_service.runtime.cli_fallback.run_pipeline_job_via_cli",
                side_effect=RuntimeError("fallback failed"),
            ):
                outcome = process_one_job({"job_id": job_id})

        self.assertEqual(outcome["status"], "failed")
        with SessionLocal() as session:
            repo = PipelineJobRepository(session)
            job = repo.get_job(job_id)
            self.assertEqual(job.status, "failed")
            self.assertEqual(job.error_code, "pipeline_runtime_error")
            self.assertIn("fallback failed", job.error_message)


class TestWorkerMain(unittest.TestCase):
    def test_worker_name_includes_queue_name(self) -> None:
        self.assertEqual(worker_name(), "progrec-worker:pipeline-jobs")

    def test_main_exits_cleanly_when_stop_event_is_set(self) -> None:
        with patch("progrec_service.worker.stop_event.wait", return_value=True):
            with patch("progrec_service.worker.signal.signal"):
                self.assertEqual(main(poll_interval_seconds=0.01), 0)

    def test_main_processes_dequeued_job(self) -> None:
        with patch("progrec_service.worker.dequeue_job_message", return_value={"job_id": "job_001"}):
            with patch("progrec_service.worker.process_one_job", return_value={"status": "succeeded"}) as process_mock:
                with patch("progrec_service.worker.stop_event.wait", side_effect=[False, True]):
                    with patch("progrec_service.worker.signal.signal"):
                        self.assertEqual(main(poll_interval_seconds=0.01), 0)
        process_mock.assert_called_once_with({"job_id": "job_001"})


if __name__ == "__main__":
    unittest.main()
