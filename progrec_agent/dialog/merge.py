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
