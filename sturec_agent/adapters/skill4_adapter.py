from __future__ import annotations

import sys
from pathlib import Path

_SKILL4_ROOT = Path(__file__).resolve().parents[2] / "skill4_handoff"
if str(_SKILL4_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL4_ROOT))

from skill.discovery import run_pipeline_from_cli_config


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
