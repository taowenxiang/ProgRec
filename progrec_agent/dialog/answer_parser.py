from __future__ import annotations

from copy import deepcopy

from progrec_agent.dialog.pending_answer import parse_pending_answer
from progrec_agent.dialog.state import DialogState


def apply_pending_answer(state: DialogState, user_text: str) -> DialogState:
    updated = deepcopy(state)
    pending = updated.pending_question
    if pending is None:
        return updated
    slot = parse_pending_answer(pending, user_text)
    updated.resolved_slots[pending.slot_name] = slot.value
    updated.pending_question = None
    updated.clarification_turn_count += 1
    updated.last_user_turn = user_text
    return updated
