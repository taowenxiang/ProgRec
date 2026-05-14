from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill.discovery import run_pipeline_from_cli_config


def test_strict_raises_on_skill3_student_mismatch(tmp_path: Path) -> None:
    s2 = tmp_path / "s2.json"
    s2.write_text(
        '{"version":"1.0","students":[{"student_id":"s_002","grade":"Y2","major":"CS","skills":["a"],"interests":["b"],"availability":""}]}',
        encoding="utf-8",
    )
    s3 = tmp_path / "s3.json"
    s3.write_text(
        json.dumps(
            {
                "student_id": "other-student",
                "mentor_candidates": [{"mentor_id": "m_1", "final_score": 0.5, "topic_score": 0.5, "graph_score": 0.0}],
            }
        ),
        encoding="utf-8",
    )
    cfg = {
        "target_student_id": "s_002",
        "skill1_profiles_path": "",
        "skill2_students_path": str(s2),
        "skill2_graph_path": "",
        "skill2_mentors_path": "",
        "mentor_candidates_path": str(s3),
        "skill3_output_path": str(s3),
        "mock_projects_path": str(Path(__file__).resolve().parents[1] / "data" / "mock_projects.json"),
        "mock_mentor_candidates_path": "",
        "strict_target_student": True,
        "allow_target_fallback_with_skill3": False,
        "top_n_projects": 1,
        "top_n_teammates": 1,
        "max_candidate_teammates": 5,
        "fallback_mentor_top_k": 2,
    }
    with pytest.raises(ValueError, match="skill3_target_student_id_mismatch"):
        run_pipeline_from_cli_config(cfg)


def test_non_strict_emits_mismatch_warning(tmp_path: Path) -> None:
    s2 = tmp_path / "s2.json"
    s2.write_text(
        '{"version":"1.0","students":[{"student_id":"s_002","grade":"Y2","major":"CS","skills":["a"],"interests":["b"],"availability":""}]}',
        encoding="utf-8",
    )
    s3 = tmp_path / "s3.json"
    s3.write_text(
        json.dumps(
            {
                "target_student_id": "alice-other",
                "mentor_candidates": [{"mentor_id": "m_1", "final_score": 0.5, "topic_score": 0.5, "graph_score": 0.0}],
            }
        ),
        encoding="utf-8",
    )
    cfg = {
        "target_student_id": "s_002",
        "skill1_profiles_path": "",
        "skill2_students_path": str(s2),
        "skill2_graph_path": "",
        "skill2_mentors_path": "",
        "mentor_candidates_path": str(s3),
        "skill3_output_path": str(s3),
        "mock_projects_path": str(Path(__file__).resolve().parents[1] / "data" / "mock_projects.json"),
        "mock_mentor_candidates_path": "",
        "strict_target_student": False,
        "allow_target_fallback_with_skill3": False,
        "top_n_projects": 1,
        "top_n_teammates": 1,
        "max_candidate_teammates": 5,
        "fallback_mentor_top_k": 2,
    }
    body = run_pipeline_from_cli_config(cfg)
    assert any(
        isinstance(w, str) and w.startswith("skill3_target_student_id_mismatch")
        for w in body.get("warnings", [])
    )
