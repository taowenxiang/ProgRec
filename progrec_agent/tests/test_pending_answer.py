from __future__ import annotations

import unittest

from progrec_agent.dialog.pending_answer import parse_pending_answer
from progrec_agent.dialog.state import PendingQuestion


class TestPendingAnswer(unittest.TestCase):
    def test_profile_source_variants(self) -> None:
        question = PendingQuestion(
            slot_name="profile_source",
            question="Use existing profile or temporary profile?",
            expected_answer_shape="existing_profile|temporary_profile",
        )

        self.assertEqual(parse_pending_answer(question, "temporary").value, "temporary_profile")
        self.assertEqual(
            parse_pending_answer(question, "build a temporary profile from your description").value,
            "temporary_profile",
        )
        self.assertEqual(
            parse_pending_answer(question, "use an existing student profile").value,
            "existing_profile",
        )

    def test_mode_variants(self) -> None:
        question = PendingQuestion(
            slot_name="mode",
            question="Use demo or graph mode?",
            expected_answer_shape="demo|graph",
        )

        self.assertEqual(parse_pending_answer(question, "use the real graph").value, "graph")
        self.assertEqual(parse_pending_answer(question, "graph mode please").value, "graph")
        self.assertEqual(parse_pending_answer(question, "demo mode").value, "demo")

    def test_free_text_slots_preserve_answer(self) -> None:
        topic = PendingQuestion("research_topic", "What research topic?", "free_text")
        program = PendingQuestion("program_type", "What program?", "free_text")

        self.assertEqual(parse_pending_answer(topic, "NLP safety and trustworthy AI").value, "NLP safety and trustworthy AI")
        self.assertEqual(parse_pending_answer(program, "undergraduate research").value, "undergraduate research")


if __name__ == "__main__":
    unittest.main()
