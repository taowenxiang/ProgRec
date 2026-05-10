from pathlib import Path

from sturec_agent.session import AgentSession


def test_session_starts_empty(tmp_path: Path) -> None:
    session = AgentSession(temp_dir=tmp_path)

    assert session.mode is None
    assert session.student_profile is None
    assert session.skill5_result is None
    assert session.has_results is False


def test_session_stores_pipeline_results(tmp_path: Path) -> None:
    session = AgentSession(temp_dir=tmp_path)
    payload = {
        "student_id": "s_002",
        "recommendations": {"mentors": [{"mentor_id": "m_001", "rank": 1}]},
    }

    session.set_student_profile({"student_id": "s_002", "major": "CS"})
    session.set_mode("dataset_mode")
    session.set_results(
        skill3_result={"mentor_candidates": [{"mentor_id": "m_001"}]},
        skill4_result={"mentor_project_teammate_recommendations": []},
        skill5_result=payload,
        temporary_paths=[],
    )

    assert session.mode == "dataset_mode"
    assert session.student_profile["student_id"] == "s_002"
    assert session.skill5_result == payload
    assert session.has_results is True


def test_restart_clears_results_and_temp_files(tmp_path: Path) -> None:
    session = AgentSession(temp_dir=tmp_path)
    temp_file = tmp_path / "skill3.json"
    temp_file.write_text("{}", encoding="utf-8")
    session.set_student_profile({"student_id": "s_002"})
    session.set_mode("dataset_mode")
    session.set_results(
        skill3_result={},
        skill4_result={},
        skill5_result={"student_id": "s_002"},
        temporary_paths=[temp_file],
    )

    session.reset()

    assert session.mode is None
    assert session.student_profile is None
    assert session.skill3_result is None
    assert session.skill4_result is None
    assert session.skill5_result is None
    assert not temp_file.exists()
