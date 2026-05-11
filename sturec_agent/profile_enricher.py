from __future__ import annotations

from sturec_agent.agent_schema import AgentProfile
from sturec_agent.adapters.skill1_adapter import normalize_manual_profile
from sturec_agent.prompts import INTENT_UNDERSTANDING_PROMPT


def build_profiles_from_text(user_text: str, llm_client) -> tuple[dict[str, object], AgentProfile]:
    payload = llm_client.complete_json(f"{INTENT_UNDERSTANDING_PROMPT}\nUser request: {user_text}")
    raw_skill = payload.get("skill_profile") or {}
    skill_profile = normalize_manual_profile(
        {
            "grade": str(raw_skill.get("grade", "")),
            "major": str(raw_skill.get("major", "")),
            "skills": ", ".join(str(item) for item in raw_skill.get("skills", [])),
            "interests": ", ".join(str(item) for item in raw_skill.get("interests", [])),
            "experience_summary": str(raw_skill.get("experience_summary", "")),
            "availability": str(raw_skill.get("availability", "moderate")),
            "resume_text": user_text,
        }
    )
    agent_profile = AgentProfile(
        goal=str(payload.get("goal", user_text)),
        research_direction=[str(item) for item in payload.get("research_direction", [])],
        desired_outcomes=[str(item) for item in payload.get("desired_outcomes", [])],
        constraints=dict(payload.get("constraints") or {}),
        preferences=dict(payload.get("preferences") or {}),
        confidence=float(payload.get("confidence", 0.0)),
    )
    return skill_profile, agent_profile
