from __future__ import annotations

import re

from progrec_agent.nlu.domain_guard import extract_research_topic

_SKILL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("python", "python"),
    ("pytorch", "pytorch"),
    ("tensorflow", "tensorflow"),
    ("nlp", "nlp"),
    ("natural language processing", "nlp"),
    ("machine learning", "machine learning"),
    ("llm", "llm"),
    ("computer vision", "computer vision"),
    ("data analysis", "data analysis"),
)


def infer_program_type(user_text: str) -> str:
    text = user_text.strip().lower()
    if re.search(r"\b(ug|undergrad|undergraduate)\b", text):
        return "undergraduate"
    if re.search(r"\b(pg|postgrad|postgraduate|graduate|masters?|phd|doctor(?:al)?)\b", text):
        return "graduate"
    return ""


def infer_experience_level(user_text: str) -> str:
    text = user_text.strip().lower()
    if re.search(r"\b(beginner|new|novice|introductory)\b", text):
        return "beginner"
    if re.search(r"\b(intermediate|some experience|moderate)\b", text):
        return "intermediate"
    if re.search(r"\b(advanced|experienced|expert|strong)\b", text):
        return "advanced"
    return ""


def infer_skills(user_text: str) -> list[str]:
    normalized = f" {user_text.strip().lower()} "
    discovered: list[str] = []
    for needle, label in _SKILL_PATTERNS:
        if f" {needle} " in normalized and label not in discovered:
            discovered.append(label)
    return discovered


def profile_context_from_text(user_text: str) -> dict[str, object]:
    profile_context: dict[str, object] = {
        "raw_profile_text": user_text,
        "profile_details": user_text,
    }
    program_type = infer_program_type(user_text)
    if program_type:
        profile_context["program_type"] = program_type
    experience_level = infer_experience_level(user_text)
    if experience_level:
        profile_context["experience_level"] = experience_level
    research_topic = extract_research_topic(user_text)
    if research_topic:
        profile_context["research_topic"] = research_topic
    skills = infer_skills(user_text)
    if skills:
        profile_context["skills"] = skills
    return profile_context
