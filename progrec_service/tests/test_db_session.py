from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from deployment.scripts.migrate import discover_migrations
from progrec_service.config import Settings, load_settings
from progrec_service.db.models import AgentSession, Base, PipelineJob, RuntimeProfile
from progrec_service.db.session import build_engine, build_session_factory


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


class TestDatabaseModels(unittest.TestCase):
    def test_tables_can_be_created_in_sqlite(self) -> None:
        engine = build_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.assertIn("runtime_profiles", Base.metadata.tables)
        self.assertIn("agent_sessions", Base.metadata.tables)
        self.assertIn("pipeline_jobs", Base.metadata.tables)

    def test_session_factory_persists_runtime_profile(self) -> None:
        engine = build_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        session_factory = build_session_factory(engine)
        with session_factory() as session:
            row = RuntimeProfile(
                id="rp_001",
                label="Saved profile",
                base_url="https://api.openai.com/v1",
                model="gpt-4.1-mini",
                api_key_ciphertext="cipher",
                api_key_last4="test",
            )
            session.add(row)
            session.commit()
        with session_factory() as session:
            stored = session.get(RuntimeProfile, "rp_001")
        self.assertIsNotNone(stored)
        self.assertEqual(stored.model, "gpt-4.1-mini")


if __name__ == "__main__":
    unittest.main()
