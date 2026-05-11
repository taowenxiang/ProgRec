"""Tests for hard student_id alignment before Skill 5."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from progrec_agent.schemas import (
    assert_agent_student_alignment,
    assert_same_student_id,
    get_skill3_student_id,
    get_skill4_student_id,
)


def _write(p: Path, obj: object) -> None:
    p.write_text(json.dumps(obj), encoding="utf-8")


class TestGetSkill3StudentId(unittest.TestCase):
    def test_prefers_student_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s3.json"
            _write(p, {"student_id": "alice", "target_student_id": "bob", "mentor_candidates": []})
            self.assertEqual(get_skill3_student_id(p), "alice")

    def test_falls_back_to_target_student_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s3.json"
            _write(p, {"target_student_id": "carol", "mentor_candidates": []})
            self.assertEqual(get_skill3_student_id(p), "carol")

    def test_raises_when_both_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s3.json"
            _write(p, {"mentor_candidates": []})
            with self.assertRaisesRegex(ValueError, "missing student_id and target_student_id"):
                get_skill3_student_id(p)


class TestGetSkill4StudentId(unittest.TestCase):
    def test_reads_target_student_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s4.json"
            _write(p, {"target_student_id": "dave", "mentor_project_teammate_recommendations": []})
            self.assertEqual(get_skill4_student_id(p), "dave")

    def test_raises_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s4.json"
            _write(p, {"mentor_project_teammate_recommendations": []})
            with self.assertRaisesRegex(ValueError, "missing target_student_id"):
                get_skill4_student_id(p)


class TestAssertAgentStudentAlignment(unittest.TestCase):
    def test_all_match(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            s3 = base / "skill3.json"
            s4 = base / "skill4.json"
            _write(s3, {"student_id": "exp-1", "mentor_candidates": []})
            _write(s4, {"target_student_id": "exp-1", "mentor_project_teammate_recommendations": []})
            assert_agent_student_alignment("exp-1", s3, s4)

    def test_skill3_not_expected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            s3 = base / "skill3.json"
            s4 = base / "skill4.json"
            _write(s3, {"student_id": "wrong-s3", "mentor_candidates": []})
            _write(s4, {"target_student_id": "exp-1", "mentor_project_teammate_recommendations": []})
            with self.assertRaisesRegex(ValueError, "Student ID mismatch before Skill 5"):
                assert_agent_student_alignment("exp-1", s3, s4)

    def test_skill4_not_expected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            s3 = base / "skill3.json"
            s4 = base / "skill4.json"
            _write(s3, {"student_id": "exp-1", "mentor_candidates": []})
            _write(s4, {"target_student_id": "wrong-s4", "mentor_project_teammate_recommendations": []})
            with self.assertRaisesRegex(ValueError, "Student ID mismatch before Skill 5"):
                assert_agent_student_alignment("exp-1", s3, s4)

    def test_skill3_and_skill4_inconsistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            s3 = base / "skill3.json"
            s4 = base / "skill4.json"
            _write(s3, {"student_id": "alice", "mentor_candidates": []})
            _write(s4, {"target_student_id": "bob", "mentor_project_teammate_recommendations": []})
            with self.assertRaisesRegex(ValueError, "Student ID mismatch before Skill 5"):
                assert_agent_student_alignment("alice", s3, s4)

    def test_raises_when_skill3_path_none(self) -> None:
        with self.assertRaisesRegex(ValueError, "skill3_path is required"):
            assert_agent_student_alignment("x", None, Path("/tmp/x.json"))

    def test_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            s3 = base / "skill3.json"
            s4 = base / "skill4.json"
            s3.write_text("{not json", encoding="utf-8")
            _write(s4, {"target_student_id": "exp-1", "mentor_project_teammate_recommendations": []})
            with self.assertRaisesRegex(ValueError, "Invalid JSON"):
                assert_agent_student_alignment("exp-1", s3, s4)

    def test_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            s3 = base / "missing.json"
            s4 = base / "skill4.json"
            _write(s4, {"target_student_id": "exp-1", "mentor_project_teammate_recommendations": []})
            with self.assertRaisesRegex(FileNotFoundError, "Not found"):
                assert_agent_student_alignment("exp-1", s3, s4)


class TestAssertSameStudentIdDelegates(unittest.TestCase):
    def test_delegates_to_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            s3 = base / "s3.json"
            s4 = base / "s4.json"
            _write(s3, {"student_id": "u1", "mentor_candidates": []})
            _write(s4, {"target_student_id": "u1", "mentor_project_teammate_recommendations": []})
            assert_same_student_id(s3, s4, "u1")
