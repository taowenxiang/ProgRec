from __future__ import annotations


def render_clarification(question) -> str:
    return question.question


def render_execution_blocker(state) -> str:
    return f"I still need {', '.join(state.missing_slots)} before I can run this request."


def render_recommendation_summary(result: dict[str, object]) -> str:
    recs = dict((result.get("skill5_result") or {}).get("recommendations") or {})
    return (
        "I ran the recommendation pipeline and generated recommendations. "
        f"Mentors: {len(list(recs.get('mentors') or []))}, "
        f"Projects: {len(list(recs.get('projects') or []))}, "
        f"Teammates: {len(list(recs.get('teammates') or []))}."
    )
