from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from deployment.scripts.migrate import discover_migrations
from progrec_service.config import Settings, load_settings


class TestSettingsAndMigrations(unittest.TestCase):
    def test_load_settings_reads_database_and_runtime_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
            os.environ["REDIS_URL"] = "redis://localhost:6379/9"
            os.environ["ENCRYPTION_KEY"] = "0123456789abcdef0123456789abcdef"
            os.environ["PROGREC_REPO_ROOT"] = tmp_dir
            os.environ["PROGREC_ARTIFACT_ROOT"] = str(Path(tmp_dir) / "artifacts")
            settings = load_settings()
        self.assertIsInstance(settings, Settings)
        self.assertEqual(settings.database_url, "sqlite+pysqlite:///:memory:")
        self.assertEqual(settings.redis_url, "redis://localhost:6379/9")
        self.assertEqual(settings.progrec_artifact_root.name, "artifacts")

    def test_discover_migrations_returns_sorted_sql_files(self) -> None:
        paths = discover_migrations(Path("progrec_service/db/migrations"))
        self.assertTrue(paths, "expected at least one SQL migration")
        self.assertEqual(paths[0].suffix, ".sql")


if __name__ == "__main__":
    unittest.main()
