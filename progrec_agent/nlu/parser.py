from __future__ import annotations

from progrec_agent.nlu.domain_guard import (
    build_domain_fallback_frame,
    looks_like_domain_request,
    should_override_frame,
)
from progrec_agent.nlu.schema import IntentFrame
from progrec_agent.nlu.skill_frame import SkillAwareFrame, safe_out_of_scope, validate_skill_frame_payload
from progrec_agent.nlu.validators import build_safe_fallback_frame, validate_parse_payload
from progrec_agent.skill_catalog import SkillCatalog

SEMANTIC_PARSE_PROMPT = """
You are the bounded NLU layer for ProgRec, an academic recommendation assistant.
Return strict JSON describing the user's request.
Do not choose tools.
Do not ask clarification questions.
Do not invent facts.
Classify requests about mentors, advisors, projects, teammates, student fit, research topics, ranking, or ProgRec resources as in scope.
Use intent "recommendation_request" when the user wants mentor, project, or teammate recommendations.
Use intent "out_of_scope" only when the request is unrelated to ProgRec recommendations.
Use these top-level JSON keys exactly: intent, target_types, entities, constraints, preferences, references, confidence, uncertain_fields, possible_conflicts.
Each slot map value must be an object with "value" and "provenance" where provenance is explicit, inferred, or unknown.
""".strip()

SKILL_AWARE_PARSE_PROMPT = """
You are the skill-aware NLU layer for ProgRec, a bounded academic recommendation assistant.
Use the skill catalog to classify the user turn and propose candidate skills/tools.
Return strict JSON with keys:
turn_type, task, target_types, slots, candidate_skills, candidate_tools, missing_information, confidence, reasoning_summary.
Do not execute tools.
Do not invent student ids.
Use task "recommend_temporary_profile" when the user wants recommendations from a described profile.
Use task "recommend_existing_student" only when a dataset student_id is explicit or the user chooses an existing profile.
Use task "inspect_recommendation" or "explain_recommendation" for follow-ups about previous ranked results.
Use task "validate_resources" for graph/demo resource checks.
Use task "answer_meta_question" for questions about what skills or tools were used.
Use task "out_of_scope" only when the request is unrelated to ProgRec recommendations.
Only propose candidate_skills and candidate_tools that appear in the skill catalog.
Each slot value must be an object with "value" and "provenance".
""".strip()


def parse_user_message(user_text: str, *, dialog_state, llm_client):
    if llm_client is None:
        if looks_like_domain_request(user_text):
            return build_domain_fallback_frame(user_text, reason="missing_llm_domain_fallback")
        return build_safe_fallback_frame("missing_llm")
    try:
        payload = llm_client.complete_json(
            f"{SEMANTIC_PARSE_PROMPT}\nDialog state: {dialog_state}\nUser message: {user_text}"
        )
        frame = validate_parse_payload(dict(payload))
    except Exception:
        if looks_like_domain_request(user_text):
            return build_domain_fallback_frame(user_text, reason="llm_parse_error_domain_fallback")
        return build_safe_fallback_frame("llm_parse_error")
    if should_override_frame(frame, user_text):
        return build_domain_fallback_frame(user_text, reason="llm_domain_override")
    return frame


def _frame_from_legacy_intent(frame: IntentFrame) -> SkillAwareFrame:
    slots = {**frame.entities, **frame.constraints, **frame.preferences, **frame.references}
    task = frame.intent
    candidate_skills: list[str] = []
    candidate_tools: list[str] = []
    if frame.intent == "recommendation_request":
        task = "recommendation_request"
        profile_source = slots.get("profile_source")
        if profile_source is not None and str(profile_source.value) == "existing_profile":
            task = "recommend_existing_student"
        elif profile_source is not None and str(profile_source.value) == "temporary_profile":
            task = "recommend_temporary_profile"
        if "student_id" in slots:
            task = "recommend_existing_student"
        if any(slot in slots for slot in ("research_topic", "topic", "research_area", "area", "field")):
            task = "recommend_temporary_profile"
        candidate_skills = ["/student-profiling", "/mentor-discovery", "/social-ranking"]
        candidate_tools = ["recommend_full_pipeline"]
    elif frame.intent == "inspect_recommendation":
        task = "inspect_recommendation"
    elif frame.intent == "explain_recommendation":
        task = "explain_recommendation"
    elif frame.intent == "validate_resources":
        task = "validate_resources"
    else:
        task = "out_of_scope"
    return SkillAwareFrame(
        turn_type="domain_task" if task != "out_of_scope" else "out_of_scope",
        task=task,
        target_types=list(frame.target_types),
        slots=slots,
        candidate_skills=candidate_skills,
        candidate_tools=candidate_tools,
        missing_information=list(frame.uncertain_fields),
        confidence=frame.confidence,
        reasoning_summary="Converted legacy intent frame.",
        validation_errors=list(frame.possible_conflicts),
    )


def _domain_fallback_skill_frame(user_text: str, *, reason: str) -> SkillAwareFrame:
    fallback = build_domain_fallback_frame(user_text, reason=reason)
    if fallback.intent != "recommendation_request":
        return safe_out_of_scope([reason], reasoning_summary="Local domain fallback.")
    return _frame_from_legacy_intent(fallback)


def parse_skill_aware_user_message(
    user_text: str,
    *,
    dialog_state,
    llm_client,
    skill_catalog: SkillCatalog,
) -> SkillAwareFrame:
    if llm_client is None:
        if looks_like_domain_request(user_text):
            return _domain_fallback_skill_frame(user_text, reason="missing_llm_skill_fallback")
        return safe_out_of_scope(["missing_llm"], reasoning_summary="No LLM client configured.")
    try:
        payload = llm_client.complete_json(
            f"{SKILL_AWARE_PARSE_PROMPT}\n"
            f"Skill catalog:\n{skill_catalog.to_prompt_context()}\n"
            f"Dialog state: {dialog_state}\n"
            f"User message: {user_text}"
        )
        payload_dict = dict(payload)
        if "turn_type" not in payload_dict and "intent" in payload_dict:
            legacy = validate_parse_payload(payload_dict)
            if should_override_frame(legacy, user_text):
                return _domain_fallback_skill_frame(user_text, reason="llm_domain_override")
            return _frame_from_legacy_intent(legacy)
        frame = validate_skill_frame_payload(payload_dict, skill_catalog)
    except Exception:
        if looks_like_domain_request(user_text):
            return _domain_fallback_skill_frame(user_text, reason="llm_parse_error_skill_fallback")
        return safe_out_of_scope(["llm_parse_error"], reasoning_summary="LLM parse failure.")
    if frame.task == "out_of_scope" and looks_like_domain_request(user_text):
        return _domain_fallback_skill_frame(user_text, reason="llm_skill_domain_override")
    return frame
