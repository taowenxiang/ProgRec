from __future__ import annotations

import re

from progrec_agent.nlu.schema import IntentFrame, SlotValue

RECOMMENDATION_TERMS = {
    "advisor",
    "adviser",
    "match",
    "mentor",
    "mentors",
    "project",
    "projects",
    "recommend",
    "recommendation",
    "recommendations",
    "teammate",
    "teammates",
}

RESEARCH_TERMS = {
    "ai",
    "graph neural network",
    "graph neural networks",
    "machine learning",
    "ml",
    "nlp",
    "research",
    "trustworthy ai",
}

TOPIC_PATTERNS = (
    re.compile(r"\b(?:mentor|mentors|advisor|adviser)\s+for\s+(?P<topic>.+)$", re.IGNORECASE),
    re.compile(r"\b(?:project|projects|teammate|teammates)\s+(?:about|for|in)\s+(?P<topic>.+)$", re.IGNORECASE),
    re.compile(r"\b(?:interested in|working on|focus(?:ed)? on|about|for|in)\s+(?P<topic>.+)$", re.IGNORECASE),
)


def looks_like_domain_request(user_text: str) -> bool:
    normalized = user_text.lower()
    return any(term in normalized for term in RECOMMENDATION_TERMS) or any(
        term in normalized for term in RESEARCH_TERMS
    )


def extract_research_topic(user_text: str) -> str:
    normalized = " ".join(user_text.strip().split())
    for pattern in TOPIC_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return _clean_topic(match.group("topic"))
    return ""


def build_domain_fallback_frame(user_text: str, *, reason: str = "domain_fallback") -> IntentFrame:
    target_types = _target_types(user_text)
    topic = extract_research_topic(user_text)
    entities: dict[str, SlotValue] = {}
    constraints: dict[str, SlotValue] = {}
    if topic:
        entities["profile_source"] = SlotValue(value="temporary_profile", provenance="inferred")
        constraints["research_topic"] = SlotValue(value=topic, provenance="explicit")
    return IntentFrame(
        intent="recommendation_request",
        target_types=target_types,
        entities=entities,
        constraints=constraints,
        confidence=0.65 if topic else 0.55,
        uncertain_fields=[] if topic else ["profile_source"],
        possible_conflicts=[reason],
    )


def should_override_frame(frame: IntentFrame, user_text: str) -> bool:
    if not looks_like_domain_request(user_text):
        return False
    return frame.intent == "recommendation_request" and frame.confidence < 0.35


def _target_types(user_text: str) -> list[str]:
    normalized = user_text.lower()
    target_types: list[str] = []
    if "mentor" in normalized or "advisor" in normalized or "adviser" in normalized:
        target_types.append("mentor")
    if "project" in normalized:
        target_types.append("project")
    if "teammate" in normalized or "team mate" in normalized:
        target_types.append("teammate")
    return target_types or ["mentor"]


def _clean_topic(value: str) -> str:
    topic = value.strip().strip(" .?!,;:")
    topic = re.sub(r"^(?:a|an|the)\s+", "", topic, flags=re.IGNORECASE)
    topic = re.sub(r"\s+(?:mentor|mentors|advisor|adviser|project|projects|teammate|teammates)$", "", topic, flags=re.IGNORECASE)
    return topic.strip()
