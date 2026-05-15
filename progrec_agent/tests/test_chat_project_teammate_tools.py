from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.runtime.chat_tool_executor import ChatToolExecutor


class TestChatProjectTeammateTools(unittest.TestCase):
    def test_recommend_projects_calls_project_runtime(self) -> None:
        runtime = Mock()
        runtime.run_project_recommendations_for_profile.return_value = {
            "student_profile": {"student_id": "chat-temp-1"},
            "skill4_result": {
                "mentor_project_teammate_recommendations": [
                    {"project_recommendations": [{"project_id": "p1"}], "teammate_recommendations": []}
                ]
            },
            "projects": [{"project_id": "p1"}],
        }
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=runtime)
            result = executor.execute(
                "/project-teammate-discovery.recommend_projects",
                {"profile": {"student_id": "chat-temp-1"}, "top_k": 5},
            )

        runtime.run_project_recommendations_for_profile.assert_called_once()
        self.assertEqual(result.skill_id, "/project-teammate-discovery")
        self.assertEqual(result.payload["projects"], [{"project_id": "p1"}])

    def test_recommend_teammates_calls_teammate_runtime(self) -> None:
        runtime = Mock()
        runtime.run_teammate_recommendations_for_profile.return_value = {
            "student_profile": {"student_id": "chat-temp-1"},
            "skill4_result": {
                "mentor_project_teammate_recommendations": [
                    {"project_recommendations": [], "teammate_recommendations": [{"student_id": "s2"}]}
                ]
            },
            "teammates": [{"student_id": "s2"}],
        }
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=runtime)
            result = executor.execute(
                "/project-teammate-discovery.recommend_teammates",
                {"profile": {"student_id": "chat-temp-1"}, "top_k": 5},
            )

        runtime.run_teammate_recommendations_for_profile.assert_called_once()
        self.assertEqual(result.skill_id, "/project-teammate-discovery")
        self.assertEqual(result.payload["teammates"], [{"student_id": "s2"}])


if __name__ == "__main__":
    unittest.main()
