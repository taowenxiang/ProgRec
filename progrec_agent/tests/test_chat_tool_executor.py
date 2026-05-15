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
        self.assertEqual(result.payload["profile"]["interests"], ["nlp", "trustworthy ai"])

    def test_rank_mentors_calls_mentor_only_runtime(self) -> None:
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

        runtime.run_mentor_recommendation_for_profile.assert_called_once()
        self.assertEqual(result.skill_id, "/mentor-discovery")
        self.assertIn("skill3_result", result.payload)


if __name__ == "__main__":
    unittest.main()
