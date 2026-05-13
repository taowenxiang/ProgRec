from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from progrec_service.app import create_app


class TestSystemRoutes(unittest.TestCase):
    def test_health_returns_ok(self) -> None:
        client = TestClient(create_app())
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_models_recommended_returns_default_model(self) -> None:
        client = TestClient(create_app())
        response = client.get("/models/recommended")
        self.assertEqual(response.status_code, 200)
        self.assertIn("recommended", response.json())


if __name__ == "__main__":
    unittest.main()
