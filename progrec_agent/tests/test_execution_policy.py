from __future__ import annotations

import unittest

from progrec_agent.agent_schema import RouterDecision
from progrec_agent.execution_policy import choose_action


class TestExecutionPolicy(unittest.TestCase):
    def test_confirmation_required_for_confirm_tool(self) -> None:
        decision = RouterDecision(intent="rebuild", confidence=0.9, candidate_tools=["rebuild_skill2_graph"])
        action = choose_action(decision, tool_name="rebuild_skill2_graph", tool_meta={"risk_level": "confirm"})
        self.assertEqual(action["kind"], "confirm")

    def test_low_confidence_routes_to_clarification(self) -> None:
        decision = RouterDecision(
            intent="chat",
            confidence=0.3,
            candidate_tools=[],
            needs_clarification=True,
            clarification_question="Which student?",
        )
        action = choose_action(decision, tool_name="", tool_meta={})
        self.assertEqual(action["kind"], "clarify")


if __name__ == "__main__":
    unittest.main()
