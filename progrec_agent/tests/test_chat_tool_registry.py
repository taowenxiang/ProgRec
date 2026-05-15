from __future__ import annotations

import unittest

from progrec_agent.chat_tool_registry import get_chat_tool, list_chat_tools, planner_tool_context


class TestChatToolRegistry(unittest.TestCase):
    def test_lists_target_specific_tools(self) -> None:
        tool_names = [tool.name for tool in list_chat_tools()]

        self.assertIn("/student-profiling.build_temporary_profile", tool_names)
        self.assertIn("/mentor-discovery.rank_mentors", tool_names)
        self.assertIn("/project-teammate-discovery.recommend_projects", tool_names)
        self.assertIn("/project-teammate-discovery.recommend_teammates", tool_names)

    def test_mentor_tool_is_gated_to_mentor_target(self) -> None:
        tool = get_chat_tool("/mentor-discovery.rank_mentors")

        self.assertEqual(tool.skill_id, "/mentor-discovery")
        self.assertEqual(tool.allowed_targets, ["mentor"])
        self.assertIn("profile", tool.required_arguments)

    def test_planner_context_mentions_no_extra_categories(self) -> None:
        context = planner_tool_context()

        self.assertIn("/mentor-discovery.rank_mentors", context)
        self.assertIn("Do not call this for project or teammate recommendations", context)


if __name__ == "__main__":
    unittest.main()
