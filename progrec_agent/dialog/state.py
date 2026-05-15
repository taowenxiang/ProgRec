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
    last_result: dict[str, object] = field(default_factory=dict)
    last_turn_type: str = ""
    next_question: str = ""
    latest_result_refs: dict[str, str] = field(default_factory=dict)
    active_result_ref: str = ""
    last_shown_entities: dict[str, str] = field(default_factory=dict)
    result_ref_payloads: dict[str, dict[str, object]] = field(default_factory=dict)


@dataclass
class DialogState:
    task: str = ""
    goal: str = ""
    active_goal: str = ""
    goal_targets: list[str] = field(default_factory=list)
    profile_context: dict[str, object] = field(default_factory=dict)
    planner_actions: list[dict[str, object]] = field(default_factory=list)
    suggested_next_actions: list[dict[str, object]] = field(default_factory=list)
    tool_results_summary: dict[str, object] = field(default_factory=dict)
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
    skill_trace: list[dict[str, object]] = field(default_factory=list)
    last_skill_plan: dict[str, object] = field(default_factory=dict)
    last_result_summary: str = ""
