from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from progrec_agent.agent_schema import (
    AgentProfile,
    ClarificationQuestion,
    ExecutionPlan,
    PendingConfirmation,
    RouterDecision,
)
from progrec_agent.session import AgentSession


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

    def test_router_decision_defaults(self) -> None:
        decision = RouterDecision(
            message_type="domain_task",
            intent="recommend_mentor",
            confidence=0.2,
            candidate_tools=[],
        )
        self.assertEqual(decision.intent, "recommend_mentor")
        self.assertEqual(decision.candidate_tools, [])
        self.assertFalse(decision.needs_clarification)

    def test_session_tracks_pending_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            pending = PendingConfirmation(
                action_id="rebuild-graph-1",
                tool_name="rebuild_skill2_graph",
                arguments={"mode": "graph"},
                prompt="Rebuild graph now?",
            )
            session.set_pending_confirmation(pending)
            self.assertEqual(session.pending_confirmation_action["tool_name"], "rebuild_skill2_graph")
            session.clear_pending_confirmation()
            self.assertIsNone(session.pending_confirmation_action)


if __name__ == "__main__":
    unittest.main()
