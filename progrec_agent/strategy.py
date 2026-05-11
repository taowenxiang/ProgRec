from __future__ import annotations


def build_strategy(agent_profile: dict[str, object]) -> dict[str, object]:
    constraints = dict(agent_profile.get("constraints") or {})
    preferences = dict(agent_profile.get("preferences") or {})
    time_budget = int(constraints.get("time_budget_hours_per_week") or 0)
    return {
        "top_k": 5,
        "prefer_diversity": bool(preferences.get("prefer_diversity")),
        "prefer_low_commitment": bool(preferences.get("prefer_low_commitment") or (0 < time_budget <= 4)),
        "prefer_fast_onboarding": bool(preferences.get("prefer_fast_onboarding") or (0 < time_budget <= 4)),
        "exclude_topics": [str(item) for item in constraints.get("exclude_topics", [])],
        "max_reruns": 2,
    }
