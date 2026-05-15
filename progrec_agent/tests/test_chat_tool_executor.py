from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.runtime.chat_tool_executor import ChatToolExecutor


class TestChatToolExecutor(unittest.TestCase):
    def test_build_temporary_profile_records_skill_trace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=Mock())
            result = executor.execute(
                "/student-profiling.build_temporary_profile",
                {
                    "profile_context": {
                        "research_topic": "NLP and trustworthy AI",
                        "program_type": "undergraduate research",
                        "experience_level": "medium",
                    }
                },
            )

        self.assertEqual(result.skill_id, "/student-profiling")
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.payload["result_type"], "student_profile")
        self.assertEqual(result.payload["profile"]["interests"], ["nlp", "trustworthy ai"])
        self.assertIn("profile", result.payload["payload"])

    def test_build_temporary_profile_accepts_free_text_profile_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=Mock())
            result = executor.execute(
                "/student-profiling.build_temporary_profile",
                {
                    "profile_context": (
                        "I am an undergraduate CS student with Python and some NLP project "
                        "experience. I want a research opportunity for next semester."
                    )
                },
            )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.payload["profile"]["student_id"][:9], "chat-temp")
        self.assertIn("undergraduate", result.payload["profile"]["experience_summary"].lower())

    def test_recommend_mentors_returns_result_reference_metadata(self) -> None:
        runtime = Mock()
        runtime.run_mentor_recommendation_for_profile.return_value = {
            "student_profile": {"student_id": "chat-temp-1"},
            "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}, {"mentor_id": "m2"}]},
        }
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=runtime)
            result = executor.execute(
                "/mentor-discovery.recommend_mentors",
                {
                    "student_profile_ref": {
                        "result_ref": "sp_001",
                        "payload": {"profile": {"student_id": "chat-temp-1"}},
                    },
                    "top_k": 5,
                },
            )

        runtime.run_mentor_recommendation_for_profile.assert_called_once()
        self.assertEqual(result.skill_id, "/mentor-discovery")
        self.assertEqual(result.payload["result_type"], "mentor_result")
        self.assertEqual(result.payload["summary"]["count"], 2)
        self.assertIn("skill3_result", result.payload)

    def test_legacy_rank_mentors_alias_still_returns_flattened_payload(self) -> None:
        runtime = Mock()
        runtime.run_mentor_recommendation_for_profile.return_value = {
            "student_profile": {"student_id": "chat-temp-1"},
            "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}]},
        }
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=runtime)
            result = executor.execute(
                "/mentor-discovery.rank_mentors",
                {"profile": {"student_id": "chat-temp-1"}, "top_k": 5},
            )

        self.assertEqual(result.payload["result_type"], "mentor_result")
        self.assertIn("skill3_result", result.payload)

    def test_explain_mentor_match_returns_summary_card(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=Mock())
            result = executor.execute(
                "/mentor-discovery.explain_mentor_match",
                {
                    "mentor_result_ref": {
                        "result_ref": "rr_mentor_001",
                        "result_type": "mentor_result",
                        "payload": {
                            "skill3_result": {
                                "mentor_candidates": [
                                    {"mentor_id": "m1", "reason": "Strong NLP alignment."}
                                ]
                            }
                        },
                    },
                    "rank": 1,
                },
            )

        self.assertEqual(result.skill_id, "/mentor-discovery")
        self.assertEqual(result.payload["mentor_id"], "m1")
        self.assertEqual(result.payload["summary"], "Strong NLP alignment.")

    def test_explain_project_match_returns_summary_card(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=Mock())
            result = executor.execute(
                "/project-teammate-discovery.explain_project_match",
                {
                    "project_result_ref": {
                        "result_ref": "rr_project_001",
                        "result_type": "project_result",
                        "payload": {
                            "projects": [
                                {"project_id": "p1", "reason": "Fits your CV and Python background."}
                            ]
                        },
                    },
                    "rank": 1,
                },
            )

        self.assertEqual(result.skill_id, "/project-teammate-discovery")
        self.assertEqual(result.payload["project_id"], "p1")
        self.assertEqual(result.payload["summary"], "Fits your CV and Python background.")

    def test_explain_teammate_match_returns_summary_card(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=Mock())
            result = executor.execute(
                "/project-teammate-discovery.explain_teammate_match",
                {
                    "teammate_result_ref": {
                        "result_ref": "rr_teammate_001",
                        "result_type": "teammate_result",
                        "payload": {
                            "teammates": [
                                {"student_id": "s1", "reason": "Strong complementary systems skills."}
                            ]
                        },
                    },
                    "rank": 1,
                },
            )

        self.assertEqual(result.skill_id, "/project-teammate-discovery")
        self.assertEqual(result.payload["student_id"], "s1")
        self.assertEqual(result.payload["summary"], "Strong complementary systems skills.")


if __name__ == "__main__":
    unittest.main()
