from __future__ import annotations

import json
import subprocess
from pathlib import Path

from progrec_agent.agent_schema import ToolExecutionResult
from progrec_agent.config import resolve_repo_root, resolve_resource_config
from progrec_agent.orchestrator import ProgRecOrchestrator


class ToolExecutor:
    def __init__(self, *, repo_root: Path, temp_dir: Path) -> None:
        self.repo_root = resolve_repo_root(repo_root)
        self.temp_dir = temp_dir
        self.orchestrator = ProgRecOrchestrator(repo_root=self.repo_root, temp_dir=self.temp_dir)

    def execute(self, tool_name: str, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            return ToolExecutionResult(tool_name=tool_name, ok=False, error=f"Unknown tool: {tool_name}")
        return handler(arguments, session=session)

    def _resolve_mentors_path(self, *, session) -> Path | None:
        resource_context = dict(session.resource_context or {})
        mentors_path = resource_context.get("mentors_path")
        if mentors_path:
            return Path(str(mentors_path))
        try:
            resources = resolve_resource_config("demo", self.repo_root)
        except (FileNotFoundError, ValueError):
            return None
        return resources.skill2_mentors

    @staticmethod
    def _load_mentor_profiles(mentors_path: Path) -> dict[str, dict[str, object]]:
        payload = json.loads(mentors_path.read_text(encoding="utf-8"))
        rows = payload.get("mentors") if isinstance(payload, dict) else payload
        mentors = rows if isinstance(rows, list) else []
        return {
            str(mentor.get("mentor_id")): dict(mentor)
            for mentor in mentors
            if isinstance(mentor, dict) and mentor.get("mentor_id")
        }

    def _tool_show_current_profile(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        return ToolExecutionResult(
            tool_name="show_current_profile",
            ok=True,
            payload={"student_profile": dict(session.student_profile or {})},
        )

    def _tool_show_recommended_mentor_profile(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        skill5_result = dict(session.skill5_result or {})
        recs = dict(skill5_result.get("recommendations") or {})
        mentors = list(recs.get("mentors") or [])
        if not mentors:
            return ToolExecutionResult(
                tool_name="show_recommended_mentor_profile",
                ok=False,
                error="No mentor recommendations are available yet. Run recommend first.",
            )

        requested_mentor_id = str(arguments.get("mentor_id") or "").strip()
        mentor_recommendation = (
            next((item for item in mentors if str(item.get("mentor_id")) == requested_mentor_id), None)
            if requested_mentor_id
            else None
        )
        if mentor_recommendation is None:
            mentor_recommendation = dict(mentors[0])
        else:
            mentor_recommendation = dict(mentor_recommendation)

        mentor_id = str(mentor_recommendation.get("mentor_id") or "").strip()
        mentor_profile: dict[str, object] = {}
        mentors_path = self._resolve_mentors_path(session=session)
        if mentors_path and mentors_path.is_file():
            mentor_profile = self._load_mentor_profiles(mentors_path).get(mentor_id, {})

        if not mentor_profile:
            mentor_profile = {
                "mentor_id": mentor_id,
                "name": mentor_recommendation.get("mentor_name") or mentor_id,
            }

        return ToolExecutionResult(
            tool_name="show_recommended_mentor_profile",
            ok=True,
            payload={
                "rank": mentor_recommendation.get("rank") or 1,
                "mentor_recommendation": mentor_recommendation,
                "mentor_profile": mentor_profile,
            },
        )

    def _tool_recommend_full_pipeline(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        student_id = str(arguments.get("student_id") or "").strip()
        mode = str(arguments.get("mode") or "").strip().lower()
        bundle = None
        if mode in {"demo", "graph"}:
            try:
                bundle = resolve_resource_config(mode, self.repo_root, validate_graph=True)
            except (FileNotFoundError, ValueError) as exc:
                return ToolExecutionResult(tool_name="recommend_full_pipeline", ok=False, error=str(exc))

        if student_id:
            result = self.orchestrator.recommend_for_student_id(student_id, top_k=5, bundle=bundle)
        elif session.student_profile and session.student_profile.get("student_id"):
            result = self.orchestrator.recommend_for_profile(dict(session.student_profile), top_k=5)
        else:
            return ToolExecutionResult(
                tool_name="recommend_full_pipeline",
                ok=False,
                error="No active student profile or student_id was provided for recommendation.",
            )
        session.set_mode(result["mode"])
        session.set_student_profile(result["student_profile"])
        session.set_resource_context(result["resource_context"])
        session.set_results(
            skill3_result=result["skill3_result"],
            skill4_result=result["skill4_result"],
            skill5_result=result["skill5_result"],
            temporary_paths=result["temporary_paths"],
        )
        return ToolExecutionResult(tool_name="recommend_full_pipeline", ok=True, payload=result)

    def _tool_inspect_artifacts(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        return ToolExecutionResult(
            tool_name="inspect_artifacts",
            ok=True,
            payload={
                "mode": session.mode,
                "temporary_paths": [str(path) for path in session.temporary_paths],
                "resource_context": dict(session.resource_context or {}),
            },
        )

    def _tool_debug_graph_mode(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        try:
            bundle = resolve_resource_config("graph", self.repo_root, validate_graph=False)
        except (FileNotFoundError, ValueError) as exc:
            return ToolExecutionResult(tool_name="debug_graph_mode", ok=False, error=str(exc))
        return ToolExecutionResult(
            tool_name="debug_graph_mode",
            ok=True,
            payload={
                "student_id": str(arguments.get("student_id") or ""),
                "graph_exists": bool(bundle.skill2_graph and bundle.skill2_graph.exists()),
                "students_path": str(bundle.skill2_students),
                "mentors_path": str(bundle.skill2_mentors),
                "graph_path": str(bundle.skill2_graph) if bundle.skill2_graph else "",
            },
        )

    def _tool_rebuild_skill2_graph(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        script = self.repo_root / "skill2_academic_graph_builder" / "regenerate_kit" / "scripts" / "build_graph.py"
        completed = subprocess.run(
            ["python3", str(script)],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return ToolExecutionResult(tool_name="rebuild_skill2_graph", ok=False, error=completed.stderr.strip())
        return ToolExecutionResult(
            tool_name="rebuild_skill2_graph",
            ok=True,
            payload={"stdout": completed.stdout.strip()},
        )

    def _tool_rebuild_skill1_profiles(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        return ToolExecutionResult(
            tool_name="rebuild_skill1_profiles",
            ok=False,
            error="Skill 1 rebuild is not configured in-repo; provide an external entrypoint before enabling this tool.",
        )
