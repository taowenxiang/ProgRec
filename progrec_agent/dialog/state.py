from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PendingQuestion:
    slot_name: str
    question: str
    expected_answer_shape: str


@dataclass
class ExecutionContext:
    result_handle: str | None = None
    selected_entity_type: str | None = None
    selected_entity_id: str | None = None


@dataclass
class DialogState:
    task: str = ""
    goal: str = ""
    resolved_slots: dict[str, object] = field(default_factory=dict)
    candidate_slots: dict[str, object] = field(default_factory=dict)
    required_slots: list[str] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    pending_question: PendingQuestion | None = None
    conflicts: list[str] = field(default_factory=list)
    execution_context: ExecutionContext = field(default_factory=ExecutionContext)
    clarification_turn_count: int = 0
    last_user_turn: str = ""
    last_agent_turn: str = ""
