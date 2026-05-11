from __future__ import annotations

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

    def _tool_show_current_profile(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        return ToolExecutionResult(
            tool_name="show_current_profile",
            ok=True,
            payload={"student_profile": dict(session.student_profile or {})},
        )

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
        script = self.repo_root / "skill2_handoff" / "regenerate_kit" / "scripts" / "build_graph.py"
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
