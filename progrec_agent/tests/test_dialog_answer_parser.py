from __future__ import annotations

import unittest

from progrec_agent.dialog.answer_parser import apply_pending_answer
from progrec_agent.dialog.merge import merge_intent_frame
from progrec_agent.dialog.state import DialogState, PendingQuestion
from progrec_agent.nlu.schema import IntentFrame, SlotValue


class TestDialogMerge(unittest.TestCase):
    def test_merge_promotes_explicit_entities_to_resolved_slots(self) -> None:
        state = DialogState()
        frame = IntentFrame(
            intent="recommendation_request",
            entities={"student_id": SlotValue(value="jamie-taylor-00008", provenance="explicit")},
        )
        merged = merge_intent_frame(state, frame)
        self.assertEqual(merged.resolved_slots["student_id"], "jamie-taylor-00008")

    def test_apply_pending_answer_updates_bound_slot(self) -> None:
        state = DialogState(
            pending_question=PendingQuestion(
                slot_name="mode",
                question="Use demo or graph mode?",
                expected_answer_shape="demo|graph",
            )
        )
        updated = apply_pending_answer(state, "graph")
        self.assertEqual(updated.resolved_slots["mode"], "graph")
        self.assertIsNone(updated.pending_question)

    def test_profile_source_accepts_full_temporary_profile_option(self) -> None:
        state = DialogState(
            task="recommendation_request",
            pending_question=PendingQuestion(
                slot_name="profile_source",
                question="Should I use an existing student profile from the dataset, or build a temporary profile from your description?",
                expected_answer_shape="existing_profile|temporary_profile",
            ),
        )

        updated = apply_pending_answer(state, "build a temporary profile from your description")

        self.assertEqual(updated.resolved_slots["profile_source"], "temporary_profile")
        self.assertIsNone(updated.pending_question)

    def test_profile_source_accepts_existing_student_profile_phrase(self) -> None:
        state = DialogState(
            task="recommendation_request",
            pending_question=PendingQuestion(
                slot_name="profile_source",
                question="Should I use an existing student profile from the dataset, or build a temporary profile from your description?",
                expected_answer_shape="existing_profile|temporary_profile",
            ),
        )

        updated = apply_pending_answer(state, "use an existing student profile")

        self.assertEqual(updated.resolved_slots["profile_source"], "existing_profile")

    def test_merge_skill_frame_promotes_explicit_slots(self) -> None:
        from progrec_agent.dialog.merge import merge_skill_frame
        from progrec_agent.nlu.skill_frame import SkillAwareFrame

        frame = SkillAwareFrame(
            turn_type="domain_task",
            task="recommend_temporary_profile",
            target_types=["mentor"],
            slots={
                "research_topic": SlotValue("NLP", "explicit"),
                "profile_source": SlotValue("temporary_profile", "inferred"),
            },
            candidate_skills=["/mentor-discovery"],
            candidate_tools=["recommend_full_pipeline"],
            missing_information=["program_type"],
            confidence=0.9,
            reasoning_summary="topic supplied",
        )

        merged = merge_skill_frame(DialogState(), frame)

        self.assertEqual(merged.task, "recommend_temporary_profile")
        self.assertEqual(merged.resolved_slots["research_topic"], "NLP")
        self.assertEqual(merged.candidate_slots["profile_source"], "temporary_profile")
        self.assertEqual(merged.last_skill_plan["candidate_skills"], ["/mentor-discovery"])


if __name__ == "__main__":
    unittest.main()
