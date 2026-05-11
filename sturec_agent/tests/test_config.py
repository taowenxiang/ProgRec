"""Tests for sturec_agent.config."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from sturec_agent.config import resolve_repo_root, resolve_resource_config


def _real_repo() -> Path:
    return Path(__file__).resolve().parents[2]


class TestConfig(unittest.TestCase):
    def test_resolve_repo_root_default(self) -> None:
        root = resolve_repo_root()
        self.assertTrue((root / "skill1_handoff").is_dir())
        self.assertTrue((root / "sturec_agent" / "config.py").is_file())

    def test_resolve_repo_root_explicit(self) -> None:
        root = resolve_repo_root(_real_repo())
        self.assertEqual(root, _real_repo().resolve())

    def test_demo_config_resolves(self) -> None:
        root = _real_repo()
        cfg = resolve_resource_config("demo", root)
        self.assertEqual(cfg.mode, "demo")
        self.assertEqual(cfg.skill2_students.name, "student_profiles_standard.json")
        self.assertIsNotNone(cfg.skill2_graph)
        self.assertEqual(cfg.skill2_graph.name, "mock_academic_graph.json")
        self.assertEqual(cfg.mock_graph, cfg.skill2_graph)

    def test_graph_config_raises_when_graph_missing(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "repo"
            (fake / "skill1_handoff").mkdir(parents=True)
            proc = fake / "skill2_handoff" / "regenerate_kit" / "data" / "processed"
            proc.mkdir(parents=True)
            (proc / "student_profiles_standard.json").write_text(
                json.dumps(
                    {
                        "version": "1",
                        "students": [
                            {
                                "student_id": "x",
                                "grade": "Senior",
                                "major": "CS",
                                "skills": [],
                                "interests": [],
                                "experience_summary": "",
                                "availability": "high",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (proc / "mentor_profiles_standard.json").write_text(
                json.dumps({"version": "1", "mentors": [{"mentor_id": "m_001", "name": "A"}]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FileNotFoundError, "Graph mode requires academic_graph"):
                resolve_resource_config("graph", fake)

    def test_graph_config_raises_when_project_nodes_empty(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "repo2"
            (fake / "skill1_handoff").mkdir(parents=True)
            proc = fake / "skill2_handoff" / "regenerate_kit" / "data" / "processed"
            proc.mkdir(parents=True)
            (proc / "student_profiles_standard.json").write_text(
                json.dumps(
                    {
                        "version": "1",
                        "students": [
                            {
                                "student_id": "x",
                                "grade": "Senior",
                                "major": "CS",
                                "skills": [],
                                "interests": [],
                                "experience_summary": "",
                                "availability": "high",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (proc / "mentor_profiles_standard.json").write_text(
                json.dumps({"version": "1", "mentors": []}),
                encoding="utf-8",
            )
            bad_graph = {"version": "1", "nodes": {"project": [], "mentor": []}, "edges": []}
            (proc / "academic_graph.json").write_text(json.dumps(bad_graph), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no nodes.project entries"):
                resolve_resource_config("graph", fake)

    def test_graph_config_ok_when_bundle_exists(self) -> None:
        root = _real_repo()
        graph = root / "skill2_handoff/regenerate_kit/data/processed/academic_graph.json"
        if not graph.is_file():
            self.skipTest("processed academic_graph.json not present")
        cfg = resolve_resource_config("graph", root)
        self.assertEqual(cfg.mode, "graph")
        self.assertEqual(cfg.skill2_graph, graph)


if __name__ == "__main__":
    unittest.main()
