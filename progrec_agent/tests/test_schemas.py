"""Tests for progrec_agent.schemas."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from progrec_agent.schemas import (
    assert_same_student_id,
    validate_skill3_output,
    validate_skill4_output,
    validate_skill5_output,
    validate_student_profiles,
)

_FIX = Path(__file__).resolve().parent / "fixtures"


class TestSchemas(unittest.TestCase):
    def test_validate_student_profiles_fixture(self) -> None:
        info = validate_student_profiles(_FIX / "student_profiles.json")
        self.assertEqual(info["count"], 2)
        self.assertEqual(info["sample_ids"][0], "alice-test-00001")
        self.assertIn("bob-test-00002", info["all_student_ids"])

    def test_validate_skill3_output_fixture(self) -> None:
        info = validate_skill3_output(_FIX / "skill3_output.json")
        self.assertEqual(info["student_id"], "alice-test-00001")
        self.assertEqual(info["mentor_count"], 1)

    def test_validate_skill4_output_fixture(self) -> None:
        info = validate_skill4_output(_FIX / "skill4_output.json")
        self.assertEqual(info["target_student_id"], "alice-test-00001")
        self.assertEqual(info["mentor_bundle_count"], 1)
        self.assertEqual(info["total_project_recommendations"], 1)
        self.assertEqual(info["total_teammate_recommendations"], 1)

    def test_validate_skill5_output_fixture(self) -> None:
        info = validate_skill5_output(_FIX / "skill5_output.json")
        self.assertEqual(info["total_mentor_candidates"], 1)
        self.assertEqual(info["ranked_projects"], 1)

    def test_assert_same_student_id_ok(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            s3 = base / "s3.json"
            s4 = base / "s4.json"
            s3.write_text(
                json.dumps({"student_id": "alice-test-00001", "mentor_candidates": []}),
                encoding="utf-8",
            )
            s4.write_text(json.dumps({"target_student_id": "alice-test-00001"}), encoding="utf-8")
            assert_same_student_id(s3, s4, "alice-test-00001")

    def test_assert_same_student_id_mismatch(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            s3 = base / "s3.json"
            s4 = base / "s4.json"
            s3.write_text(
                json.dumps({"student_id": "other-id", "mentor_candidates": []}),
                encoding="utf-8",
            )
            s4.write_text(json.dumps({"target_student_id": "other-id"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Student ID mismatch before Skill 5"):
                assert_same_student_id(s3, s4, "alice-test-00001")


if __name__ == "__main__":
    unittest.main()
