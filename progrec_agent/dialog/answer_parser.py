from __future__ import annotations

from copy import deepcopy

from progrec_agent.dialog.state import DialogState

ANSWER_MAP = {
    "use my description": {"profile_source": "temporary_profile"},
    "build a temporary profile": {"profile_source": "temporary_profile"},
    "temporary": {"profile_source": "temporary_profile"},
    "existing": {"profile_source": "existing_profile"},
    "graph": {"mode": "graph"},
    "demo": {"mode": "demo"},
}


def apply_pending_answer(state: DialogState, user_text: str) -> DialogState:
    updated = deepcopy(state)
    pending = updated.pending_question
    if pending is None:
        return updated
    normalized = user_text.strip().lower()
    if normalized in ANSWER_MAP and pending.slot_name in ANSWER_MAP[normalized]:
        updated.resolved_slots[pending.slot_name] = ANSWER_MAP[normalized][pending.slot_name]
    else:
        updated.resolved_slots[pending.slot_name] = user_text.strip()
    updated.pending_question = None
    updated.clarification_turn_count += 1
    updated.last_user_turn = user_text
    return updated
