from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from progrec_service.app import create_app
from progrec_service.db.models import PipelineJob, PipelineResult, WorkerEvent
from progrec_service.db.repositories.pipeline_jobs import PipelineJobRepository
from progrec_service.db.session import SessionLocal


class TestPipelineRoutes(unittest.TestCase):
    def _job_id(self, suffix: str) -> str:
        return f"job_{suffix}_{uuid.uuid4().hex[:8]}"

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

    def test_create_pipeline_job_rejects_invalid_payload_without_enqueuing(self) -> None:
        client = TestClient(create_app())
        with patch("progrec_service.queue.enqueue_job", return_value=None) as enqueue_mock:
            response = client.post(
                "/pipeline/jobs",
                json={"job_type": "recommend_for_profile", "top_k": 5},
            )

        self.assertEqual(response.status_code, 422)
        self.assertIn("student_profile", response.json()["detail"])
        enqueue_mock.assert_not_called()

    def test_list_pipeline_jobs_returns_frontend_card_contract(self) -> None:
        job_id = self._job_id("list")
        with SessionLocal() as session:
            repo = PipelineJobRepository(session)
            repo.add_job(
                PipelineJob(
                    id=job_id,
                    job_type="recommend_existing_student",
                    runtime_profile_id="rp_saved",
                    request_payload={
                        "job_type": "recommend_existing_student",
                        "student_id": "jamie-taylor-00008",
                    },
                    status="failed",
                    progress_stage="running_skill4",
                    progress_message="Project and teammate expansion failed.",
                    attempt_count=2,
                    error_code="pipeline_runtime_error",
                    error_message="Skill 4 failed",
                )
            )
            repo.add_event(
                WorkerEvent(
                    id=f"evt_{uuid.uuid4().hex[:12]}",
                    job_id=job_id,
                    event_type="stage_changed",
                    payload={"stage": "running_skill4"},
                )
            )
            session.commit()

        client = TestClient(create_app())
        response = client.get("/pipeline/jobs")

        self.assertEqual(response.status_code, 200)
        matching = [item for item in response.json()["jobs"] if item["job_id"] == job_id]
        self.assertEqual(len(matching), 1)
        item = matching[0]
        self.assertEqual(item["status"], "failed")
        self.assertEqual(item["runtime_profile_id"], "rp_saved")
        self.assertTrue(item["is_retryable"])
        self.assertIn("jamie-taylor-00008", item["request_summary"])
        self.assertIn("created_at", item)
        self.assertIn("updated_at", item)
        self.assertIn("last_event_at", item)

    def test_get_pipeline_job_returns_stable_detail_contract(self) -> None:
        job_id = self._job_id("detail")
        with SessionLocal() as session:
            repo = PipelineJobRepository(session)
            repo.add_job(
                PipelineJob(
                    id=job_id,
                    job_type="recommend_temporary_profile",
                    runtime_profile_id=None,
                    request_payload={
                        "job_type": "recommend_temporary_profile",
                        "student_profile": {"name": "Avery Chen", "research_topic": "AI safety"},
                    },
                    status="running",
                    progress_stage="running_skill3",
                    progress_message="Finding mentor candidates.",
                    attempt_count=1,
                )
            )
            session.commit()

        client = TestClient(create_app())
        response = client.get(f"/pipeline/jobs/{job_id}")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["job_id"], job_id)
        self.assertEqual(body["progress_stage"], "running_skill3")
        self.assertFalse(body["is_retryable"])
        self.assertIn("Avery Chen", body["request_summary"])
        for field in [
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
            "error_code",
            "error_message",
            "runtime_profile_id",
            "supersedes_job_id",
        ]:
            self.assertIn(field, body)

    def test_profile_request_summary_joins_interest_lists(self) -> None:
        job_id = self._job_id("summary")
        with SessionLocal() as session:
            repo = PipelineJobRepository(session)
            repo.add_job(
                PipelineJob(
                    id=job_id,
                    job_type="recommend_for_profile",
                    runtime_profile_id=None,
                    request_payload={
                        "job_type": "recommend_for_profile",
                        "student_profile": {
                            "student_id": "alex-chen-demo",
                            "name": "Alex Chen",
                            "interests": ["social computing", "mentor matching"],
                        },
                    },
                    status="queued",
                    progress_stage="validating_input",
                    progress_message="Queued",
                    attempt_count=1,
                )
            )
            session.commit()

        client = TestClient(create_app())
        response = client.get(f"/pipeline/jobs/{job_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["request_summary"],
            "Recommendations for Alex Chen: social computing, mentor matching",
        )

    def test_get_pipeline_job_result_returns_409_until_completed(self) -> None:
        client = TestClient(create_app())
        response = client.get("/pipeline/jobs/job_pending/result")
        self.assertEqual(response.status_code, 409)

    def test_get_pipeline_job_result_returns_persisted_payload_when_succeeded(self) -> None:
        job_id = self._job_id("result")
        with SessionLocal() as session:
            repo = PipelineJobRepository(session)
            repo.add_job(
                PipelineJob(
                    id=job_id,
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
                    id=f"res_{uuid.uuid4().hex[:12]}",
                    job_id=job_id,
                    result_payload={
                        "skill5_result": {
                            "recommendations": {
                                "mentors": [{"id": "m1", "name": "Dr. Ada", "reasons": ["topic fit"]}],
                                "projects": [{"id": "p1", "title": "Graph Lab"}],
                                "teammates": [{"id": "s2", "name": "Riley"}],
                            }
                        }
                    },
                    summary_payload={"mentor_count": 1, "project_count": 1, "teammate_count": 1},
                    artifacts_payload={},
                )
            )
            session.commit()
        client = TestClient(create_app())
        response = client.get(f"/pipeline/jobs/{job_id}/result")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job_id"], job_id)
        self.assertIn("result", response.json())
        self.assertEqual(response.json()["result"]["mentors"]["count"], 1)
        self.assertEqual(response.json()["result"]["projects"]["count"], 1)
        self.assertEqual(response.json()["result"]["teammates"]["count"], 1)
        self.assertIn("raw_result", response.json())

    def test_retry_pipeline_job_creates_replacement_job(self) -> None:
        job_id = self._job_id("failed")
        with SessionLocal() as session:
            repo = PipelineJobRepository(session)
            repo.add_job(
                PipelineJob(
                    id=job_id,
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
            response = client.post(f"/pipeline/jobs/{job_id}/retry")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "queued")
        self.assertNotEqual(response.json()["job_id"], job_id)
