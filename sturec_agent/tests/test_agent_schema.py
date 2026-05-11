from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sturec_agent.agent_schema import AgentProfile, ClarificationQuestion, ExecutionPlan
from sturec_agent.session import AgentSession


class TestAgentSchema(unittest.TestCase):
    def test_agent_profile_defaults(self) -> None:
        profile = AgentProfile(goal="find an NLP mentor")
        self.assertEqual(profile.goal, "find an NLP mentor")
        self.assertEqual(profile.research_direction, [])
        self.assertEqual(profile.desired_outcomes, [])
        self.assertFalse(profile.preferences["prefer_diversity"])

    def test_execution_plan_defaults(self) -> None:
        plan = ExecutionPlan()
        self.assertFalse(plan.need_clarification)
        self.assertFalse(plan.run_skill3)
        self.assertEqual(plan.clarification_questions, [])

    def test_clarification_question_fields(self) -> None:
        question = ClarificationQuestion(key="time_budget", question="How many hours per week?")
        self.assertEqual(question.key, "time_budget")
        self.assertIn("hours", question.question)

    def test_session_tracks_agent_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            session.conversation_history.append({"role": "user", "content": "hello"})
            session.rerun_count = 1
            self.assertEqual(session.conversation_history[0]["role"], "user")
            self.assertEqual(session.rerun_count, 1)


if __name__ == "__main__":
    unittest.main()
