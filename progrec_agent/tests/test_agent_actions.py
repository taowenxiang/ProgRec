from __future__ import annotations

import unittest

from progrec_agent.agent_actions import parse_planner_action


class TestAgentActions(unittest.TestCase):
    def test_parse_ask_user_action(self) -> None:
        action = parse_planner_action(
            {
                "action": "ask_user",
                "message": "Tell me about your research background.",
                "reasoning_summary": "Need profile context.",
            },
            allowed_tools={"/mentor-discovery.rank_mentors"},
        )

        self.assertEqual(action.action, "ask_user")
        self.assertEqual(action.message, "Tell me about your research background.")
        self.assertEqual(action.reasoning_summary, "Need profile context.")

    def test_rejects_unknown_action(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_planner_action({"action": "dance"}, allowed_tools=set())

        self.assertIn("Unknown planner action", str(ctx.exception))

    def test_rejects_unknown_tool(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_planner_action(
                {"action": "call_tool", "tool_name": "/unknown.run", "arguments": {}},
                allowed_tools={"/mentor-discovery.rank_mentors"},
            )

        self.assertIn("Unknown chat tool", str(ctx.exception))

    def test_call_tool_defaults_arguments(self) -> None:
        action = parse_planner_action(
            {"action": "call_tool", "tool_name": "/mentor-discovery.rank_mentors"},
            allowed_tools={"/mentor-discovery.rank_mentors"},
        )

        self.assertEqual(action.action, "call_tool")
        self.assertEqual(action.tool_name, "/mentor-discovery.rank_mentors")
        self.assertEqual(action.arguments, {})


if __name__ == "__main__":
    unittest.main()
