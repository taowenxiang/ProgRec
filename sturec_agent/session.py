from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sturec_agent.models import ConversationTurn, JsonDict, Mode


@dataclass
class AgentSession:
    temp_dir: Path
    mode: Mode | None = None
    student_profile: JsonDict | None = None
    resource_context: JsonDict | None = None
    skill3_result: JsonDict | None = None
    skill4_result: JsonDict | None = None
    skill5_result: JsonDict | None = None
    temporary_paths: list[Path] = field(default_factory=list)
    conversation_history: list[ConversationTurn] = field(default_factory=list)
    agent_profile: JsonDict | None = None
    latest_plan: JsonDict | None = None
    active_strategy: JsonDict | None = None
    decision_trace: list[str] = field(default_factory=list)
    rerun_count: int = 0
    pending_clarification_questions: list[JsonDict] = field(default_factory=list)
    pending_goal_text: str = ""

    @property
    def has_results(self) -> bool:
        return self.skill5_result is not None

    def set_mode(self, mode: Mode) -> None:
        self.mode = mode

    def set_student_profile(self, profile: JsonDict) -> None:
        self.student_profile = dict(profile)

    def set_resource_context(self, resource_context: JsonDict) -> None:
        self.resource_context = dict(resource_context)

    def set_results(
        self,
        *,
        skill3_result: JsonDict,
        skill4_result: JsonDict,
        skill5_result: JsonDict,
        temporary_paths: list[Path],
    ) -> None:
        self.skill3_result = skill3_result
        self.skill4_result = skill4_result
        self.skill5_result = skill5_result
        self.temporary_paths = list(temporary_paths)

    def set_agent_profile(self, agent_profile: JsonDict) -> None:
        self.agent_profile = dict(agent_profile)

    def set_latest_plan(self, latest_plan: JsonDict) -> None:
        self.latest_plan = dict(latest_plan)

    def set_active_strategy(self, active_strategy: JsonDict) -> None:
        self.active_strategy = dict(active_strategy)

    def set_pending_clarification(
        self, pending_clarification_questions: list[JsonDict], pending_goal_text: str
    ) -> None:
        self.pending_clarification_questions = [dict(item) for item in pending_clarification_questions]
        self.pending_goal_text = pending_goal_text

    def reset(self) -> None:
        for path in self.temporary_paths:
            if path.exists():
                path.unlink()
        self.mode = None
        self.student_profile = None
        self.resource_context = None
        self.skill3_result = None
        self.skill4_result = None
        self.skill5_result = None
        self.temporary_paths = []
        self.conversation_history = []
        self.agent_profile = None
        self.latest_plan = None
        self.active_strategy = None
        self.decision_trace = []
        self.rerun_count = 0
        self.pending_clarification_questions = []
        self.pending_goal_text = ""
