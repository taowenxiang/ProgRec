from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import uuid

from progrec_agent.capability_adapters import academic_graph, mentor_discovery, project_teammate_discovery, student_profiling
from progrec_agent.contracts.registry import get_capability
from progrec_agent.inspectors import (
    bundle_result_inspector,
    mentor_result_inspector,
    project_result_inspector,
    teammate_result_inspector,
)
from progrec_agent.runtime import recommendation_runtime as default_recommendation_runtime


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
        canonical_tool_name = get_capability(tool_name).capability_id

        if canonical_tool_name == "/student-profiling.build_temporary_profile":
            _require_any_argument(tool_name, arguments, ["profile_context"])
            payload = student_profiling.build_temporary_profile(
                profile_context=arguments["profile_context"],
                executor_context=self,
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/student-profiling",
                status="succeeded",
                summary="Built a temporary student profile from the conversation context.",
                payload=self._make_action_result_payload(
                    tool_name=canonical_tool_name,
                    result_type="student_profile",
                    input_refs=[],
                    summary={"student_id": str(payload["profile"].get("student_id") or "")},
                    payload=payload,
                ),
            )

        if canonical_tool_name == "/student-profiling.update_profile_context":
            _require_any_argument(tool_name, arguments, ["profile_context"])
            payload = student_profiling.update_profile_context(
                profile_context=arguments["profile_context"],
                executor_context=self,
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/student-profiling",
                status="succeeded",
                summary="Updated the student profile context from the latest user message.",
                payload=self._make_action_result_payload(
                    tool_name=canonical_tool_name,
                    result_type="student_profile",
                    input_refs=[],
                    summary={"field_count": len(payload["profile_context"])},
                    payload=payload,
                ),
            )

        if canonical_tool_name == "/mentor-discovery.recommend_mentors":
            _require_any_argument(tool_name, arguments, ["student_profile_ref", "profile"])
            profile_ref = _coerce_profile_ref(arguments)
            payload = mentor_discovery.recommend_mentors(
                student_profile_ref=profile_ref,
                top_k=arguments.get("top_k") or 5,
                executor_context=self,
            )
            candidates = list(dict(payload.get("skill3_result") or {}).get("mentor_candidates") or [])
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/mentor-discovery",
                status="succeeded",
                summary="Ranked mentor candidates for the current student profile.",
                payload=self._make_action_result_payload(
                    tool_name=canonical_tool_name,
                    result_type="mentor_result",
                    input_refs=[str(profile_ref.get("result_ref") or "")] if profile_ref.get("result_ref") else [],
                    summary={
                        "count": len(candidates),
                        "top_ids": [str(item.get("mentor_id") or "") for item in candidates[:3]],
                    },
                    payload=dict(payload),
                ),
            )

        if canonical_tool_name == "/project-teammate-discovery.recommend_projects":
            _require_any_argument(tool_name, arguments, ["student_profile_ref", "profile"])
            profile_ref = _coerce_profile_ref(arguments)
            mentor_result_ref = _coerce_mentor_result_ref(arguments)
            payload = project_teammate_discovery.recommend_projects(
                student_profile_ref=profile_ref,
                mentor_result_ref=mentor_result_ref,
                top_k=arguments.get("top_k") or 5,
                executor_context=self,
            )
            projects = list(payload.get("projects") or [])
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/project-teammate-discovery",
                status="succeeded",
                summary="Recommended projects for the current student profile.",
                payload=self._make_action_result_payload(
                    tool_name=canonical_tool_name,
                    result_type="project_result",
                    input_refs=_collect_input_refs(profile_ref, mentor_result_ref),
                    summary={
                        "count": len(projects),
                        "top_ids": [str(item.get("project_id") or "") for item in projects[:3]],
                    },
                    payload=dict(payload),
                ),
            )

        if canonical_tool_name == "/project-teammate-discovery.recommend_teammates":
            _require_any_argument(tool_name, arguments, ["student_profile_ref", "profile"])
            profile_ref = _coerce_profile_ref(arguments)
            mentor_result_ref = _coerce_mentor_result_ref(arguments)
            payload = project_teammate_discovery.recommend_teammates(
                student_profile_ref=profile_ref,
                mentor_result_ref=mentor_result_ref,
                top_k=arguments.get("top_k") or 5,
                executor_context=self,
            )
            teammates = list(payload.get("teammates") or [])
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/project-teammate-discovery",
                status="succeeded",
                summary="Recommended teammates for the current student profile.",
                payload=self._make_action_result_payload(
                    tool_name=canonical_tool_name,
                    result_type="teammate_result",
                    input_refs=_collect_input_refs(profile_ref, mentor_result_ref),
                    summary={
                        "count": len(teammates),
                        "top_ids": [str(item.get("student_id") or item.get("teammate_id") or "") for item in teammates[:3]],
                    },
                    payload=dict(payload),
                ),
            )

        if canonical_tool_name == "/academic-graph.validate_graph_resources":
            _require_any_argument(tool_name, arguments, ["mode"])
            payload = academic_graph.validate_graph_resources(
                mode=arguments["mode"],
                executor_context=self,
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/academic-graph",
                status="succeeded",
                summary="Validated the configured academic graph resources.",
                payload=self._make_action_result_payload(
                    tool_name=canonical_tool_name,
                    result_type="resource_validation",
                    input_refs=[],
                    summary={"mode": str(payload.get("mode") or "")},
                    payload=payload,
                ),
            )

        if canonical_tool_name == "/mentor-discovery.get_mentor_by_rank":
            _require_any_argument(tool_name, arguments, ["mentor_result_ref", "rank"])
            card = mentor_result_inspector.get_mentor_by_rank(
                dict(arguments["mentor_result_ref"]),
                rank=int(arguments["rank"]),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/mentor-discovery",
                status="succeeded",
                summary="Expanded the selected mentor from the current mentor result.",
                payload={"payload": card, **card},
            )

        if canonical_tool_name == "/mentor-discovery.explain_mentor_match":
            _require_any_argument(tool_name, arguments, ["mentor_result_ref", "rank"])
            card = mentor_result_inspector.explain_mentor_match(
                dict(arguments["mentor_result_ref"]),
                rank=int(arguments["rank"]),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/mentor-discovery",
                status="succeeded",
                summary="Explained why the selected mentor was recommended.",
                payload={"payload": card, **card},
            )

        if canonical_tool_name == "/project-teammate-discovery.get_project_by_rank":
            _require_any_argument(tool_name, arguments, ["project_result_ref", "rank"])
            card = project_result_inspector.get_project_by_rank(
                dict(arguments["project_result_ref"]),
                rank=int(arguments["rank"]),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/project-teammate-discovery",
                status="succeeded",
                summary="Expanded the selected project from the current project result.",
                payload={"payload": card, **card},
            )

        if canonical_tool_name == "/project-teammate-discovery.explain_project_match":
            _require_any_argument(tool_name, arguments, ["project_result_ref", "rank"])
            card = project_result_inspector.explain_project_match(
                dict(arguments["project_result_ref"]),
                rank=int(arguments["rank"]),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/project-teammate-discovery",
                status="succeeded",
                summary="Explained why the selected project was recommended.",
                payload={"payload": card, **card},
            )

        if canonical_tool_name == "/project-teammate-discovery.get_teammate_by_rank":
            _require_any_argument(tool_name, arguments, ["teammate_result_ref", "rank"])
            card = teammate_result_inspector.get_teammate_by_rank(
                dict(arguments["teammate_result_ref"]),
                rank=int(arguments["rank"]),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/project-teammate-discovery",
                status="succeeded",
                summary="Expanded the selected teammate from the current teammate result.",
                payload={"payload": card, **card},
            )

        if canonical_tool_name == "/project-teammate-discovery.explain_teammate_match":
            _require_any_argument(tool_name, arguments, ["teammate_result_ref", "rank"])
            card = teammate_result_inspector.explain_teammate_match(
                dict(arguments["teammate_result_ref"]),
                rank=int(arguments["rank"]),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/project-teammate-discovery",
                status="succeeded",
                summary="Explained why the selected teammate was recommended.",
                payload={"payload": card, **card},
            )

        if canonical_tool_name == "/social-ranking.show_bundle_summary":
            _require_any_argument(tool_name, arguments, ["bundle_result_ref"])
            summary = bundle_result_inspector.show_bundle_summary(dict(arguments["bundle_result_ref"]))
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/social-ranking",
                status="succeeded",
                summary="Loaded the current bundle summary.",
                payload={"payload": summary, **summary},
            )

        raise ValueError(f"Tool {tool_name!r} is registered but has no executor implementation yet.")

    def _make_action_result_payload(
        self,
        *,
        tool_name: str,
        result_type: str,
        input_refs: list[str],
        summary: dict[str, object],
        payload: dict[str, object],
    ) -> dict[str, Any]:
        contract = get_capability(tool_name)
        result_ref_payload: dict[str, Any] = {
            "result_ref": f"rr_{result_type}_{uuid.uuid4().hex[:8]}",
            "result_type": result_type,
            "owner_skill": contract.owner_skill,
            "input_refs": list(input_refs),
            "summary": dict(summary),
            "followups": list(contract.followups),
            "payload": dict(payload),
        }
        for key, value in payload.items():
            if key not in result_ref_payload:
                result_ref_payload[key] = value
        return result_ref_payload


def _coerce_profile_ref(arguments: dict[str, Any]) -> dict[str, object]:
    if isinstance(arguments.get("student_profile_ref"), dict):
        return dict(arguments["student_profile_ref"])
    if isinstance(arguments.get("profile"), dict):
        return {
            "result_ref": "",
            "result_type": "student_profile",
            "payload": {"profile": dict(arguments["profile"])},
        }
    raise ValueError("A student profile reference or profile payload is required.")


def _coerce_mentor_result_ref(arguments: dict[str, Any]) -> dict[str, object] | None:
    if isinstance(arguments.get("mentor_result_ref"), dict):
        return dict(arguments["mentor_result_ref"])
    if isinstance(arguments.get("mentor_result"), dict):
        return {
            "result_ref": "",
            "result_type": "mentor_result",
            "payload": dict(arguments["mentor_result"]),
        }
    return None


def _collect_input_refs(profile_ref: dict[str, object], mentor_result_ref: dict[str, object] | None) -> list[str]:
    refs: list[str] = []
    profile_result_ref = str(profile_ref.get("result_ref") or "").strip()
    if profile_result_ref:
        refs.append(profile_result_ref)
    if mentor_result_ref is not None:
        mentor_ref = str(mentor_result_ref.get("result_ref") or "").strip()
        if mentor_ref:
            refs.append(mentor_ref)
    return refs


def _require_any_argument(tool_name: str, arguments: dict[str, Any], required_keys: list[str]) -> None:
    missing = [key for key in required_keys if key not in arguments]
    if not missing:
        return
    if len(required_keys) == 1:
        raise ValueError(f"Tool {tool_name} requires argument {required_keys[0]!r}.")
    present = [key for key in required_keys if key in arguments]
    if present:
        return
    raise ValueError(
        f"Tool {tool_name} requires one of {', '.join(repr(key) for key in required_keys)}."
    )
