from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChatTool:
    name: str
    skill_id: str
    description: str
    required_arguments: list[str]
    optional_arguments: list[str] = field(default_factory=list)
    allowed_targets: list[str] = field(default_factory=list)
    planner_notes: str = ""


CHAT_TOOLS: dict[str, ChatTool] = {
    "/student-profiling.build_temporary_profile": ChatTool(
        name="/student-profiling.build_temporary_profile",
        skill_id="/student-profiling",
        description="Build a normalized temporary student profile from the conversation context.",
        required_arguments=["profile_context"],
        optional_arguments=["top_k"],
        allowed_targets=["mentor", "project", "teammate"],
        planner_notes="Use this before discovery tools when the chat does not already have a usable profile.",
    ),
    "/student-profiling.update_profile_context": ChatTool(
        name="/student-profiling.update_profile_context",
        skill_id="/student-profiling",
        description="Merge new user-provided profile details into the current profile context.",
        required_arguments=["profile_context"],
        optional_arguments=[],
        allowed_targets=["mentor", "project", "teammate"],
        planner_notes="Use this when the user answers a profile clarification question.",
    ),
    "/mentor-discovery.rank_mentors": ChatTool(
        name="/mentor-discovery.rank_mentors",
        skill_id="/mentor-discovery",
        description="Rank mentor candidates for the current student profile.",
        required_arguments=["profile"],
        optional_arguments=["top_k"],
        allowed_targets=["mentor"],
        planner_notes="Do not call this for project or teammate recommendations.",
    ),
    "/project-teammate-discovery.recommend_projects": ChatTool(
        name="/project-teammate-discovery.recommend_projects",
        skill_id="/project-teammate-discovery",
        description="Recommend projects after a user requests projects or accepts a project follow-up.",
        required_arguments=["profile"],
        optional_arguments=["mentor_result", "top_k"],
        allowed_targets=["project"],
        planner_notes="Only call after the user requests projects or accepts a project suggestion.",
    ),
    "/project-teammate-discovery.recommend_teammates": ChatTool(
        name="/project-teammate-discovery.recommend_teammates",
        skill_id="/project-teammate-discovery",
        description="Recommend teammates after a user requests teammates or accepts a teammate follow-up.",
        required_arguments=["profile"],
        optional_arguments=["mentor_result", "top_k"],
        allowed_targets=["teammate"],
        planner_notes="Only call after the user requests teammates or accepts a teammate suggestion.",
    ),
    "/social-ranking.rerank_candidates": ChatTool(
        name="/social-ranking.rerank_candidates",
        skill_id="/social-ranking",
        description="Rerank a mixed set of mentors, projects, and teammates when the user asks for a combined package.",
        required_arguments=["skill3_result", "skill4_result"],
        optional_arguments=["top_k"],
        allowed_targets=["mentor", "project", "teammate"],
        planner_notes="Do not call for mentor-only requests.",
    ),
}


def list_chat_tools() -> list[ChatTool]:
    return list(CHAT_TOOLS.values())


def get_chat_tool(name: str) -> ChatTool:
    if name not in CHAT_TOOLS:
        raise KeyError(f"Unknown chat tool {name!r}. Known tools: {sorted(CHAT_TOOLS)}")
    return CHAT_TOOLS[name]


def allowed_tool_names() -> set[str]:
    return set(CHAT_TOOLS)


def planner_tool_context() -> str:
    lines: list[str] = []
    for tool in list_chat_tools():
        lines.append(
            "\n".join(
                [
                    f"tool: {tool.name}",
                    f"skill_id: {tool.skill_id}",
                    f"description: {tool.description}",
                    f"required_arguments: {', '.join(tool.required_arguments)}",
                    f"optional_arguments: {', '.join(tool.optional_arguments) or 'none'}",
                    f"allowed_targets: {', '.join(tool.allowed_targets) or 'any'}",
                    f"notes: {tool.planner_notes}",
                ]
            )
        )
    return "\n\n".join(lines)
