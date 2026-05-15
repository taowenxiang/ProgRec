from __future__ import annotations

import unittest
from unittest.mock import Mock

from progrec_agent.agent_planner import AgentPlanner, _planner_state_snapshot
from progrec_agent.dialog.state import DialogState


class TestAgentPlanner(unittest.TestCase):
    def test_planner_parses_llm_action(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "action": "ask_user",
            "message": "What kind of research opportunity are you targeting?",
            "reasoning_summary": "Need profile context.",
        }
        planner = AgentPlanner(llm_client=llm)

        action = planner.plan_next_action(DialogState(), "Find me an NLP mentor.")

        self.assertEqual(action.action, "ask_user")
        self.assertIn("research opportunity", action.message)
        prompt = llm.complete_json.call_args.args[0]
        self.assertIn("/mentor-discovery.recommend_mentors", prompt)
        self.assertIn("/mentor-discovery.get_mentor_by_rank", prompt)
        self.assertIn("Do not run extra recommendation categories", prompt)

    def test_invalid_llm_action_returns_safe_ask_user(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {"action": "call_tool", "tool_name": "/unknown.run"}
        planner = AgentPlanner(llm_client=llm)

        action = planner.plan_next_action(DialogState(), "Find me an NLP mentor.")

        self.assertEqual(action.action, "ask_user")
        self.assertIn("clarify", action.message.lower())

    def test_state_snapshot_exposes_latest_result_refs(self) -> None:
        state = DialogState()
        state.execution_context.latest_result_refs = {"mentor_result": "rr_mentor_001"}

        snapshot = _planner_state_snapshot(state)

        self.assertEqual(snapshot["latest_result_refs"]["mentor_result"], "rr_mentor_001")


if __name__ == "__main__":
    unittest.main()
