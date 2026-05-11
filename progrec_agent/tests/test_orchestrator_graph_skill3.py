"""Orchestrator wiring: graph mode passes explicit Skill 2 paths into Skill 3."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from progrec_agent.config import ResourceConfig
from progrec_agent.orchestrator import ProgRecOrchestrator


def _write_minimal_student_bundle(path: Path, student_id: str = "s1") -> None:
    path.write_text(
        json.dumps(
            {
                "students": [
                    {
                        "student_id": student_id,
                        "grade": "Senior",
                        "major": "CS",
                        "skills": [],
                        "interests": [],
                        "experience_summary": "",
                        "availability": "high",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _write_minimal_mentor_bundle(path: Path) -> None:
    path.write_text(json.dumps({"mentors": [{"mentor_id": "m_1", "name": "A"}]}), encoding="utf-8")


def _write_minimal_graph(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "nodes": {"project": [{"id": "p1"}], "mentor": [], "student": []},
                "edges": [
                    {
                        "type": "project_leads",
                        "source": {"type": "mentor", "id": "m_1"},
                        "target": {"type": "project", "id": "p1"},
                        "weight": 1.0,
                        "metadata": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


class TestOrchestratorGraphSkill3(unittest.TestCase):
    @patch("progrec_agent.orchestrator.run_skill4_dataset_mode")
    @patch("progrec_agent.orchestrator.run_skill3")
    def test_graph_bundle_passes_explicit_skill2_paths(
        self, mock_skill3: MagicMock, mock_skill4: MagicMock
    ) -> None:
        mock_skill3.return_value = {
            "student_id": "s1",
            "mentor_candidates": [],
            "data_sources": {
                "resource_mode": "explicit",
                "student_profiles": "",
                "mentor_profiles": "",
                "academic_graph": "",
            },
        }
        mock_skill4.return_value = {"target_student_id": "s1", "mentor_project_teammate_recommendations": []}

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            (root / "skill1_handoff").mkdir(parents=True)
            proc = root / "skill2_handoff" / "regenerate_kit" / "data" / "processed"
            proc.mkdir(parents=True)
            sp = proc / "student_profiles_standard.json"
            mp = proc / "mentor_profiles_standard.json"
            gp = proc / "academic_graph.json"
            _write_minimal_student_bundle(sp)
            _write_minimal_mentor_bundle(mp)
            _write_minimal_graph(gp)

            bundle = ResourceConfig(
                mode="graph",
                skill2_graph=gp,
                skill2_students=sp,
                skill2_mentors=mp,
                skill1_profiles=None,
                mock_graph=None,
                default_student_id="s1",
            )
            work = Path(td) / "work"
            work.mkdir()
            orch = ProgRecOrchestrator(repo_root=root, temp_dir=work)
            orch.recommend_for_student_id("s1", top_k=3, bundle=bundle, skip_skill5=True)

        mock_skill3.assert_called_once()
        ca = mock_skill3.call_args
        self.assertEqual(ca.kwargs.get("skill2_graph"), gp)
        self.assertEqual(ca.kwargs.get("skill2_students"), sp)
        self.assertEqual(ca.kwargs.get("skill2_mentors"), mp)

    @patch("progrec_agent.orchestrator.run_skill4_dataset_mode")
    @patch("progrec_agent.orchestrator.run_skill3")
    def test_demo_bundle_does_not_pass_explicit_skill2_paths(
        self, mock_skill3: MagicMock, mock_skill4: MagicMock
    ) -> None:
        mock_skill3.return_value = {"student_id": "s1", "mentor_candidates": [], "data_sources": {}}
        mock_skill4.return_value = {"target_student_id": "s1", "mentor_project_teammate_recommendations": []}

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            (root / "skill1_handoff").mkdir(parents=True)
            out = root / "skill2_handoff" / "outputs"
            out.mkdir(parents=True)
            sp = out / "student_profiles_standard.json"
            mp = out / "mentor_profiles_standard.json"
            _write_minimal_student_bundle(sp)
            _write_minimal_mentor_bundle(mp)
            mock_g = out / "mock_academic_graph.json"
            mock_g.write_text("{}", encoding="utf-8")

            bundle = ResourceConfig(
                mode="demo",
                skill2_graph=mock_g,
                skill2_students=sp,
                skill2_mentors=mp,
                skill1_profiles=None,
                mock_graph=mock_g,
                default_student_id="s1",
            )
            work = Path(td) / "work"
            work.mkdir()
            orch = ProgRecOrchestrator(repo_root=root, temp_dir=work)
            orch.recommend_for_student_id("s1", top_k=2, bundle=bundle, skip_skill5=True)

        mock_skill3.assert_called_once()
        self.assertNotIn("skill2_graph", mock_skill3.call_args.kwargs)
        self.assertNotIn("skill2_students", mock_skill3.call_args.kwargs)
        self.assertNotIn("skill2_mentors", mock_skill3.call_args.kwargs)
