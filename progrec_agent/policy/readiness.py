from __future__ import annotations

from copy import deepcopy

from progrec_agent.dialog.slots import TASK_REQUIRED_SLOTS


def compute_readiness(state):
    updated = deepcopy(state)
    required = TASK_REQUIRED_SLOTS.get(updated.task, [])
    updated.required_slots = list(required)
    updated.missing_slots = [slot for slot in required if slot not in updated.resolved_slots]
    return updated
