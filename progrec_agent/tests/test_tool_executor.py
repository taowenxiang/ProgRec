from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from progrec_agent.session import AgentSession
from progrec_agent.tool_executor import ToolExecutor


class TestToolExecutor(unittest.TestCase):
    def test_show_current_profile_returns_session_profile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            session.set_student_profile({"student_id": "s_002", "major": "CS"})
            executor = ToolExecutor(repo_root=Path("."), temp_dir=Path(td))
            result = executor.execute("show_current_profile", {}, session=session)
            self.assertTrue(result.ok)
            self.assertEqual(result.payload["student_profile"]["student_id"], "s_002")

    def test_inspect_artifacts_returns_session_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            session.set_resource_context({"resource_mode": "demo"})
            executor = ToolExecutor(repo_root=Path("."), temp_dir=Path(td))
            result = executor.execute("inspect_artifacts", {}, session=session)
            self.assertTrue(result.ok)
            self.assertEqual(result.payload["resource_context"]["resource_mode"], "demo")


if __name__ == "__main__":
    unittest.main()
