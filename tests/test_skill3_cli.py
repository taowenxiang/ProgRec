import json
import subprocess
import sys
import unittest
from pathlib import Path


class Skill3CliTest(unittest.TestCase):
    def test_cli_prints_ranked_candidates_for_sample_student(self):
        repo_root = Path(__file__).resolve().parents[1]
        student_id = "jamie-taylor-00008"
        cmd = [
            sys.executable,
            str(repo_root / "skill3_mentor_discovery" / "run_skill3.py"),
            "--student-id",
            student_id,
            "--top-k",
            "3",
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(len(payload["mentor_candidates"]), 3)
        self.assertIn("graph_status", payload)
        first_candidate = payload["mentor_candidates"][0]
        self.assertIn("mentor_id", first_candidate)
        self.assertIn("personalized_proximity", first_candidate)
        self.assertIn("graph_confidence", first_candidate)
        self.assertIn("mentor_authority", first_candidate)
        self.assertIn("meta_path_breakdown", first_candidate)
        self.assertIn("top_evidence_paths", first_candidate)
        if payload["graph_status"] == "loaded_lightweight_mentor_subgraph":
            self.assertIn("graph_notice", payload)
            self.assertIn("switched", payload["graph_notice"].lower())
            self.assertTrue(
                any(
                    candidate["personalized_proximity"] > 0.0
                    or candidate["top_evidence_paths"]
                    for candidate in payload["mentor_candidates"]
                ),
                payload["mentor_candidates"],
            )
