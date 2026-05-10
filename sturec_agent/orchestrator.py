from __future__ import annotations

import json
from pathlib import Path

from sturec_agent.adapters.skill2_adapter import resolve_skill2_resources
from sturec_agent.adapters.skill3_adapter import run_skill3
from sturec_agent.adapters.skill4_adapter import run_skill4_dataset_mode
from sturec_agent.adapters.skill5_adapter import run_skill5


class StuRecOrchestrator:
    def __init__(self, *, repo_root: Path, temp_dir: Path) -> None:
        self.repo_root = repo_root
        self.temp_dir = temp_dir

    def recommend_for_student_id(self, student_id: str, top_k: int = 5) -> dict[str, object]:
        resources = resolve_skill2_resources(self.repo_root)
        students_payload = json.loads(Path(resources["students_path"]).read_text(encoding="utf-8"))
        student_profile = next(
            student for student in students_payload["students"] if student["student_id"] == student_id
        )
        skill3_path = self.temp_dir / "skill3.json"
        skill4_path = self.temp_dir / "skill4.json"
        skill5_path = self.temp_dir / "skill5.json"
        skill3_result = run_skill3(self.repo_root, student_profile, top_k)
        skill3_path.write_text(json.dumps(skill3_result, ensure_ascii=False, indent=2), encoding="utf-8")
        skill4_result = run_skill4_dataset_mode(
            repo_root=self.repo_root,
            student_id=student_id,
            skill3_path=skill3_path,
            output_path=skill4_path,
        )
        skill4_path.write_text(json.dumps(skill4_result, ensure_ascii=False, indent=2), encoding="utf-8")
        skill5_result = run_skill5(
            repo_root=self.repo_root,
            skill3_path=skill3_path,
            skill4_path=skill4_path,
            output_path=skill5_path,
            student_id=student_id,
            top_k=top_k,
        )
        return {
            "mode": "dataset_mode",
            "student_profile": student_profile,
            "resource_context": resources,
            "skill3_result": skill3_result,
            "skill4_result": skill4_result,
            "skill5_result": skill5_result,
            "temporary_paths": [skill3_path, skill4_path, skill5_path],
        }
