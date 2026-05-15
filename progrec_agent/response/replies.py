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


def render_ranked_entity(entity_type: str, rank: int, entity: dict[str, object]) -> str:
    if not entity:
        return f"I could not find a ranked {entity_type} at rank {rank} in the latest recommendation result."

    title = (
        entity.get(f"{entity_type}_name")
        or entity.get("name")
        or entity.get("title")
        or entity.get(f"{entity_type}_id")
        or entity.get("id")
        or f"rank {rank} {entity_type}"
    )
    score = entity.get("final_score") or entity.get("score") or entity.get("fit_score")
    score_text = f" Score: {score}." if score is not None else ""
    reason_values = entity.get("reasons") or entity.get("reason") or entity.get("explanation")
    if isinstance(reason_values, list):
        reason_text = " ".join(str(item) for item in reason_values[:3])
    else:
        reason_text = str(reason_values or "")
    reason_suffix = f" {reason_text}" if reason_text else ""
    return f"{entity_type.title()} profile: {title}.{score_text}{reason_suffix}"


def render_meta_answer(state) -> str:
    trace = list(state.skill_trace or [])
    if not trace:
        return "I have not run any ProgRec skills in this chat yet."
    summaries = [f"{entry.get('skill_id')}: {entry.get('summary')}" for entry in trace]
    return "I used these ProgRec skills: " + " ".join(summaries)
