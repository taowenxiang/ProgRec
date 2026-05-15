from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from progrec_service.services.runtime_context import resolve_runtime_context


class TestRuntimeContext(unittest.TestCase):
    def test_resolve_runtime_context_reads_env_txt_defaults_in_development(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env_path = Path(td) / "env.txt"
            env_path.write_text("sk-test-1234\ndemo-model\nhttps://example.com/v1\n", encoding="utf-8")

            with patch("progrec_service.services.runtime_context.settings") as settings:
                settings.app_env = "development"
                settings.runtime_env_file = env_path
                context = resolve_runtime_context(ephemeral_runtime=None, runtime_profile_id=None)

        self.assertEqual(context.source, "env_file")
        self.assertEqual(context.api_key, "sk-test-1234")
        self.assertEqual(context.model, "demo-model")
        self.assertEqual(context.base_url, "https://example.com/v1")

    def test_resolve_runtime_context_does_not_read_env_txt_in_production(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env_path = Path(td) / "env.txt"
            env_path.write_text("sk-test-1234\ndemo-model\nhttps://example.com/v1\n", encoding="utf-8")

            with patch("progrec_service.services.runtime_context.settings") as settings:
                settings.app_env = "production"
                settings.runtime_env_file = env_path
                with self.assertRaisesRegex(ValueError, "ephemeral runtime or runtime_profile_id"):
                    resolve_runtime_context(ephemeral_runtime=None, runtime_profile_id=None)
