from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from progrec_service.app import create_app
from progrec_service.db.models import PipelineJob, PipelineResult
from progrec_service.db.repositories.pipeline_jobs import PipelineJobRepository
from progrec_service.db.session import SessionLocal


class TestPipelineRoutes(unittest.TestCase):
    def test_create_pipeline_job_returns_queued_with_real_job_id(self) -> None:
        client = TestClient(create_app())
        with patch("progrec_service.queue.enqueue_job", return_value=None):
            response = client.post(
                "/pipeline/jobs",
                json={
                    "job_type": "recommend_existing_student",
                    "mode": "graph",
                    "student_id": "jamie-taylor-00008",
                    "runtime": {
                        "mode": "ephemeral",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-4.1-mini",
                        "api_key": "sk-test",
                    },
                },
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "queued")
        self.assertIn("job_id", response.json())

    def test_get_pipeline_job_result_returns_409_until_completed(self) -> None:
        client = TestClient(create_app())
        response = client.get("/pipeline/jobs/job_pending/result")
        self.assertEqual(response.status_code, 409)

    def test_get_pipeline_job_result_returns_persisted_payload_when_succeeded(self) -> None:
        with SessionLocal() as session:
            repo = PipelineJobRepository(session)
            repo.add_job(
                PipelineJob(
                    id="job_done",
                    job_type="recommend_existing_student",
                    runtime_profile_id=None,
                    request_payload={"student_id": "jamie-taylor-00008"},
                    status="succeeded",
                    progress_stage="completed",
                    progress_message="Done",
                    attempt_count=1,
                )
            )
            repo.add_result(
                PipelineResult(
                    id="res_done",
                    job_id="job_done",
                    result_payload={"skill5_result": {"recommendations": {"mentors": []}}},
                    summary_payload={"mentor_count": 0},
                    artifacts_payload={},
                )
            )
            session.commit()
        client = TestClient(create_app())
        response = client.get("/pipeline/jobs/job_done/result")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job_id"], "job_done")
        self.assertIn("result", response.json())

    def test_retry_pipeline_job_creates_replacement_job(self) -> None:
        with SessionLocal() as session:
            repo = PipelineJobRepository(session)
            repo.add_job(
                PipelineJob(
                    id="job_failed",
                    job_type="recommend_existing_student",
                    runtime_profile_id=None,
                    request_payload={"student_id": "jamie-taylor-00008", "job_type": "recommend_existing_student"},
                    status="failed",
                    progress_stage="completed",
                    progress_message="Failed",
                    attempt_count=1,
                )
            )
            session.commit()
        client = TestClient(create_app())
        with patch("progrec_service.queue.enqueue_job", return_value=None):
            response = client.post("/pipeline/jobs/job_failed/retry")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "queued")
        self.assertNotEqual(response.json()["job_id"], "job_failed")
