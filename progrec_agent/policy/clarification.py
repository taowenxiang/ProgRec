from __future__ import annotations

from progrec_agent.dialog.state import PendingQuestion

QUESTION_BANK = {
    "profile_source": "Should I use an existing student profile from the dataset, or build a temporary profile from your description?",
    "student_id": "Which student_id from the dataset should I use?",
    "mode": "Should I use demo mode or graph mode?",
    "research_topic": "What research topic should I use for the temporary profile?",
    "program_type": "What kind of program are you targeting, such as undergraduate research or summer research?",
    "experience_level": "What is your current experience level in this topic?",
}


def choose_next_question(state):
    if state.conflicts:
        return PendingQuestion(
            slot_name="conflict_resolution",
            question="Your last two instructions conflict. Which one should I follow?",
            expected_answer_shape="free_text",
        )
    if state.task == "recommendation_request" and "profile_source" not in state.resolved_slots:
        return PendingQuestion(
            slot_name="profile_source",
            question=QUESTION_BANK["profile_source"],
            expected_answer_shape="free_text",
        )
    for slot_name in state.missing_slots:
        return PendingQuestion(
            slot_name=slot_name,
            question=QUESTION_BANK[slot_name],
            expected_answer_shape="free_text",
        )
    return None
