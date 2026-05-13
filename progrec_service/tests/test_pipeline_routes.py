from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from progrec_service.app import create_app


class TestPipelineRoutes(unittest.TestCase):
    def test_create_pipeline_job(self) -> None:
        client = TestClient(create_app())
        payload = {
            "runtime_profile": {
                "mode": "ephemeral",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4.1-mini",
                "api_key": "sk-test",
            },
            "job_type": "recommend_existing_student",
            "mode": "graph",
            "student_id": "jamie-taylor-00008",
            "top_k": 10,
        }
        response = client.post("/pipeline/jobs", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "queued")
