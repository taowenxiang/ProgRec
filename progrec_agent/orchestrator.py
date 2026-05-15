from __future__ import annotations

import json
from pathlib import Path

from progrec_agent.adapters.skill2_adapter import resolve_skill2_resources
from progrec_agent.adapters.skill3_adapter import run_skill3
from progrec_agent.adapters.skill4_adapter import run_skill4_custom_mode, run_skill4_dataset_mode
from progrec_agent.adapters.skill5_adapter import run_skill5
from progrec_agent.config import ResourceConfig
from progrec_agent.schemas import assert_agent_student_alignment


class ProgRecOrchestrator:
    def __init__(self, *, repo_root: Path, temp_dir: Path) -> None:
        self.repo_root = repo_root
        self.temp_dir = temp_dir

    def recommend_for_student_id(
        self,
        student_id: str,
        top_k: int = 5,
        *,
        bundle: ResourceConfig | None = None,
        skip_skill5: bool = False,
    ) -> dict[str, object]:
        if bundle is not None:
            students_path = bundle.skill2_students
            students_payload = json.loads(Path(students_path).read_text(encoding="utf-8"))
            resource_context: dict[str, object] = {
                "resource_mode": bundle.mode,
                "students_path": str(bundle.skill2_students.resolve()),
                "mentors_path": str(bundle.skill2_mentors.resolve()),
                "graph_path": str(bundle.skill2_graph.resolve()) if bundle.skill2_graph else None,
            }
        else:
            resources = resolve_skill2_resources(self.repo_root)
            students_path = Path(str(resources["students_path"]))
            students_payload = json.loads(students_path.read_text(encoding="utf-8"))
            resource_context = dict(resources)
        student_profile = next(
            student for student in students_payload["students"] if student["student_id"] == student_id
        )
        skill3_path = self.temp_dir / "skill3.json"
        skill4_path = self.temp_dir / "skill4.json"
        skill5_path = self.temp_dir / "skill5.json"
        if bundle is not None and bundle.mode == "graph":
            skill3_result = run_skill3(
                self.repo_root,
                student_profile,
                top_k,
                skill2_graph=bundle.skill2_graph,
                skill2_students=bundle.skill2_students,
                skill2_mentors=bundle.skill2_mentors,
            )
        else:
            skill3_result = run_skill3(self.repo_root, student_profile, top_k)
        skill3_path.write_text(json.dumps(skill3_result, ensure_ascii=False, indent=2), encoding="utf-8")
        skill4_result = run_skill4_dataset_mode(
            repo_root=self.repo_root,
            student_id=student_id,
            skill3_path=skill3_path,
            output_path=skill4_path,
            bundle=bundle,
        )
        skill4_path.write_text(json.dumps(skill4_result, ensure_ascii=False, indent=2), encoding="utf-8")
        assert_agent_student_alignment(
            expected_student_id=student_id,
            skill3_path=skill3_path,
            skill4_path=skill4_path,
        )
        if skip_skill5:
            skill5_result: dict[str, object] = {}
            paths = [skill3_path, skill4_path]
        else:
            skill5_result = run_skill5(
                repo_root=self.repo_root,
                skill3_path=skill3_path,
                skill4_path=skill4_path,
                output_path=skill5_path,
                student_id=student_id,
                top_k=top_k,
            )
            paths = [skill3_path, skill4_path, skill5_path]
        return {
            "mode": "dataset_mode",
            "student_profile": student_profile,
            "resource_context": resource_context,
            "skill3_result": skill3_result,
            "skill4_result": skill4_result,
            "skill5_result": skill5_result,
            "temporary_paths": paths,
            "skip_skill5": skip_skill5,
        }

    def recommend_for_profile(self, student_profile: dict[str, object], top_k: int = 5) -> dict[str, object]:
        skill3_path = self.temp_dir / "skill3.json"
        skill4_path = self.temp_dir / "skill4.json"
        skill5_path = self.temp_dir / "skill5.json"
        skill3_result = run_skill3(self.repo_root, student_profile, top_k)
        skill3_path.write_text(json.dumps(skill3_result, ensure_ascii=False, indent=2), encoding="utf-8")
        skill4_result = run_skill4_custom_mode(
            repo_root=self.repo_root,
            student_profile=student_profile,
            skill3_result=skill3_result,
            output_path=skill4_path,
        )
        assert_agent_student_alignment(
            expected_student_id=str(student_profile["student_id"]),
            skill3_path=skill3_path,
            skill4_path=skill4_path,
        )
        skill5_result = run_skill5(
            repo_root=self.repo_root,
            skill3_path=skill3_path,
            skill4_path=skill4_path,
            output_path=skill5_path,
            student_id=str(student_profile["student_id"]),
            top_k=top_k,
        )
        return {
            "mode": "custom_profile_mode",
            "student_profile": student_profile,
            "resource_context": {"resource_mode": "custom_profile_mode"},
            "skill3_result": skill3_result,
            "skill4_result": skill4_result,
            "skill5_result": skill5_result,
            "temporary_paths": [skill3_path, skill4_path, skill5_path],
        }

    def rank_mentors_for_profile(self, student_profile: dict[str, object], top_k: int = 5) -> dict[str, object]:
        skill3_path = self.temp_dir / "skill3.json"
        skill3_result = run_skill3(self.repo_root, student_profile, top_k)
        skill3_path.write_text(json.dumps(skill3_result, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "mode": "custom_profile_mentor_only",
            "student_profile": student_profile,
            "resource_context": {"resource_mode": "custom_profile_mentor_only"},
            "skill3_result": skill3_result,
            "temporary_paths": [skill3_path],
        }

    def expand_projects_and_teammates_for_profile(
        self,
        student_profile: dict[str, object],
        top_k: int = 5,
        *,
        skill3_result: dict[str, object] | None = None,
    ) -> dict[str, object]:
        skill3_path = self.temp_dir / "skill3.json"
        skill4_path = self.temp_dir / "skill4.json"
        resolved_skill3 = skill3_result or run_skill3(self.repo_root, student_profile, top_k)
        skill3_path.write_text(json.dumps(resolved_skill3, ensure_ascii=False, indent=2), encoding="utf-8")
        skill4_result = run_skill4_custom_mode(
            repo_root=self.repo_root,
            student_profile=student_profile,
            skill3_result=resolved_skill3,
            output_path=skill4_path,
        )
        assert_agent_student_alignment(
            expected_student_id=str(student_profile["student_id"]),
            skill3_path=skill3_path,
            skill4_path=skill4_path,
        )
        return {
            "mode": "custom_profile_project_teammate_only",
            "student_profile": student_profile,
            "resource_context": {"resource_mode": "custom_profile_project_teammate_only"},
            "skill3_result": resolved_skill3,
            "skill4_result": skill4_result,
            "temporary_paths": [skill3_path, skill4_path],
        }
