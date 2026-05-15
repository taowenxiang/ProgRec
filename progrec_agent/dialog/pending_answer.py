from __future__ import annotations

import re

from progrec_agent.dialog.state import PendingQuestion
from progrec_agent.nlu.schema import SlotValue


def _normalized(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _parse_profile_source(text: str) -> str:
    if _contains_any(
        text,
        (
            "temporary",
            "my description",
            "your description",
            "from my description",
            "build one",
            "build a profile",
            "create a profile",
            "use what i tell",
        ),
    ):
        return "temporary_profile"
    if _contains_any(text, ("existing", "dataset", "student id", "student_id", "saved profile")):
        return "existing_profile"
    return ""


def _parse_mode(text: str) -> str:
    if re.search(r"\b(graph|real graph|full graph)\b", text):
        return "graph"
    if re.search(r"\b(demo|sample)\b", text):
        return "demo"
    return ""


def _parse_experience_level(text: str) -> str:
    if re.search(r"\b(beginner|new|novice|introductory)\b", text):
        return "beginner"
    if re.search(r"\b(intermediate|some experience|moderate)\b", text):
        return "intermediate"
    if re.search(r"\b(advanced|experienced|expert|strong)\b", text):
        return "advanced"
    return ""


def parse_pending_answer(question: PendingQuestion, user_text: str) -> SlotValue:
    raw = user_text.strip()
    text = _normalized(user_text)
    slot_name = question.slot_name

    if slot_name == "profile_source":
        value = _parse_profile_source(text)
        return SlotValue(value=value or raw, provenance="explicit")
    if slot_name == "mode":
        value = _parse_mode(text)
        return SlotValue(value=value or raw, provenance="explicit")
    if slot_name == "experience_level":
        value = _parse_experience_level(text)
        return SlotValue(value=value or raw, provenance="explicit")
    return SlotValue(value=raw, provenance="explicit")
