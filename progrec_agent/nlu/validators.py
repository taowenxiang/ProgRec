from __future__ import annotations

from typing import Any

from progrec_agent.nlu.schema import IntentFrame, SlotValue

ALLOWED_INTENTS = {
    "recommendation_request",
    "inspect_recommendation",
    "explain_recommendation",
    "validate_resources",
}
ALLOWED_MODES = {"demo", "graph"}
ALLOWED_PROVENANCE = {"explicit", "inferred", "unknown"}


def build_safe_fallback_frame(reason: str, *, uncertain_fields: list[str] | None = None) -> IntentFrame:
    return IntentFrame(
        intent="recommendation_request",
        target_types=["mentor"],
        confidence=0.0,
        uncertain_fields=list(uncertain_fields or ["profile_source"]),
        possible_conflicts=[reason],
    )


def _coerce_slot_map(raw_mapping: dict[str, Any]) -> dict[str, SlotValue]:
    items: dict[str, SlotValue] = {}
    for key, item in raw_mapping.items():
        row = dict(item or {})
        provenance = str(row.get("provenance") or "unknown")
        if provenance not in ALLOWED_PROVENANCE:
            provenance = "unknown"
        items[str(key)] = SlotValue(value=row.get("value"), provenance=provenance)
    return items


def validate_parse_payload(payload: dict[str, object]) -> IntentFrame:
    intent = str(payload.get("intent") or "")
    if intent not in ALLOWED_INTENTS:
        return build_safe_fallback_frame("invalid_intent")

    entities = _coerce_slot_map(dict(payload.get("entities") or {}))
    constraints = _coerce_slot_map(dict(payload.get("constraints") or {}))
    preferences = _coerce_slot_map(dict(payload.get("preferences") or {}))
    references = _coerce_slot_map(dict(payload.get("references") or {}))

    for source in (entities, constraints, preferences, references):
        mode = source.get("mode")
        if mode is not None and str(mode.value) not in ALLOWED_MODES:
            return build_safe_fallback_frame("invalid_mode", uncertain_fields=["mode"])

    return IntentFrame(
        intent=intent,
        target_types=[str(x) for x in list(payload.get("target_types") or [])],
        entities=entities,
        constraints=constraints,
        preferences=preferences,
        references=references,
        confidence=float(payload.get("confidence", 0.0)),
        uncertain_fields=[str(x) for x in list(payload.get("uncertain_fields") or [])],
        possible_conflicts=[str(x) for x in list(payload.get("possible_conflicts") or [])],
    )
