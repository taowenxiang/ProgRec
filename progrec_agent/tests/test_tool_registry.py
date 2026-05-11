from __future__ import annotations

import unittest

from progrec_agent.tool_registry import get_tool, list_tools


class TestToolRegistry(unittest.TestCase):
    def test_rebuild_graph_requires_confirmation(self) -> None:
        tool = get_tool("rebuild_skill2_graph")
        self.assertEqual(tool["risk_level"], "confirm")
        self.assertTrue(tool["requires_confirmation"])

    def test_recommendation_tool_is_safe(self) -> None:
        tool = get_tool("recommend_full_pipeline")
        self.assertEqual(tool["risk_level"], "safe")

    def test_list_tools_includes_registry_entries(self) -> None:
        names = {tool["name"] for tool in list_tools()}
        self.assertIn("show_current_profile", names)


if __name__ == "__main__":
    unittest.main()
