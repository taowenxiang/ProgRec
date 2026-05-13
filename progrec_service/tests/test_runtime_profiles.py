from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from progrec_service.app import create_app
from progrec_service.services.encryption import decrypt_secret, encrypt_secret


class TestRuntimeProfileEncryption(unittest.TestCase):
    def test_encrypt_and_decrypt_roundtrip(self) -> None:
        token = "sk-test"
        ciphertext = encrypt_secret(token, "0123456789abcdef0123456789abcdef")
        self.assertNotEqual(ciphertext, token)
        plaintext = decrypt_secret(ciphertext, "0123456789abcdef0123456789abcdef")
        self.assertEqual(plaintext, token)

    def test_runtime_profile_test_route_requires_api_key(self) -> None:
        client = TestClient(create_app())
        response = client.post(
            "/runtime-profiles/test",
            json={"base_url": "https://api.openai.com/v1", "model": "gpt-4.1-mini"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ok"], False)

    def test_runtime_profile_test_route_accepts_api_key(self) -> None:
        client = TestClient(create_app())
        response = client.post(
            "/runtime-profiles/test",
            json={
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4.1-mini",
                "api_key": "sk-test",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ok"], True)
