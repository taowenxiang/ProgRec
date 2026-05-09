import unittest
from pathlib import Path
import json
import tempfile

from skill3_mentor_discovery.loaders import (
    load_standardized_resources,
    rebuild_commands,
    resolve_resource_paths,
)
from skill3_mentor_discovery.graph_features import prepare_graph_for_ranking


class LoaderResolutionTest(unittest.TestCase):
    def test_resolves_standardized_output_paths(self):
        repo_root = Path(__file__).resolve().parents[1]
        resolved = resolve_resource_paths(repo_root)
        self.assertTrue(resolved.mentor_profiles_path.is_file())
        self.assertTrue(resolved.student_profiles_path.is_file())
        self.assertEqual(
            resolved.needs_graph_rebuild,
            not resolved.outputs_graph_path.is_file() and not resolved.graph_path.is_file(),
        )

    def test_rebuild_commands_include_seed_generation_when_missing(self):
        repo_root = Path(__file__).resolve().parents[1]
        kit_root = repo_root / "skill2_handoff" / "regenerate_kit"
        commands = rebuild_commands(kit_root)
        self.assertEqual(commands[-1], ["python3", "scripts/build_graph.py"])
        if not (kit_root / "data" / "seeds").is_dir():
            self.assertEqual(commands[0], ["python3", "scripts/generate_mentor_pool.py"])

    def test_loading_resources_tolerates_invalid_graph_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "skill2_handoff" / "outputs"
            processed = root / "skill2_handoff" / "regenerate_kit" / "data" / "processed"
            outputs.mkdir(parents=True)
            processed.mkdir(parents=True)
            (outputs / "mentor_profiles_standard.json").write_text(
                json.dumps({"mentors": [{"mentor_id": "m_1", "name": "A"}]}),
                encoding="utf-8",
            )
            (outputs / "student_profiles_standard.json").write_text(
                json.dumps({"students": [{"student_id": "s_1", "skills": [], "interests": []}]}),
                encoding="utf-8",
            )
            (processed / "academic_graph.json").write_text('{"broken": ', encoding="utf-8")
            resources = load_standardized_resources(root)
            self.assertIsNone(resources.graph)

    def test_loading_resources_uses_valid_fallback_graph_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "skill2_handoff" / "outputs"
            processed = root / "skill2_handoff" / "regenerate_kit" / "data" / "processed"
            outputs.mkdir(parents=True)
            processed.mkdir(parents=True)
            (outputs / "mentor_profiles_standard.json").write_text(
                json.dumps({"mentors": [{"mentor_id": "m_1", "name": "A"}]}),
                encoding="utf-8",
            )
            (outputs / "student_profiles_standard.json").write_text(
                json.dumps({"students": [{"student_id": "s_1", "skills": [], "interests": []}]}),
                encoding="utf-8",
            )
            (processed / "academic_graph.json").write_text('{"broken": ', encoding="utf-8")
            (processed / "academic_graph_small.json").write_text(
                json.dumps({"nodes": {"mentor": [], "student": []}, "edges": []}),
                encoding="utf-8",
            )
            resources = load_standardized_resources(root)
            self.assertEqual(resources.graph, {"nodes": {"mentor": [], "student": []}, "edges": []})

    def test_loading_resources_prefers_outputs_graph_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "skill2_handoff" / "outputs"
            processed = root / "skill2_handoff" / "regenerate_kit" / "data" / "processed"
            outputs.mkdir(parents=True)
            processed.mkdir(parents=True)
            (outputs / "mentor_profiles_standard.json").write_text(
                json.dumps({"mentors": [{"mentor_id": "m_1", "name": "A"}]}),
                encoding="utf-8",
            )
            (outputs / "student_profiles_standard.json").write_text(
                json.dumps({"students": [{"student_id": "s_1", "skills": [], "interests": []}]}),
                encoding="utf-8",
            )
            (outputs / "academic_graph.json").write_text(
                json.dumps({"nodes": {"mentor": [{"mentor_id": "m_1"}]}, "edges": []}),
                encoding="utf-8",
            )
            (processed / "academic_graph.json").write_text(
                json.dumps({"nodes": {"mentor": [{"mentor_id": "m_2"}]}, "edges": []}),
                encoding="utf-8",
            )
            resources = load_standardized_resources(root)
            self.assertEqual(resources.graph["nodes"]["mentor"][0]["mentor_id"], "m_1")

    def test_prepare_graph_for_ranking_switches_to_lightweight_mode(self):
        graph = {
            "nodes": {"mentor": [{"mentor_id": "m_1"}, {"mentor_id": "m_2"}]},
            "edges": [
                {
                    "type": "collaboration",
                    "source": {"type": "mentor", "id": "m_1"},
                    "target": {"type": "mentor", "id": "m_2"},
                    "weight": 1.0,
                    "metadata": {},
                },
                {
                    "type": "authored",
                    "source": {"type": "mentor", "id": "m_1"},
                    "target": {"type": "paper", "id": "p_1"},
                    "weight": 1.0,
                    "metadata": {},
                },
                {
                    "type": "skill_complementarity",
                    "source": {"type": "student", "id": "s_1"},
                    "target": {"type": "student", "id": "s_2"},
                    "weight": 0.8,
                    "metadata": {},
                },
            ],
        }
        prepared_graph, graph_status, graph_notice = prepare_graph_for_ranking(
            graph,
            max_full_graph_edges=2,
        )
        self.assertEqual(graph_status, "loaded_lightweight_mentor_subgraph")
        self.assertIn("switched", graph_notice.lower())
        self.assertEqual(len(prepared_graph["edges"]), 2)
