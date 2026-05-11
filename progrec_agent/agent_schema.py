from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

IntentName = Literal["recommend", "explain", "inspect", "debug", "rebuild", "help", "chat"]
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
    intent: IntentName
    confidence: float
    candidate_tools: list[str]
    needs_clarification: bool = False
    clarification_question: str = ""
    reasoning_summary: str = ""


@dataclass
class ToolExecutionResult:
    tool_name: str
    ok: bool
    payload: dict[str, Any] = field(default_factory=dict)
    error: str = ""
