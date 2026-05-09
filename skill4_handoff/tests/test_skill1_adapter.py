from __future__ import annotations

import json
from pathlib import Path

from skill.skill1_adapter import (
    build_student_index,
    list_available_student_ids,
    load_skill1_profiles,
    normalize_skill1_profile,
    split_target_and_candidates,
)


def test_load_skill1_profiles_skips_blank(tmp_path: Path) -> None:
    p = tmp_path / "p.jsonl"
    p.write_text(
        '{"student_id":"a-1","grade":"Senior","skills":["Python"],"interests":["ML"],"availability":""}\n\nnot-json\n',
        encoding="utf-8",
    )
    rows = load_skill1_profiles(p)
    assert len(rows) == 1
    assert rows[0]["student_id"] == "a-1"


def test_normalize_lowercase_and_defaults() -> None:
    n = normalize_skill1_profile(
        {
            "student_id": "x",
            "skills": ["Python", "python", " DATA "],
            "interests": ["ML", "ml"],
            "availability": "",
            "grade": "",
        }
    )
    assert n["skills"] == ["data", "python"]
    assert n["interests"] == ["ml"]
    assert n["availability"] == "moderate"
    assert n["grade"] == "unknown"


def test_list_available_student_ids() -> None:
    rows = [{"student_id": "c"}, {"student_id": "a"}, {"student_id": "a"}, {"student_id": "b"}]
    assert list_available_student_ids(rows, 2) == ["c", "a"]


def test_split_target_and_candidates() -> None:
    profs = [
        {"student_id": "t", "skills": ["a"], "interests": ["b"], "grade": "Freshman"},
        {"student_id": "o", "skills": ["c"], "interests": ["d"], "grade": "Senior"},
    ]
    t, cands = split_target_and_candidates(profs, "t")
    assert t is not None
    assert t["student_id"] == "t"
    assert len(cands) == 1
    assert cands[0]["student_id"] == "o"
    idx = build_student_index(profs)
    assert len(idx) == 2
