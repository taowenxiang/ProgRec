from __future__ import annotations

import unittest
from pathlib import Path

from progrec_agent.skill_catalog import build_skill_catalog


class TestSkillCatalog(unittest.TestCase):
    def test_catalog_contains_compact_cards_for_core_skills(self) -> None:
        catalog = build_skill_catalog(Path("."))
        cards = {card.skill_id: card for card in catalog.cards}

        self.assertIn("/student-profiling", cards)
        self.assertIn("/mentor-discovery", cards)
        self.assertIn("/project-teammate-discovery", cards)
        self.assertIn("/social-ranking", cards)
        self.assertIn("mentor", cards["/mentor-discovery"].when_to_use.lower())
        self.assertIn("recommend_full_pipeline", cards["/mentor-discovery"].allowed_tools)

    def test_catalog_prompt_context_is_compact_and_names_allowed_tools(self) -> None:
        catalog = build_skill_catalog(Path("."))
        prompt_context = catalog.to_prompt_context()

        self.assertIn("/mentor-discovery", prompt_context)
        self.assertIn("recommend_full_pipeline", prompt_context)
        self.assertLess(len(prompt_context), 9000)

    def test_full_prompt_context_includes_complete_skill_docs(self) -> None:
        catalog = build_skill_catalog(Path("."))
        prompt_context = catalog.to_full_prompt_context()

        self.assertIn("skill_id: /mentor-discovery", prompt_context)
        self.assertIn("# Mentor Discovery (Skill 3)", prompt_context)
        self.assertIn("# Skill 4", prompt_context)
        self.assertIn("# Student Recommendation Ranker", prompt_context)
        self.assertIn("Critical: Student ID Alignment", prompt_context)


if __name__ == "__main__":
    unittest.main()
