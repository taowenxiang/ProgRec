from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from progrec_agent.nlu.schema import SlotValue
from progrec_agent.skill_catalog import SkillCatalog


ALLOWED_TURN_TYPES = {
    "domain_task",
    "clarification_answer",
    "inspect_previous_result",
    "resource_validation",
    "meta_question",
    "out_of_scope",
}
ALLOWED_TASKS = {
    "recommend_existing_student",
    "recommend_temporary_profile",
    "inspect_recommendation",
    "explain_recommendation",
    "validate_resources",
    "answer_meta_question",
    "out_of_scope",
}
ALLOWED_PROVENANCE = {"explicit", "inferred", "unknown"}
ALLOWED_MODES = {"demo", "graph"}


@dataclass(frozen=True)
class SkillAwareFrame:
    turn_type: str
    task: str
    target_types: list[str] = field(default_factory=list)
    slots: dict[str, SlotValue] = field(default_factory=dict)
    candidate_skills: list[str] = field(default_factory=list)
    candidate_tools: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning_summary: str = ""
    validation_errors: list[str] = field(default_factory=list)


def _coerce_slot_value(raw: Any) -> SlotValue:
    row = dict(raw or {})
    provenance = str(row.get("provenance") or "unknown")
    if provenance not in ALLOWED_PROVENANCE:
        provenance = "unknown"
    return SlotValue(value=row.get("value"), provenance=provenance)


def safe_out_of_scope(errors: list[str], *, reasoning_summary: str = "") -> SkillAwareFrame:
    return SkillAwareFrame(
        turn_type="out_of_scope",
        task="out_of_scope",
        confidence=0.0,
        reasoning_summary=reasoning_summary,
        validation_errors=errors,
    )


def validate_skill_frame_payload(payload: dict[str, object], catalog: SkillCatalog) -> SkillAwareFrame:
    errors: list[str] = []
    turn_type = str(payload.get("turn_type") or "")
    task = str(payload.get("task") or "")
    if turn_type not in ALLOWED_TURN_TYPES:
        errors.append(f"invalid_turn_type:{turn_type}")
    if task not in ALLOWED_TASKS:
        errors.append(f"invalid_task:{task}")

    slots = {
        str(key): _coerce_slot_value(value)
        for key, value in dict(payload.get("slots") or {}).items()
    }
    mode = slots.get("mode")
    if mode is not None and str(mode.value).strip().lower() not in ALLOWED_MODES:
        errors.append(f"invalid_mode:{mode.value}")

    candidate_skills = [str(item) for item in list(payload.get("candidate_skills") or [])]
    candidate_tools = [str(item) for item in list(payload.get("candidate_tools") or [])]
    for skill_id in candidate_skills:
        if skill_id not in catalog.allowed_skill_ids:
            errors.append(f"unknown_skill:{skill_id}")
    for tool_name in candidate_tools:
        if tool_name not in catalog.allowed_tool_names:
            errors.append(f"unknown_tool:{tool_name}")

    reasoning_summary = str(payload.get("reasoning_summary") or "")
    if errors:
        return safe_out_of_scope(errors, reasoning_summary=reasoning_summary)

    return SkillAwareFrame(
        turn_type=turn_type,
        task=task,
        target_types=[str(item) for item in list(payload.get("target_types") or [])],
        slots=slots,
        candidate_skills=candidate_skills,
        candidate_tools=candidate_tools,
        missing_information=[str(item) for item in list(payload.get("missing_information") or [])],
        confidence=float(payload.get("confidence") or 0.0),
        reasoning_summary=reasoning_summary,
        validation_errors=[],
    )
