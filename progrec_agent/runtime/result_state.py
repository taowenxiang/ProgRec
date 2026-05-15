from __future__ import annotations

from typing import Any

from progrec_agent.contracts.result_refs import ResultReference, ResultRegistry


RESULT_REF_ARGUMENT_KEYS = (
    "student_profile_ref",
    "mentor_result_ref",
    "project_result_ref",
    "teammate_result_ref",
    "bundle_result_ref",
    "resource_validation_ref",
)

RESULT_TYPE_BY_ARGUMENT_KEY = {
    "student_profile_ref": "student_profile",
    "mentor_result_ref": "mentor_result",
    "project_result_ref": "project_result",
    "teammate_result_ref": "teammate_result",
    "bundle_result_ref": "bundle_result",
    "resource_validation_ref": "resource_validation",
}


def store_result_payload(execution_context, payload: dict[str, object]) -> str:
    result_ref = str(payload.get("result_ref") or "").strip()
    result_type = str(payload.get("result_type") or "").strip()
    if not result_ref or not result_type:
        return ""
    execution_context.latest_result_refs[result_type] = result_ref
    execution_context.active_result_ref = result_ref
    execution_context.result_ref_payloads[result_ref] = dict(payload)
    execution_context.result_handle = result_ref
    execution_context.last_result = dict(payload)
    return result_ref


def latest_result_ref(execution_context, result_type: str) -> str:
    return str(execution_context.latest_result_refs.get(result_type) or "")


def latest_result_payload(execution_context, result_type: str) -> dict[str, object]:
    result_ref = latest_result_ref(execution_context, result_type)
    if not result_ref:
        raise KeyError(f"No latest result is available for result_type {result_type!r}")
    return resolve_result_payload(execution_context, result_ref)


def active_result_payload(execution_context) -> dict[str, object]:
    active_ref = str(execution_context.active_result_ref or "").strip()
    if not active_ref:
        raise KeyError("No active result is available in execution context")
    return resolve_result_payload(execution_context, active_ref)


def resolve_result_payload(execution_context, result_ref: str) -> dict[str, object]:
    if result_ref not in execution_context.result_ref_payloads:
        raise KeyError(f"Unknown result_ref {result_ref!r}")
    return dict(execution_context.result_ref_payloads[result_ref])


def result_registry_from_execution_context(execution_context) -> ResultRegistry:
    registry = ResultRegistry()
    for result_ref, payload in dict(execution_context.result_ref_payloads or {}).items():
        result_type = str(payload.get("result_type") or "").strip()
        if not result_type:
            continue
        registry.store(
            ResultReference(
                result_ref=result_ref,
                result_type=result_type,
                owner_skill=str(payload.get("owner_skill") or ""),
                session_id=str(payload.get("session_id") or ""),
                input_refs=list(payload.get("input_refs") or []),
                summary=dict(payload.get("summary") or {}),
                followups=list(payload.get("followups") or []),
                payload=dict(payload.get("payload") or {}),
            )
        )
    return registry


def hydrate_result_arguments(execution_context, arguments: dict[str, object]) -> dict[str, object]:
    hydrated = dict(arguments)
    for ref_key in RESULT_REF_ARGUMENT_KEYS:
        ref_value = hydrated.get(ref_key)
        if isinstance(ref_value, str) and ref_value in execution_context.result_ref_payloads:
            hydrated[ref_key] = resolve_result_payload(execution_context, ref_value)
            continue
        if ref_key not in hydrated:
            result_type = RESULT_TYPE_BY_ARGUMENT_KEY[ref_key]
            latest_ref = latest_result_ref(execution_context, result_type)
            if latest_ref:
                hydrated[ref_key] = resolve_result_payload(execution_context, latest_ref)
    return hydrated


def record_shown_entity(execution_context, entity_type: str, entity_id: str) -> None:
    normalized_type = str(entity_type or "").strip()
    normalized_id = str(entity_id or "").strip()
    if normalized_type and normalized_id:
        execution_context.last_shown_entities[normalized_type] = normalized_id


def result_state_snapshot(execution_context) -> dict[str, object]:
    return {
        "last_result_handle": execution_context.result_handle,
        "latest_result_refs": dict(execution_context.latest_result_refs),
        "active_result_ref": execution_context.active_result_ref,
        "last_shown_entities": dict(execution_context.last_shown_entities),
    }


def result_handle_from_payload(
    *,
    structured_payload: dict[str, object] | None,
    dialog_state_payload: dict[str, object] | None,
) -> str:
    structured = dict(structured_payload or {})
    if structured.get("last_result_handle"):
        return str(structured.get("last_result_handle") or "")
    dialog_state = dict(dialog_state_payload or {})
    execution_context = dict(dialog_state.get("execution_context") or {})
    return str(execution_context.get("result_handle") or "")
