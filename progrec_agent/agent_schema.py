from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

IntentName = Literal[
    "recommend_mentor",
    "recommend_project",
    "recommend_teammate",
    "inspect_current_mentor",
    "explain_recommendation",
    "show_current_profile",
    "inspect_artifacts",
    "debug_graph_mode",
    "rebuild_graph",
    "ask_last_action",
    "ask_capabilities",
]
MessageType = Literal["domain_task", "meta_question", "startup_help"]
RiskLevel = Literal["safe", "confirm", "restricted"]


@dataclass
class ClarificationQuestion:
    key: str
    question: str


@dataclass
class AgentProfile:
    goal: str
    research_direction: list[str] = field(default_factory=list)
    desired_outcomes: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, Any] = field(
        default_factory=lambda: {
            "prefer_diversity": False,
            "prefer_low_commitment": False,
            "prefer_fast_onboarding": False,
            "collaboration_focus": "balanced",
        }
    )
    confidence: float = 0.0


@dataclass
class ExecutionPlan:
    need_clarification: bool = False
    clarification_questions: list[ClarificationQuestion] = field(default_factory=list)
    run_skill3: bool = False
    run_skill4: bool = False
    run_skill5: bool = False
    rerun_needed: bool = False
    stop_reason: str = ""


@dataclass
class PendingConfirmation:
    action_id: str
    tool_name: str
    arguments: dict[str, Any]
    prompt: str


@dataclass
class RouterDecision:
    message_type: MessageType
    intent: IntentName
    confidence: float
    candidate_tools: list[str]
    needs_clarification: bool = False
    clarification_question: str = ""
    answer_only: bool = False
    tool_name: str = ""
    tool_arguments: dict[str, Any] = field(default_factory=dict)
    meta_reply: str = ""
    reasoning_summary: str = ""


@dataclass
class ToolExecutionResult:
    tool_name: str
    ok: bool
    payload: dict[str, Any] = field(default_factory=dict)
    error: str = ""
