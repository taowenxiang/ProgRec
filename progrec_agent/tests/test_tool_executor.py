from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import json
from unittest.mock import patch

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

    def test_show_recommended_mentor_profile_returns_top_mentor_profile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            mentors_path = td_path / "mentor_profiles_standard.json"
            mentors_path.write_text(
                json.dumps(
                    {
                        "version": "test",
                        "mentors": [
                            {
                                "mentor_id": "m_101",
                                "name": "Dr. Ada",
                                "department": "Computer Science",
                                "research_areas": ["nlp", "information retrieval"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            session = AgentSession(temp_dir=td_path)
            session.set_resource_context({"mentors_path": str(mentors_path)})
            session.skill5_result = {
                "recommendations": {
                    "mentors": [
                        {
                            "mentor_id": "m_101",
                            "mentor_name": "Dr. Ada",
                            "final_score": 0.97,
                            "rank": 1,
                        }
                    ]
                }
            }
            executor = ToolExecutor(repo_root=Path("."), temp_dir=td_path)
            result = executor.execute("show_recommended_mentor_profile", {}, session=session)
            self.assertTrue(result.ok)
            self.assertEqual(result.payload["mentor_profile"]["mentor_id"], "m_101")
            self.assertEqual(result.payload["mentor_profile"]["name"], "Dr. Ada")
            self.assertEqual(result.payload["rank"], 1)

    @patch("progrec_agent.tool_executor.resolve_resource_config")
    @patch("progrec_agent.tool_executor.ProgRecOrchestrator.recommend_for_student_id")
    def test_recommend_full_pipeline_uses_explicit_graph_mode_bundle(
        self,
        mock_recommend_for_student_id,
        mock_resolve_resource_config,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            session = AgentSession(temp_dir=td_path)
            bundle = object()
            mock_resolve_resource_config.return_value = bundle
            mock_recommend_for_student_id.return_value = {
                "mode": "dataset_mode",
                "student_profile": {"student_id": "jamie-taylor-00008"},
                "resource_context": {"resource_mode": "graph"},
                "skill3_result": {},
                "skill4_result": {},
                "skill5_result": {"recommendations": {"mentors": [], "projects": [], "teammates": []}},
                "temporary_paths": [],
            }
            executor = ToolExecutor(repo_root=Path("."), temp_dir=td_path)

            result = executor.execute(
                "recommend_full_pipeline",
                {"student_id": "jamie-taylor-00008", "mode": "graph"},
                session=session,
            )

            self.assertTrue(result.ok)
            mock_resolve_resource_config.assert_called_once_with("graph", executor.repo_root, validate_graph=True)
            mock_recommend_for_student_id.assert_called_once_with("jamie-taylor-00008", top_k=5, bundle=bundle)


if __name__ == "__main__":
    unittest.main()
