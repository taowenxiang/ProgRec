from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from progrec_agent.chat_tool_registry import get_chat_tool
from progrec_agent.runtime import recommendation_runtime as default_recommendation_runtime
from progrec_agent.runtime.profile_standardizer import standardize_temporary_profile


@dataclass
class ToolExecutionResult:
    tool_name: str
    skill_id: str
    status: str
    summary: str
    payload: dict[str, Any]

    def to_skill_trace_entry(self) -> dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "summary": self.summary,
        }


class ChatToolExecutor:
    def __init__(self, *, repo_root: Path, temp_dir: Path, recommendation_runtime=None) -> None:
        self.repo_root = repo_root
        self.temp_dir = temp_dir
        self.recommendation_runtime = recommendation_runtime or default_recommendation_runtime

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolExecutionResult:
        tool = get_chat_tool(tool_name)
        for required in tool.required_arguments:
            if required not in arguments:
                raise ValueError(f"Tool {tool_name} requires argument {required!r}.")

        if tool_name == "/student-profiling.build_temporary_profile":
            profile_context = dict(arguments["profile_context"])
            profile = standardize_temporary_profile(profile_context)
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id=tool.skill_id,
                status="succeeded",
                summary="Built a temporary student profile from the conversation context.",
                payload={"profile": profile},
            )

        if tool_name == "/student-profiling.update_profile_context":
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id=tool.skill_id,
                status="succeeded",
                summary="Updated the student profile context from the latest user message.",
                payload={"profile_context": dict(arguments["profile_context"])},
            )

        if tool_name == "/mentor-discovery.rank_mentors":
            payload = self.recommendation_runtime.run_mentor_recommendation_for_profile(
                repo_root=self.repo_root,
                temp_dir=self.temp_dir,
                profile=dict(arguments["profile"]),
                top_k=int(arguments.get("top_k") or 5),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id=tool.skill_id,
                status="succeeded",
                summary="Ranked mentor candidates for the current student profile.",
                payload=dict(payload),
            )

        if tool_name == "/project-teammate-discovery.recommend_projects":
            payload = self.recommendation_runtime.run_project_recommendations_for_profile(
                repo_root=self.repo_root,
                temp_dir=self.temp_dir,
                profile=dict(arguments["profile"]),
                mentor_result=arguments.get("mentor_result") if isinstance(arguments.get("mentor_result"), dict) else None,
                top_k=int(arguments.get("top_k") or 5),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id=tool.skill_id,
                status="succeeded",
                summary="Recommended projects for the current student profile.",
                payload=dict(payload),
            )

        if tool_name == "/project-teammate-discovery.recommend_teammates":
            payload = self.recommendation_runtime.run_teammate_recommendations_for_profile(
                repo_root=self.repo_root,
                temp_dir=self.temp_dir,
                profile=dict(arguments["profile"]),
                mentor_result=arguments.get("mentor_result") if isinstance(arguments.get("mentor_result"), dict) else None,
                top_k=int(arguments.get("top_k") or 5),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id=tool.skill_id,
                status="succeeded",
                summary="Recommended teammates for the current student profile.",
                payload=dict(payload),
            )

        raise ValueError(f"Tool {tool_name!r} is registered but has no executor implementation yet.")
