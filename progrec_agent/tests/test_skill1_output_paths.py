from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from progrec_agent.adapters.skill4_adapter import run_skill4_dataset_mode
from progrec_agent.adapters.skill5_adapter import run_skill5


class TestSkill1OutputPaths(unittest.TestCase):
    @patch("progrec_agent.adapters.skill4_adapter.run_pipeline_from_cli_config")
    def test_skill4_dataset_mode_uses_skill1_outputs_directory(self, mock_run_pipeline) -> None:
        mock_run_pipeline.return_value = {"ok": True}
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            (repo_root / "skill1_student_profiling" / "outputs").mkdir(parents=True)
            (repo_root / "skill4_program_teammate_discovery" / "data").mkdir(parents=True)
            (repo_root / "skill4_program_teammate_discovery" / "data" / "mock_projects.json").write_text(
                "[]", encoding="utf-8"
            )
            (repo_root / "skill4_program_teammate_discovery" / "data" / "mock_mentor_candidates.json").write_text(
                "[]", encoding="utf-8"
            )
            skill3_path = repo_root / "skill3.json"
            skill3_path.write_text("{}", encoding="utf-8")
            output_path = repo_root / "skill4.json"

            run_skill4_dataset_mode(
                repo_root=repo_root,
                student_id="s1",
                skill3_path=skill3_path,
                output_path=output_path,
                bundle=None,
            )

        cfg = mock_run_pipeline.call_args.args[0]
        self.assertEqual(
            cfg["skill1_profiles_path"],
            str(repo_root / "skill1_student_profiling" / "outputs" / "student_profiles_normalized.jsonl"),
        )

    @patch("progrec_agent.adapters.skill5_adapter.subprocess.run")
    def test_skill5_uses_skill1_outputs_directory(self, mock_run) -> None:
        mock_run.return_value = None
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            (repo_root / "skill1_student_profiling" / "outputs").mkdir(parents=True)
            (repo_root / "skill5_student_recommendation_ranker" / "scripts").mkdir(parents=True)
            (repo_root / "skill5_student_recommendation_ranker" / "scripts" / "joint_ranker.py").write_text(
                "", encoding="utf-8"
            )
            skill3_path = repo_root / "skill3.json"
            skill4_path = repo_root / "skill4.json"
            output_path = repo_root / "result.json"
            output_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
            skill3_path.write_text("{}", encoding="utf-8")
            skill4_path.write_text("{}", encoding="utf-8")

            run_skill5(
                repo_root=repo_root,
                skill3_path=skill3_path,
                skill4_path=skill4_path,
                output_path=output_path,
                student_id="s1",
                top_k=5,
            )

        cmd = mock_run.call_args.args[0]
        self.assertIn(
            str(repo_root / "skill1_student_profiling" / "outputs" / "student_profiles_normalized.jsonl"),
            cmd,
        )


if __name__ == "__main__":
    unittest.main()
