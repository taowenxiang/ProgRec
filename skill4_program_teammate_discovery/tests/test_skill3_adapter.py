from __future__ import annotations

import json
from pathlib import Path

from skill.skill3_adapter import (
    load_skill3_mentor_candidates,
    load_mentor_candidates,
    parse_skill3_mentor_json,
    read_skill3_mentor_payload,
)


def test_parse_skill3_cli_envelope() -> None:
    raw = {
        "student_id": "s_001",
        "graph_status": "loaded",
        "mentor_candidates": [
            {
                "mentor_id": "m_010",
                "mentor_name": "Dr. X",
                "topic_score": 0.9,
                "graph_score": 0.5,
                "community_id": "c_1",
                "final_score": 0.77,
                "activity_score": 0.2,
                "centrality_score": 0.4,
                "network_proximity": 0.6,
                "reasons": ["overlap on robotics"],
            }
        ],
    }
    rows, meta = parse_skill3_mentor_json(raw)
    assert meta["skill3_declared_student_id"] == "s_001"
    assert meta["target_student_id"] == "s_001"
    assert meta["graph_status"] == "loaded"
    assert len(rows) == 1
    assert rows[0]["mentor_id"] == "m_010"
    assert rows[0]["final_score"] == 0.77
    assert rows[0]["skill3_rank"] == 1
    assert rows[0]["reasons"] == ["overlap on robotics"]


def test_parse_recommendations_key() -> None:
    raw = {
        "recommendations": [
            {"mentor_id": "m_1", "topic_score": 0.5, "graph_score": 0.5, "final_score": 0.5},
        ]
    }
    rows, _ = parse_skill3_mentor_json(raw)
    assert len(rows) == 1
    assert rows[0]["mentor_id"] == "m_1"


def test_parse_nested_data() -> None:
    raw = {"data": {"candidates": [{"id": "m_2", "final_score": 0.3, "topic_score": 0.3, "graph_score": 0.0}]}}
    rows, _ = parse_skill3_mentor_json(raw)
    assert rows[0]["mentor_id"] == "m_2"


def test_load_skill3_round_trip_tmp(tmp_path: Path) -> None:
    path = tmp_path / "s3.json"
    path.write_text(
        json.dumps(
            {
                "target_student_id": "s_z",
                "mentor_candidates": [{"mentor_id": "m_a", "final_score": 0.12}],
            }
        ),
        encoding="utf-8",
    )
    rows = load_skill3_mentor_candidates(path)
    assert rows is not None
    assert rows[0]["final_score"] == 0.12
    payload = read_skill3_mentor_payload(path)
    assert payload is not None
    assert payload["target_student_id"] == "s_z"


def test_load_mentor_candidates_alias_matches(tmp_path: Path) -> None:
    path = tmp_path / "x.json"
    path.write_text(json.dumps([{"mentor_id": "m_x", "final_score": 0.99}]), encoding="utf-8")
    assert load_mentor_candidates(path) == load_skill3_mentor_candidates(path)


def test_parse_both_student_and_target_ids() -> None:
    raw = {
        "student_id": "alice-1",
        "target_student_id": "alice-1",
        "mentor_candidates": [{"mentor_id": "m_1", "final_score": 0.5, "topic_score": 0.5, "graph_score": 0.5}],
    }
    rows, meta = parse_skill3_mentor_json(raw)
    assert rows
    assert meta.get("skill3_declared_student_id") == "alice-1"
    assert meta.get("skill3_declared_target_student_id") == "alice-1"


def test_singular_reason_string() -> None:
    rows, _ = parse_skill3_mentor_json(
        [{"mentor_id": "m_r", "final_score": 0.1, "topic_score": 0.1, "graph_score": 0.0, "reason": "Good fit."}]
    )
    assert rows[0]["reasons"] == ["Good fit."]
