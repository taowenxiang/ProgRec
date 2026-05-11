from __future__ import annotations

from pathlib import Path

from sturec_agent.adapters.skill3_adapter import run_skill3


class AgentTools:
    def __init__(self, *, repo_root: Path, temp_dir: Path) -> None:
        self.repo_root = repo_root
        self.temp_dir = temp_dir

    def run_mentor_discovery_tool(
        self, student_profile: dict[str, object], top_k: int
    ) -> dict[str, object]:
        return run_skill3(self.repo_root, student_profile, top_k)
