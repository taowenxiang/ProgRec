from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from progrec_service.app import create_app


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
