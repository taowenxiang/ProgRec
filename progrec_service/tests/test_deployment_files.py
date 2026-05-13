from __future__ import annotations

import unittest
from pathlib import Path


class TestDeploymentFiles(unittest.TestCase):
    def test_compose_file_exists(self) -> None:
        self.assertTrue(Path("deployment/docker-compose.yml").is_file())
