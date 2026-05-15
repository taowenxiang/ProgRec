from __future__ import annotations

import unittest

from progrec_agent.chat_tool_registry import get_chat_tool, list_chat_tools, planner_tool_context


class TestChatToolRegistry(unittest.TestCase):
    def test_lists_target_specific_tools(self) -> None:
        tool_names = [tool.name for tool in list_chat_tools()]

        self.assertIn("/student-profiling.build_temporary_profile", tool_names)
        self.assertIn("/mentor-discovery.recommend_mentors", tool_names)
        self.assertIn("/mentor-discovery.get_mentor_by_rank", tool_names)
        self.assertIn("/project-teammate-discovery.recommend_projects", tool_names)
        self.assertIn("/project-teammate-discovery.recommend_teammates", tool_names)

    def test_mentor_tool_resolves_from_canonical_contract(self) -> None:
        tool = get_chat_tool("/mentor-discovery.recommend_mentors")

        self.assertEqual(tool.skill_id, "/mentor-discovery")
        self.assertIn("student_profile_ref", tool.required_arguments)
        self.assertIn("returns=mentor_result", tool.planner_notes)

    def test_legacy_mentor_alias_is_still_available(self) -> None:
        tool = get_chat_tool("/mentor-discovery.rank_mentors")

        self.assertEqual(tool.skill_id, "/mentor-discovery")
        self.assertIn("profile", tool.required_arguments)

    def test_planner_context_mentions_no_extra_categories(self) -> None:
        context = planner_tool_context()

        self.assertIn("/mentor-discovery.recommend_mentors", context)
        self.assertIn("/mentor-discovery.get_mentor_by_rank", context)
        self.assertIn("followups", context)


if __name__ == "__main__":
    unittest.main()
