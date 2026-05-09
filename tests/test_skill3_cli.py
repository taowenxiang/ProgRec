import json
import subprocess
import sys
import unittest
from pathlib import Path


class Skill3CliTest(unittest.TestCase):
    def test_cli_prints_ranked_candidates_for_sample_student(self):
        repo_root = Path(__file__).resolve().parents[1]
        student_bundle = json.loads(
            (repo_root / "skill2_handoff" / "outputs" / "student_profiles_standard.json").read_text()
        )
        student_id = student_bundle["students"][0]["student_id"]
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
        self.assertIn("mentor_id", payload["mentor_candidates"][0])
        if payload["graph_status"] == "loaded_lightweight_mentor_subgraph":
            self.assertIn("graph_notice", payload)
            self.assertIn("switched", payload["graph_notice"].lower())
