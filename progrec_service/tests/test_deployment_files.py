from __future__ import annotations

import unittest
from pathlib import Path


class TestDeploymentFiles(unittest.TestCase):
    def test_compose_file_exists(self) -> None:
        self.assertTrue(Path("deployment/docker-compose.yml").is_file())

    def test_compose_file_supports_cloudflare_tunnel_profile(self) -> None:
        compose_text = Path("deployment/docker-compose.yml").read_text()
        self.assertIn("cloudflared:", compose_text)
        self.assertIn("cloudflare-tunnel", compose_text)

    def test_env_example_contains_tunnel_token(self) -> None:
        env_text = Path("deployment/.env.example").read_text()
        self.assertIn("CLOUDFLARE_TUNNEL_TOKEN=", env_text)
