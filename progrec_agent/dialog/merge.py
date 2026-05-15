from __future__ import annotations

from copy import deepcopy

from progrec_agent.dialog.state import DialogState


def merge_intent_frame(state: DialogState, frame) -> DialogState:
    updated = deepcopy(state)
    updated.task = updated.task or frame.intent
    for key, slot in frame.entities.items():
        if getattr(slot, "provenance", "unknown") == "explicit":
            updated.resolved_slots[key] = slot.value
        elif key not in updated.resolved_slots:
            updated.candidate_slots[key] = slot.value
    for key, slot in frame.constraints.items():
        if getattr(slot, "provenance", "unknown") == "explicit":
            updated.resolved_slots[key] = slot.value
        elif key not in updated.resolved_slots:
            updated.candidate_slots[key] = slot.value
    for key, slot in frame.preferences.items():
        if getattr(slot, "provenance", "unknown") == "explicit":
            updated.resolved_slots[key] = slot.value
        elif key not in updated.resolved_slots:
            updated.candidate_slots[key] = slot.value
    for key, slot in frame.references.items():
        if getattr(slot, "provenance", "unknown") == "explicit":
            updated.resolved_slots[key] = slot.value
        elif key not in updated.resolved_slots:
            updated.candidate_slots[key] = slot.value
    return updated


def merge_skill_frame(state: DialogState, frame) -> DialogState:
    updated = deepcopy(state)
    if frame.task and frame.task != "out_of_scope":
        updated.task = frame.task
    elif frame.task == "out_of_scope":
        updated.task = "out_of_scope"
    for key, slot in frame.slots.items():
        if getattr(slot, "provenance", "unknown") == "explicit":
            updated.resolved_slots[key] = slot.value
        elif key not in updated.resolved_slots:
            updated.candidate_slots[key] = slot.value
    updated.last_skill_plan = {
        "turn_type": frame.turn_type,
        "task": frame.task,
        "target_types": list(frame.target_types),
        "candidate_skills": list(frame.candidate_skills),
        "candidate_tools": list(frame.candidate_tools),
        "missing_information": list(frame.missing_information),
        "confidence": frame.confidence,
        "reasoning_summary": frame.reasoning_summary,
        "validation_errors": list(frame.validation_errors),
    }
    return updated
