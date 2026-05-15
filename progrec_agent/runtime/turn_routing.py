from __future__ import annotations

from progrec_agent.target_policy import TARGET_KEYWORDS, infer_user_targets


_AFFIRMATIVE_PHRASES = (
    "yes",
    "yeah",
    "yep",
    "sure",
    "please do",
    "go ahead",
    "sounds good",
    "do that",
    "that works",
    "okay",
    "ok",
)

_MULTI_TARGET_PHRASES = (
    "both",
    "all of them",
    "all three",
    "everything",
)


def detect_explicit_targets(user_text: str) -> list[str]:
    text = user_text.lower()
    return [
        target
        for target, keywords in TARGET_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]


def resolve_turn_targets(state, user_text: str) -> list[str]:
    explicit_targets = detect_explicit_targets(user_text)
    if explicit_targets:
        return explicit_targets

    suggestion_targets = _suggestion_targets(state)
    if suggestion_targets and is_affirmative_followup(user_text):
        if _requests_multiple_suggestions(user_text):
            return suggestion_targets
        return [suggestion_targets[0]]

    if state.goal_targets:
        return list(state.goal_targets)
    return infer_user_targets(user_text)


def apply_turn_routing(state, user_text: str) -> None:
    resolved_targets = resolve_turn_targets(state, user_text)
    if resolved_targets:
        state.goal_targets = list(resolved_targets)
        state.active_goal = resolved_targets[0]
    _sync_suggestion_acceptance(state, resolved_targets)


def is_affirmative_followup(user_text: str) -> bool:
    text = " ".join(str(user_text or "").lower().split())
    return any(phrase in text for phrase in _AFFIRMATIVE_PHRASES)


def _requests_multiple_suggestions(user_text: str) -> bool:
    text = " ".join(str(user_text or "").lower().split())
    return any(phrase in text for phrase in _MULTI_TARGET_PHRASES)


def _suggestion_targets(state) -> list[str]:
    targets: list[str] = []
    for item in list(state.suggested_next_actions or []):
        if not isinstance(item, dict):
            continue
        target = str(item.get("target") or "").strip()
        if target:
            targets.append(target)
    return targets


def _sync_suggestion_acceptance(state, resolved_targets: list[str]) -> None:
    if not state.suggested_next_actions:
        return
    accepted_targets = set(resolved_targets)
    for item in list(state.suggested_next_actions):
        if not isinstance(item, dict):
            continue
        target = str(item.get("target") or "").strip()
        if target:
            item["accepted"] = target in accepted_targets
