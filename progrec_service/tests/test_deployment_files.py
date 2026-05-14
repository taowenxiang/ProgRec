from __future__ import annotations

import unittest
from pathlib import Path


class TestDeploymentFiles(unittest.TestCase):
    def test_env_example_uses_container_repo_root(self) -> None:
        env_text = Path("deployment/.env.example").read_text(encoding="utf-8")
        self.assertIn("PROGREC_REPO_ROOT=/srv/app", env_text)

    def test_compose_file_runs_migration_before_api(self) -> None:
        compose_text = Path("deployment/docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("python deployment/scripts/migrate.py", compose_text)

    def test_runbook_mentions_pipeline_status_and_result_routes(self) -> None:
        runbook_text = Path("deployment/PRODUCTION_RUNBOOK.md").read_text(encoding="utf-8")
        self.assertIn("GET /pipeline/jobs/{id}", runbook_text)
        self.assertIn("GET /pipeline/jobs/{id}/result", runbook_text)
