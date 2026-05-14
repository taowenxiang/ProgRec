from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from progrec_service.app import create_app
from progrec_service.services.encryption import decrypt_secret, encrypt_secret


class TestRuntimeProfileRoutes(unittest.TestCase):
    def test_encrypt_and_decrypt_roundtrip(self) -> None:
        token = "sk-test"
        ciphertext = encrypt_secret(token, "0123456789abcdef0123456789abcdef")
        self.assertNotEqual(ciphertext, token)
        plaintext = decrypt_secret(ciphertext, "0123456789abcdef0123456789abcdef")
        self.assertEqual(plaintext, token)

    def test_runtime_profile_test_route_calls_models_probe(self) -> None:
        client = TestClient(create_app())
        with patch("progrec_service.services.runtime_profiles.fetch_available_models", return_value=["gpt-4.1-mini"]):
            response = client.post(
                "/runtime-profiles/test",
                json={
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4.1-mini",
                    "api_key": "sk-test",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["model"], "gpt-4.1-mini")

    def test_runtime_profile_create_persists_masked_record(self) -> None:
        client = TestClient(create_app())
        response = client.post(
            "/runtime-profiles",
            json={
                "label": "Saved profile",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4.1-mini",
                "api_key": "sk-test-9999",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["api_key_last4"], "9999")
        self.assertIn("profile_id", response.json())
