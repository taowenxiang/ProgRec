from __future__ import annotations

from pathlib import Path

import pytest

from skill.student_resolution import (
    build_merged_student_index_and_pool,
    resolve_target_student,
)


def test_resolve_ok_when_id_in_skill2(tmp_path: Path) -> None:
    s2 = tmp_path / "s2.json"
    s2.write_text(
        '{"version":"1.0","students":[{"student_id":"s_002","grade":"Year 2","major":"CS","skills":["a"],"interests":["b"],"availability":""}]}',
        encoding="utf-8",
    )
    merged, pool, _ = build_merged_student_index_and_pool(s2, None)
    rt = resolve_target_student(
        requested_id="s_002",
        merged_index=merged,
        candidate_pool=pool,
        strict=False,
        print_samples_to_stderr=False,
    )
    assert rt.resolution == "resolved_ok"
    assert rt.effective_student_id == "s_002"
    assert rt.profile.get("skills") == ["a"]


def test_fallback_when_missing_and_not_strict(tmp_path: Path) -> None:
    s2 = tmp_path / "s2.json"
    s2.write_text(
        '{"version":"1.0","students":[{"student_id":"s_002","grade":"Year 2","major":"CS","skills":["x"],"interests":["y"],"availability":""}]}',
        encoding="utf-8",
    )
    merged, pool, _ = build_merged_student_index_and_pool(s2, None)
    rt = resolve_target_student(
        requested_id="does-not-exist",
        merged_index=merged,
        candidate_pool=pool,
        strict=False,
        print_samples_to_stderr=False,
    )
    assert rt.resolution == "target_student_id_not_found_fallback_to_first_student"
    assert rt.effective_student_id == "s_002"
    assert "target_student_id_not_found_fallback_to_first_student" in rt.warnings[0]


def test_strict_raises(tmp_path: Path) -> None:
    s2 = tmp_path / "s2.json"
    s2.write_text(
        '{"version":"1.0","students":[{"student_id":"s_002","grade":"Year 2","major":"CS","skills":[],"interests":[],"availability":""}]}',
        encoding="utf-8",
    )
    merged, pool, _ = build_merged_student_index_and_pool(s2, None)
    with pytest.raises(ValueError, match="not found"):
        resolve_target_student(
            requested_id="nope",
            merged_index=merged,
            candidate_pool=pool,
            strict=True,
            print_samples_to_stderr=False,
        )


def test_skill1_id_found_when_merged(tmp_path: Path) -> None:
    s1 = tmp_path / "s1.jsonl"
    s1.write_text(
        '{"student_id":"alice-1","grade":"Senior","major":"Bio","skills":["x"],"interests":["y"],"availability":"low"}\n',
        encoding="utf-8",
    )
    s2 = tmp_path / "s2.json"
    s2.write_text(
        '{"version":"1.0","students":[{"student_id":"s_002","grade":"Year 2","major":"CS","skills":["a"],"interests":["b"],"availability":""}]}',
        encoding="utf-8",
    )
    merged, pool, _ = build_merged_student_index_and_pool(s2, s1)
    rt = resolve_target_student(
        requested_id="alice-1",
        merged_index=merged,
        candidate_pool=pool,
        strict=False,
        print_samples_to_stderr=False,
    )
    assert rt.resolution == "resolved_ok"
    assert rt.profile["major"] == "Bio"


def test_skill3_blocks_missing_id_without_allow_flag(tmp_path: Path) -> None:
    s2 = tmp_path / "s2.json"
    s2.write_text(
        '{"version":"1.0","students":[{"student_id":"s_002","grade":"Year 2","major":"CS","skills":[],"interests":[],"availability":""}]}',
        encoding="utf-8",
    )
    merged, pool, _ = build_merged_student_index_and_pool(s2, None)
    with pytest.raises(ValueError, match="--skill3-output"):
        resolve_target_student(
            requested_id="missing-id",
            merged_index=merged,
            candidate_pool=pool,
            strict=False,
            print_samples_to_stderr=False,
            skill3_output_blocks_fallback=True,
            allow_target_fallback_with_skill3=False,
        )


def test_skill3_allows_fallback_when_flag_set(tmp_path: Path) -> None:
    s2 = tmp_path / "s2.json"
    s2.write_text(
        '{"version":"1.0","students":[{"student_id":"s_002","grade":"Year 2","major":"CS","skills":[],"interests":[],"availability":""}]}',
        encoding="utf-8",
    )
    merged, pool, _ = build_merged_student_index_and_pool(s2, None)
    rt = resolve_target_student(
        requested_id="missing-id",
        merged_index=merged,
        candidate_pool=pool,
        strict=False,
        print_samples_to_stderr=False,
        skill3_output_blocks_fallback=True,
        allow_target_fallback_with_skill3=True,
    )
    assert rt.effective_student_id == "s_002"
    assert any("allow_target_fallback_with_skill3" in w for w in rt.warnings)


def test_skill3_requires_explicit_target_when_empty(tmp_path: Path) -> None:
    s2 = tmp_path / "s2.json"
    s2.write_text(
        '{"version":"1.0","students":[{"student_id":"s_002","grade":"Year 2","major":"CS","skills":[],"interests":[],"availability":""}]}',
        encoding="utf-8",
    )
    merged, pool, _ = build_merged_student_index_and_pool(s2, None)
    with pytest.raises(ValueError, match="No --target-student-id"):
        resolve_target_student(
            requested_id="",
            merged_index=merged,
            candidate_pool=pool,
            strict=False,
            print_samples_to_stderr=False,
            skill3_output_blocks_fallback=True,
            allow_target_fallback_with_skill3=False,
        )
