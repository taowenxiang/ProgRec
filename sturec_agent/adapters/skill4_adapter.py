from __future__ import annotations

import json
import sys
from pathlib import Path

_SKILL4_ROOT = Path(__file__).resolve().parents[2] / "skill4_handoff"
if str(_SKILL4_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL4_ROOT))

from skill.discovery import discover_projects_and_teammates, run_pipeline_from_cli_config
from skill.skill2_adapter import load_academic_graph


def run_skill4_dataset_mode(
    *,
    repo_root: Path,
    student_id: str,
    skill3_path: Path,
    output_path: Path,
) -> dict[str, object]:
    cfg = {
        "target_student_id": student_id,
        "skill1_profiles_path": str(repo_root / "skill1_handoff/student_profiles_normalized.jsonl"),
        "skill2_graph_path": "",
        "skill2_students_path": "",
        "skill2_mentors_path": "",
        "mentor_candidates_path": str(skill3_path),
        "skill3_output_path": str(skill3_path),
        "mock_projects_path": str(repo_root / "skill4_handoff/data/mock_projects.json"),
        "mock_mentor_candidates_path": str(repo_root / "skill4_handoff/data/mock_mentor_candidates.json"),
        "output_path": str(output_path),
        "top_n_projects": 3,
        "top_n_teammates": 3,
        "max_candidate_teammates": 120,
        "fallback_mentor_top_k": 10,
        "strict_target_student": False,
        "allow_target_fallback_with_skill3": False,
        "_embedding_context": None,
    }
    return run_pipeline_from_cli_config(cfg)


def run_skill4_custom_mode(
    *,
    repo_root: Path,
    student_profile: dict[str, object],
    skill3_result: dict[str, object],
    output_path: Path,
) -> dict[str, object]:
    students_path = repo_root / "skill2_handoff/outputs/student_profiles_standard.json"
    students_payload = json.loads(students_path.read_text(encoding="utf-8"))
    all_students = list(students_payload.get("students") or [])
    graph_path = repo_root / "skill2_handoff/regenerate_kit/data/processed/academic_graph.json"
    graph = load_academic_graph(graph_path) if graph_path.is_file() else None
    result = discover_projects_and_teammates(
        target_student_id=str(student_profile["student_id"]),
        target_student_profile=student_profile,
        all_student_profiles=all_students,
        mentor_candidates=list(skill3_result.get("mentor_candidates") or []),
        graph=graph,
        mock_projects_path=repo_root / "skill4_handoff/data/mock_projects.json",
        top_n_projects=3,
        top_n_teammates=3,
        max_candidate_teammates=120,
        data_sources={"mode": "custom_profile_mode"},
    )
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
