from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from progrec_agent import repl
from progrec_agent.agent_schema import AgentProfile, ClarificationQuestion, ExecutionPlan
from progrec_agent.session import AgentSession


class TestReplAgentFlow(unittest.TestCase):
    @patch("builtins.input", side_effect=["I want an NLP mentor", "exit"])
    @patch("progrec_agent.repl.run_agent_turn")
    def test_free_text_enters_agent_flow(self, mock_turn, _mock_input) -> None:
        mock_turn.return_value = "summary"
        exit_code = repl.main()
        self.assertEqual(exit_code, 0)
        mock_turn.assert_called_once()

    @patch("builtins.input", side_effect=["show trace", "exit"])
    @patch("builtins.print")
    def test_show_trace_without_history(self, mock_print, _mock_input) -> None:
        exit_code = repl.main()
        self.assertEqual(exit_code, 0)
        printed = "\n".join(" ".join(str(arg) for arg in call.args) for call in mock_print.call_args_list)
        self.assertIn("No trace available.", printed)

    @patch("progrec_agent.repl.build_strategy", return_value={"top_k": 5, "max_reruns": 0})
    @patch("progrec_agent.repl.judge_results", return_value={"rerun_needed": False, "reasons": [], "stop_reason": "quality acceptable"})
    @patch("progrec_agent.repl.build_execution_plan")
    @patch("progrec_agent.repl.build_profiles_from_text")
    @patch("progrec_agent.repl._build_llm_client_from_env", return_value=object())
    def test_clarification_answer_resumes_pipeline(
        self,
        _mock_llm,
        mock_profiles,
        mock_plan,
        _mock_judge,
        _mock_strategy,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            orchestrator = unittest.mock.Mock()
            orchestrator.recommend_for_profile.return_value = {
                "mode": "custom_profile_mode",
                "student_profile": {"student_id": "cli-custom-1"},
                "resource_context": {"resource_mode": "custom_profile_mode"},
                "skill3_result": {"student_id": "cli-custom-1", "mentor_candidates": []},
                "skill4_result": {"target_student_id": "cli-custom-1", "mentor_project_teammate_recommendations": []},
                "skill5_result": {"recommendations": {"mentors": [], "projects": [], "teammates": []}},
                "temporary_paths": [],
            }
            mock_profiles.side_effect = [
                (
                    {"student_id": "cli-custom-1", "major": "CS", "skills": [], "interests": [], "experience_summary": "", "availability": "moderate"},
                    AgentProfile(goal="I want an NLP mentor"),
                ),
                (
                    {"student_id": "cli-custom-1", "major": "CS", "skills": [], "interests": [], "experience_summary": "3 hours per week", "availability": "moderate"},
                    AgentProfile(goal="I want an NLP mentor", constraints={"time_budget_hours_per_week": 3}),
                ),
            ]
            mock_plan.side_effect = [
                ExecutionPlan(
                    need_clarification=True,
                    clarification_questions=[ClarificationQuestion(key="time_budget", question="How many hours per week?")],
                    run_skill3=False,
                    run_skill4=False,
                    run_skill5=False,
                ),
                ExecutionPlan(
                    need_clarification=False,
                    run_skill3=True,
                    run_skill4=True,
                    run_skill5=True,
                ),
            ]

            first = repl.run_agent_turn(session, "I want an NLP mentor", orchestrator)
            self.assertIn("Before I run recommendations", first)
            self.assertEqual(session.pending_clarification_questions[0]["key"], "time_budget")

            second = repl.run_agent_turn(session, "3 hours per week", orchestrator)
            self.assertIn("Goal: I want an NLP mentor", second)
            orchestrator.recommend_for_profile.assert_called_once()
            self.assertEqual(session.pending_clarification_questions, [])


if __name__ == "__main__":
    unittest.main()
