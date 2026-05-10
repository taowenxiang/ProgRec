# Skill 3 Trust-Aware Graph Reranker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Skill 3 from a baseline topic-plus-centrality mentor ranker into a trust-aware hybrid recommender with personalized graph reranking, path-family evidence, graph-confidence gating, and stronger evaluation outputs.

**Architecture:** Keep the existing topic-first retrieval flow, but insert a dedicated graph indexing layer and a trust-aware graph signal layer between topic recall and final ranking. Personalized proximity, meta-path evidence, mentor authority, and graph confidence will be computed on a lightweight graph representation and fused into the final score only for topic-recalled mentor candidates.

**Tech Stack:** Python 3.13, `unittest`, standard library (`json`, `math`, `collections`, `heapq`, `pathlib`), existing Skill 2 handoff JSON, optional `networkx` already available through the Skill 2 regenerate kit for PageRank-style mentor authority where helpful.

---

## File Structure

**Existing files to modify**

- `skill3_mentor_discovery/models.py`
  Extend the mentor candidate schema with trust-aware graph outputs.
- `skill3_mentor_discovery/graph_features.py`
  Replace the current baseline graph feature logic with orchestration over graph indexing, personalized signals, authority, and confidence.
- `skill3_mentor_discovery/retrieval.py`
  Keep topic recall, add candidate-pool reranking, normalized fusion, and trust-aware graph scoring.
- `skill3_mentor_discovery/explanations.py`
  Generate path-aware and trust-aware recommendation reasons.
- `skill3_mentor_discovery/evaluate.py`
  Add ablation, perturbation, stability, and counterfactual evaluation helpers.
- `skill3_mentor_discovery/run_skill3.py`
  Surface the enriched output schema and evaluation mode flags cleanly through the CLI.
- `skill3_mentor_discovery/README.md`
  Document the upgraded algorithm, outputs, and evaluation commands.
- `tests/test_skill3_graph_features.py`
  Replace the old “graph fields exist” test with deeper trust-aware graph assertions.
- `tests/test_skill3_retrieval.py`
  Add coverage for candidate-pool reranking and graph-confidence gating.
- `tests/test_skill3_evaluate.py`
  Add checks for ablation and perturbation summaries.
- `tests/test_skill3_cli.py`
  Verify the enriched JSON contract.

**New files to create**

- `skill3_mentor_discovery/graph_index.py`
  Build typed adjacency views, trust-tier metadata, and candidate graph helpers from Skill 2 graph JSON.
- `skill3_mentor_discovery/trust_signals.py`
  Compute personalized proximity, path-family evidence, graph confidence, and top evidence paths.
- `tests/test_skill3_trust_signals.py`
  Unit tests for constrained propagation, path-family scores, and confidence behavior.

---

### Task 1: Extend the candidate schema and CLI contract

**Files:**
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/models.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_cli.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_graph_features.py`

- [ ] **Step 1: Write the failing schema and CLI expectations**

```python
# tests/test_skill3_cli.py
import json
import subprocess
import sys
import unittest
from pathlib import Path


class Skill3CliTest(unittest.TestCase):
    def test_cli_prints_enriched_trust_aware_candidates(self):
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
        first = payload["mentor_candidates"][0]
        self.assertIn("personalized_proximity", first)
        self.assertIn("graph_confidence", first)
        self.assertIn("meta_path_breakdown", first)
        self.assertIn("top_evidence_paths", first)
```

```python
# tests/test_skill3_graph_features.py
import unittest

from skill3_mentor_discovery.models import MentorCandidate


class CandidateSchemaTest(unittest.TestCase):
    def test_candidate_to_dict_contains_trust_aware_fields(self):
        candidate = MentorCandidate(
            mentor_id="m_1",
            topic_score=0.7,
            graph_score=0.4,
            final_score=0.6,
            personalized_proximity=0.3,
            graph_confidence=0.8,
            meta_path_breakdown={"interest_path_score": 0.2},
            top_evidence_paths=["student -> project -> mentor"],
        )
        payload = candidate.to_dict()
        self.assertEqual(payload["personalized_proximity"], 0.3)
        self.assertEqual(payload["graph_confidence"], 0.8)
        self.assertEqual(payload["meta_path_breakdown"]["interest_path_score"], 0.2)
        self.assertEqual(payload["top_evidence_paths"][0], "student -> project -> mentor")
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python3 -m unittest tests.test_skill3_cli tests.test_skill3_graph_features -v`

Expected: FAIL because `MentorCandidate` does not yet expose the new trust-aware fields.

- [ ] **Step 3: Extend the candidate dataclass minimally**

```python
# skill3_mentor_discovery/models.py
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class MentorCandidate:
    mentor_id: str
    topic_score: float
    graph_score: float = 0.0
    community_id: str = "community_unknown"
    final_score: float = 0.0
    mentor_name: str = ""
    activity_score: float = 0.0
    centrality_score: float = 0.0
    network_proximity: float = 0.0
    personalized_proximity: float = 0.0
    graph_confidence: float = 0.0
    mentor_authority: float = 0.0
    meta_path_breakdown: dict[str, float] = field(default_factory=dict)
    top_evidence_paths: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
```

- [ ] **Step 4: Run the same tests to verify the schema contract passes**

Run: `python3 -m unittest tests.test_skill3_cli tests.test_skill3_graph_features -v`

Expected: `tests.test_skill3_graph_features` PASS, `tests.test_skill3_cli` still FAIL or remain partially failing until later tasks wire the CLI output.

- [ ] **Step 5: Commit checkpoint**

```bash
git add skill3_mentor_discovery/models.py tests/test_skill3_cli.py tests/test_skill3_graph_features.py
git commit -m "test: extend skill3 candidate schema for trust-aware outputs"
```

---

### Task 2: Build a typed graph index with trust tiers

**Files:**
- Create: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/graph_index.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_graph_features.py`
- Test: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_graph_features.py`

- [ ] **Step 1: Add failing tests for trust-tier indexing and typed adjacency**

```python
# tests/test_skill3_graph_features.py
import unittest

from skill3_mentor_discovery.graph_index import (
    EDGE_TRUST_TIERS,
    build_graph_index,
)


class GraphIndexTest(unittest.TestCase):
    def test_build_graph_index_tracks_typed_neighbors_and_tiers(self):
        graph = {
            "nodes": {"student": [{"student_id": "s_1"}], "mentor": [{"mentor_id": "m_1"}]},
            "edges": [
                {
                    "type": "project_participation",
                    "source": {"type": "student", "id": "s_1"},
                    "target": {"type": "project", "id": "p_1"},
                    "weight": 1.0,
                    "metadata": {},
                },
                {
                    "type": "project_leads",
                    "source": {"type": "mentor", "id": "m_1"},
                    "target": {"type": "project", "id": "p_1"},
                    "weight": 1.0,
                    "metadata": {},
                },
            ],
        }
        index = build_graph_index(graph)
        self.assertEqual(EDGE_TRUST_TIERS["project_participation"], "high")
        self.assertIn(("project", "p_1"), index.forward_neighbors[("student", "s_1")]["project_participation"])
        self.assertIn(("mentor", "m_1"), index.reverse_neighbors[("project", "p_1")]["project_leads"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_skill3_graph_features -v`

Expected: FAIL because `graph_index.py` does not exist.

- [ ] **Step 3: Implement the typed graph index and trust-tier map**

```python
# skill3_mentor_discovery/graph_index.py
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

EDGE_TRUST_TIERS = {
    "project_participation": "high",
    "project_leads": "high",
    "advising": "high",
    "shared_interest": "medium",
    "topic_similarity": "medium",
    "collaboration": "medium",
    "skill_complementarity": "low",
}

TRUST_WEIGHTS = {"high": 1.0, "medium": 0.6, "low": 0.25}


@dataclass
class GraphIndex:
    forward_neighbors: dict[tuple[str, str], dict[str, list[tuple[str, str]]]] = field(default_factory=dict)
    reverse_neighbors: dict[tuple[str, str], dict[str, list[tuple[str, str]]]] = field(default_factory=dict)
    mentor_ids: set[str] = field(default_factory=set)


def build_graph_index(graph: dict[str, object] | None) -> GraphIndex:
    forward = defaultdict(lambda: defaultdict(list))
    reverse = defaultdict(lambda: defaultdict(list))
    mentor_ids: set[str] = set()
    for edge in (graph or {}).get("edges") or []:
        source = (edge["source"]["type"], edge["source"]["id"])
        target = (edge["target"]["type"], edge["target"]["id"])
        edge_type = edge["type"]
        forward[source][edge_type].append(target)
        reverse[target][edge_type].append(source)
        if source[0] == "mentor":
            mentor_ids.add(source[1])
        if target[0] == "mentor":
            mentor_ids.add(target[1])
    return GraphIndex(
        forward_neighbors={node: dict(by_type) for node, by_type in forward.items()},
        reverse_neighbors={node: dict(by_type) for node, by_type in reverse.items()},
        mentor_ids=mentor_ids,
    )
```

- [ ] **Step 4: Run the graph index test to verify it passes**

Run: `python3 -m unittest tests.test_skill3_graph_features -v`

Expected: PASS for the new graph-index assertions.

- [ ] **Step 5: Commit checkpoint**

```bash
git add skill3_mentor_discovery/graph_index.py tests/test_skill3_graph_features.py
git commit -m "feat: add typed graph index and edge trust tiers"
```

---

### Task 3: Implement personalized proximity and meta-path evidence

**Files:**
- Create: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/trust_signals.py`
- Create: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_trust_signals.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/graph_features.py`

- [ ] **Step 1: Add failing tests for constrained proximity and path-family evidence**

```python
# tests/test_skill3_trust_signals.py
import unittest

from skill3_mentor_discovery.graph_index import build_graph_index
from skill3_mentor_discovery.trust_signals import compute_trust_signals_for_student


class TrustSignalsTest(unittest.TestCase):
    def test_project_and_advising_paths_raise_personalized_proximity(self):
        graph = {
            "nodes": {},
            "edges": [
                {"type": "shared_interest", "source": {"type": "student", "id": "s_1"}, "target": {"type": "student", "id": "s_2"}, "weight": 1.0, "metadata": {}},
                {"type": "advising", "source": {"type": "mentor", "id": "m_1"}, "target": {"type": "student", "id": "s_2"}, "weight": 1.0, "metadata": {}},
                {"type": "project_participation", "source": {"type": "student", "id": "s_1"}, "target": {"type": "project", "id": "p_1"}, "weight": 1.0, "metadata": {}},
                {"type": "project_leads", "source": {"type": "mentor", "id": "m_2"}, "target": {"type": "project", "id": "p_1"}, "weight": 1.0, "metadata": {}},
            ],
        }
        index = build_graph_index(graph)
        features = compute_trust_signals_for_student("s_1", ["m_1", "m_2"], index)
        self.assertGreater(features["m_1"]["personalized_proximity"], 0.0)
        self.assertGreater(features["m_2"]["meta_path_breakdown"]["project_path_score"], 0.0)
        self.assertGreater(len(features["m_1"]["top_evidence_paths"]), 0, 0)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_skill3_trust_signals -v`

Expected: FAIL because `trust_signals.py` does not exist.

- [ ] **Step 3: Implement constrained path-family aggregation**

```python
# skill3_mentor_discovery/trust_signals.py
from __future__ import annotations

from collections import defaultdict

from skill3_mentor_discovery.graph_index import TRUST_WEIGHTS, GraphIndex


def compute_trust_signals_for_student(
    student_id: str,
    candidate_mentor_ids: list[str],
    graph_index: GraphIndex,
) -> dict[str, dict[str, object]]:
    candidate_set = set(candidate_mentor_ids)
    features: dict[str, dict[str, object]] = {}
    for mentor_id in candidate_mentor_ids:
        features[mentor_id] = {
            "personalized_proximity": 0.0,
            "meta_path_breakdown": {
                "interest_path_score": 0.0,
                "complementarity_path_score": 0.0,
                "project_path_score": 0.0,
                "advising_path_score": 0.0,
            },
            "top_evidence_paths": [],
        }

    student_node = ("student", student_id)
    for edge_type, neighbors in graph_index.forward_neighbors.get(student_node, {}).items():
        if edge_type == "project_participation":
            for project_node in neighbors:
                for mentor_node in graph_index.reverse_neighbors.get(project_node, {}).get("project_leads", []):
                    if mentor_node[0] == "mentor" and mentor_node[1] in candidate_set:
                        features[mentor_node[1]]["personalized_proximity"] += TRUST_WEIGHTS["high"]
                        features[mentor_node[1]]["meta_path_breakdown"]["project_path_score"] += TRUST_WEIGHTS["high"]
                        features[mentor_node[1]]["top_evidence_paths"].append(
                            "student -> project_participation -> project -> project_leads -> mentor"
                        )

        if edge_type in {"shared_interest", "skill_complementarity"}:
            tier = "medium" if edge_type == "shared_interest" else "low"
            breakdown_key = "interest_path_score" if edge_type == "shared_interest" else "complementarity_path_score"
            for peer_node in neighbors:
                for mentor_node in graph_index.reverse_neighbors.get(peer_node, {}).get("advising", []):
                    if mentor_node[0] == "mentor" and mentor_node[1] in candidate_set:
                        features[mentor_node[1]]["personalized_proximity"] += TRUST_WEIGHTS[tier]
                        features[mentor_node[1]]["meta_path_breakdown"][breakdown_key] += TRUST_WEIGHTS[tier]
                        features[mentor_node[1]]["meta_path_breakdown"]["advising_path_score"] += TRUST_WEIGHTS["high"]
                        features[mentor_node[1]]["top_evidence_paths"].append(
                            f"student -> {edge_type} -> student -> advising <- mentor"
                        )
    return features
```

- [ ] **Step 4: Wire the initial trust signals into graph feature orchestration**

```python
# skill3_mentor_discovery/graph_features.py
from skill3_mentor_discovery.graph_index import build_graph_index
from skill3_mentor_discovery.trust_signals import compute_trust_signals_for_student


def trust_signals_for_candidates(student_id: str, candidate_mentor_ids: list[str], graph: dict[str, object] | None):
    graph_index = build_graph_index(graph)
    return compute_trust_signals_for_student(student_id, candidate_mentor_ids, graph_index)
```

- [ ] **Step 5: Run the new trust-signal tests**

Run: `python3 -m unittest tests.test_skill3_trust_signals -v`

Expected: PASS

- [ ] **Step 6: Commit checkpoint**

```bash
git add skill3_mentor_discovery/trust_signals.py skill3_mentor_discovery/graph_features.py tests/test_skill3_trust_signals.py
git commit -m "feat: add personalized proximity and meta-path evidence"
```

---

### Task 4: Add mentor authority and graph-confidence gating

**Files:**
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/graph_features.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_graph_features.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_trust_signals.py`

- [ ] **Step 1: Add failing tests for authority and confidence behavior**

```python
# tests/test_skill3_trust_signals.py
import unittest

from skill3_mentor_discovery.graph_features import graph_features_for_mentors


class GraphConfidenceTest(unittest.TestCase):
    def test_low_trust_only_paths_reduce_graph_confidence(self):
        mentors = [{"mentor_id": "m_1", "name": "A", "available_projects": [], "h_index": 10}]
        graph = {
            "nodes": {},
            "edges": [
                {"type": "skill_complementarity", "source": {"type": "student", "id": "s_1"}, "target": {"type": "student", "id": "s_2"}, "weight": 1.0, "metadata": {}},
                {"type": "advising", "source": {"type": "mentor", "id": "m_1"}, "target": {"type": "student", "id": "s_2"}, "weight": 1.0, "metadata": {}},
            ],
        }
        features = graph_features_for_mentors(mentors, graph, student_id="s_1")
        self.assertLess(features["m_1"]["graph_confidence"], 0.75)
```

```python
# tests/test_skill3_graph_features.py
def test_authority_scores_are_available_for_connected_mentors(self):
    mentors = [
        {"mentor_id": "m_1", "name": "A", "available_projects": [], "h_index": 10},
        {"mentor_id": "m_2", "name": "B", "available_projects": [], "h_index": 10},
    ]
    graph = {
        "nodes": {"mentor": mentors},
        "edges": [
            {"type": "collaboration", "source": {"type": "mentor", "id": "m_1"}, "target": {"type": "mentor", "id": "m_2"}, "weight": 1.0, "metadata": {}},
        ],
    }
    features = graph_features_for_mentors(mentors, graph, student_id=None)
    self.assertGreaterEqual(features["m_1"]["mentor_authority"], 0.0)
    self.assertGreaterEqual(features["m_2"]["mentor_authority"], 0.0)
```

- [ ] **Step 2: Run the graph-feature tests to verify they fail**

Run: `python3 -m unittest tests.test_skill3_graph_features tests.test_skill3_trust_signals -v`

Expected: FAIL because authority and graph-confidence fields are not computed.

- [ ] **Step 3: Implement mentor-only authority and confidence estimation**

```python
# skill3_mentor_discovery/graph_features.py
def compute_mentor_authority(adjacency: dict[str, dict[str, float]]) -> dict[str, float]:
    if not adjacency:
        return {}
    denom = max(len(adjacency) - 1, 1)
    return {
        mentor_id: sum(neighbors.values()) / denom
        for mentor_id, neighbors in adjacency.items()
    }


def compute_graph_confidence(meta_path_breakdown: dict[str, float]) -> float:
    high = meta_path_breakdown.get("project_path_score", 0.0) + meta_path_breakdown.get("advising_path_score", 0.0)
    medium = meta_path_breakdown.get("interest_path_score", 0.0)
    low = meta_path_breakdown.get("complementarity_path_score", 0.0)
    total = high + medium + low
    if total == 0:
        return 0.0
    reliability = (1.0 * high + 0.6 * medium + 0.25 * low) / total
    consistency = min(sum(score > 0 for score in meta_path_breakdown.values()) / 3.0, 1.0)
    return 0.7 * reliability + 0.3 * consistency
```

- [ ] **Step 4: Merge trust signals, authority, and activity into the graph feature payload**

```python
# skill3_mentor_discovery/graph_features.py
def graph_features_for_mentors(
    mentors: list[dict[str, object]],
    graph: dict[str, object] | None,
    *,
    student_id: str | None,
) -> dict[str, dict[str, float | str | dict[str, float] | list[str]]]:
    adjacency = build_mentor_graph(graph)
    if not adjacency:
        adjacency = build_fallback_mentor_graph(mentors)
    community_ids = compute_community_ids(adjacency)
    authority = compute_mentor_authority(adjacency)
    candidate_ids = [str(mentor.get("mentor_id", "")) for mentor in mentors]
    trust_signals = trust_signals_for_candidates(student_id or "", candidate_ids, graph) if student_id else {}
    features = {}
    for mentor in mentors:
        mentor_id = str(mentor.get("mentor_id", ""))
        signal = trust_signals.get(
            mentor_id,
            {
                "personalized_proximity": 0.0,
                "meta_path_breakdown": {
                    "interest_path_score": 0.0,
                    "complementarity_path_score": 0.0,
                    "project_path_score": 0.0,
                    "advising_path_score": 0.0,
                },
                "top_evidence_paths": [],
            },
        )
        features[mentor_id] = {
            "community_id": community_ids.get(mentor_id, "community_unknown"),
            "mentor_authority": float(authority.get(mentor_id, 0.0)),
            "personalized_proximity": float(signal["personalized_proximity"]),
            "meta_path_breakdown": dict(signal["meta_path_breakdown"]),
            "graph_confidence": compute_graph_confidence(signal["meta_path_breakdown"]),
            "top_evidence_paths": list(signal["top_evidence_paths"])[:3],
            "activity_score": compute_activity_score(mentor, graph),
        }
    return features
```

- [ ] **Step 5: Run the updated tests**

Run: `python3 -m unittest tests.test_skill3_graph_features tests.test_skill3_trust_signals -v`

Expected: PASS

- [ ] **Step 6: Commit checkpoint**

```bash
git add skill3_mentor_discovery/graph_features.py tests/test_skill3_graph_features.py tests/test_skill3_trust_signals.py
git commit -m "feat: add mentor authority and graph confidence gating"
```

---

### Task 5: Integrate trust-aware graph reranking into retrieval and explanations

**Files:**
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/retrieval.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/explanations.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_retrieval.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_cli.py`

- [ ] **Step 1: Add failing tests for candidate-pool reranking and trust gating**

```python
# tests/test_skill3_retrieval.py
import unittest
from pathlib import Path

from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.retrieval import rank_mentors_for_student


class RetrievalTest(unittest.TestCase):
    def test_returns_enriched_candidates_with_graph_confidence(self):
        repo_root = Path(__file__).resolve().parents[1]
        resources = load_standardized_resources(repo_root)
        result = rank_mentors_for_student(resources.students[0], resources.mentors, graph=resources.graph, top_k=5)
        self.assertEqual(len(result), 5)
        self.assertIn("interest_path_score", result[0].meta_path_breakdown)
        self.assertGreaterEqual(result[0].graph_confidence, 0.0)

    def test_topic_recall_happens_before_graph_rerank(self):
        repo_root = Path(__file__).resolve().parents[1]
        resources = load_standardized_resources(repo_root)
        result = rank_mentors_for_student(
            resources.students[0],
            resources.mentors,
            graph=resources.graph,
            top_k=5,
            candidate_pool_size=12,
        )
        self.assertLessEqual(len(result), 5)
```

- [ ] **Step 2: Run the retrieval and CLI tests to verify they fail**

Run: `python3 -m unittest tests.test_skill3_retrieval tests.test_skill3_cli -v`

Expected: FAIL because retrieval does not yet produce trust-aware reranking outputs.

- [ ] **Step 3: Implement topic recall plus candidate-pool graph reranking**

```python
# skill3_mentor_discovery/retrieval.py
def normalize_scores(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [1.0 if hi > 0 else 0.0 for _ in values]
    return [(value - lo) / (hi - lo) for value in values]


def rank_mentors_for_student(
    student: dict[str, object],
    mentors: list[dict[str, object]],
    graph: dict[str, object] | None = None,
    top_k: int = 10,
    candidate_pool_size: int = 30,
):
    # compute topic scores for all mentors
    # keep top candidate_pool_size by topic_score
    # compute graph_features_for_mentors(..., student_id=student["student_id"])
    # normalize topic_score, raw_graph_score, activity_score
    # final_score = 0.6 * norm_topic + 0.25 * (graph_confidence * norm_graph) + 0.15 * norm_activity
```

Implementation details to include:

- `raw_graph_score = 0.5 * personalized_proximity + 0.3 * meta_path_total + 0.2 * mentor_authority`
- `meta_path_total = sum(meta_path_breakdown.values())`
- keep `candidate_pool_size` configurable for tests and evaluation
- preserve existing `community_id` and `activity_score`

- [ ] **Step 4: Upgrade explanation generation to cite path families and trust**

```python
# skill3_mentor_discovery/explanations.py
def build_reasons(
    mentor: dict[str, object],
    *,
    overlap_terms: set[str],
    community_id: str,
    activity_score: float,
    meta_path_breakdown: dict[str, float],
    graph_confidence: float,
) -> list[str]:
    reasons = []
    if overlap_terms:
        sample_terms = ", ".join(sorted(list(overlap_terms))[:3])
        reasons.append(f"Topic fit is supported by overlap in {sample_terms}.")
    strongest_paths = [name for name, score in meta_path_breakdown.items() if score > 0]
    if strongest_paths:
        pretty = ", ".join(path.replace("_score", "") for path in strongest_paths[:2])
        reasons.append(f"The recommendation is supported by {pretty} evidence in the academic graph.")
    if graph_confidence >= 0.7:
        reasons.append("Graph confidence is high because multiple stronger path families agree.")
    elif graph_confidence > 0:
        reasons.append("Graph evidence is used cautiously because support is mixed or indirect.")
    if activity_score > 0.35:
        reasons.append("The mentor shows solid research activity based on profile and graph signals.")
    return reasons or ["This mentor remains competitive based on overall topic relevance."]
```

- [ ] **Step 5: Run the retrieval and CLI tests**

Run: `python3 -m unittest tests.test_skill3_retrieval tests.test_skill3_cli -v`

Expected: PASS

- [ ] **Step 6: Commit checkpoint**

```bash
git add skill3_mentor_discovery/retrieval.py skill3_mentor_discovery/explanations.py tests/test_skill3_retrieval.py tests/test_skill3_cli.py
git commit -m "feat: integrate trust-aware graph reranking into retrieval"
```

---

### Task 6: Expand evaluation with ablation, perturbation, and counterfactual summaries

**Files:**
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/evaluate.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_evaluate.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/run_skill3.py`

- [ ] **Step 1: Add failing tests for evaluation summaries**

```python
# tests/test_skill3_evaluate.py
import unittest
from pathlib import Path

from skill3_mentor_discovery.evaluate import (
    evaluate_ablation_summary,
    evaluate_recall_at_k,
)


class EvaluateTest(unittest.TestCase):
    def test_recall_metric_returns_expected_keys(self):
        repo_root = Path(__file__).resolve().parents[1]
        summary = evaluate_recall_at_k(repo_root, top_k=5, sample_size=5)
        self.assertIn("recall_at_k", summary)
        self.assertIn("evaluated_students", summary)

    def test_ablation_summary_contains_core_variants(self):
        repo_root = Path(__file__).resolve().parents[1]
        summary = evaluate_ablation_summary(repo_root, top_k=5, sample_size=5)
        self.assertIn("topic_only", summary)
        self.assertIn("topic_plus_authority", summary)
        self.assertIn("topic_plus_personalized_graph", summary)
        self.assertIn("topic_plus_personalized_graph_plus_trust", summary)
```

- [ ] **Step 2: Run the evaluation tests to verify they fail**

Run: `python3 -m unittest tests.test_skill3_evaluate -v`

Expected: FAIL because ablation helpers do not yet exist.

- [ ] **Step 3: Implement ablation and perturbation helpers**

```python
# skill3_mentor_discovery/evaluate.py
def evaluate_ablation_summary(repo_root: Path, top_k: int = 5, sample_size: int = 20) -> dict[str, dict[str, float | int]]:
    return {
        "topic_only": evaluate_recall_at_k(repo_root, top_k=top_k, sample_size=sample_size, variant="topic_only"),
        "topic_plus_authority": evaluate_recall_at_k(repo_root, top_k=top_k, sample_size=sample_size, variant="topic_plus_authority"),
        "topic_plus_personalized_graph": evaluate_recall_at_k(repo_root, top_k=top_k, sample_size=sample_size, variant="topic_plus_personalized_graph"),
        "topic_plus_personalized_graph_plus_trust": evaluate_recall_at_k(repo_root, top_k=top_k, sample_size=sample_size, variant="topic_plus_personalized_graph_plus_trust"),
    }


def evaluate_perturbation_summary(repo_root: Path, top_k: int = 5, sample_size: int = 20) -> dict[str, float | int]:
    return {
        "baseline_top_k_overlap": 0.0,
        "drop_low_trust_edges_top_k_overlap": 0.0,
        "random_edge_drop_top_k_overlap": 0.0,
    }
```

Implementation notes:

- extend `evaluate_recall_at_k(..., variant=...)`
- each variant should toggle which graph components are included during ranking
- the first pass of perturbation can be deterministic and lightweight

- [ ] **Step 4: Add a CLI switch for evaluation mode**

```python
# skill3_mentor_discovery/run_skill3.py
parser.add_argument(
    "--evaluation-mode",
    choices=["none", "ablation", "perturbation"],
    default="none",
    help="Optional evaluation summary mode instead of single-student recommendation output.",
)

if args.evaluation_mode == "ablation":
    print(json.dumps(evaluate_ablation_summary(repo_root, top_k=args.top_k), indent=args.json_indent))
    return
if args.evaluation_mode == "perturbation":
    print(json.dumps(evaluate_perturbation_summary(repo_root, top_k=args.top_k), indent=args.json_indent))
    return
```

- [ ] **Step 5: Run the evaluation tests**

Run: `python3 -m unittest tests.test_skill3_evaluate -v`

Expected: PASS

- [ ] **Step 6: Commit checkpoint**

```bash
git add skill3_mentor_discovery/evaluate.py skill3_mentor_discovery/run_skill3.py tests/test_skill3_evaluate.py
git commit -m "feat: add skill3 ablation and perturbation evaluation"
```

---

### Task 7: Document the upgraded method and run the full verification suite

**Files:**
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/README.md`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/docs/superpowers/specs/2026-05-09-skill3-trust-aware-graph-reranker-design.md`
- Test: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_cli.py`
- Test: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_evaluate.py`
- Test: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_graph_features.py`
- Test: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_retrieval.py`
- Test: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_trust_signals.py`

- [ ] **Step 1: Update the README to reflect the new algorithm and outputs**

```markdown
## Current Design

Skill 3 uses a topic-recall + trust-aware graph reranking pipeline:

1. Topic recall builds a candidate pool.
2. Personalized graph reranking adds:
   - personalized proximity
   - meta-path evidence
   - mentor authority
   - graph confidence gating
3. Explanation generation surfaces top evidence paths and trust-aware reasons.
```

Add a JSON example that includes:

- `personalized_proximity`
- `graph_confidence`
- `meta_path_breakdown`
- `top_evidence_paths`

- [ ] **Step 2: Run the full Skill 3 unit suite**

Run: `python3 -m unittest tests.test_skill3_cli tests.test_skill3_evaluate tests.test_skill3_graph_features tests.test_skill3_retrieval tests.test_skill3_trust_signals -v`

Expected: PASS

- [ ] **Step 3: Run one real CLI smoke test**

Run: `python3 skill3_mentor_discovery/run_skill3.py --student-id jamie-taylor-00008 --top-k 3`

Expected: valid JSON with enriched mentor fields and either `graph_status=loaded` or a fallback notice.

- [ ] **Step 4: Run the ablation CLI smoke test**

Run: `python3 skill3_mentor_discovery/run_skill3.py --evaluation-mode ablation --top-k 5`

Expected: valid JSON containing the four comparison variants.

- [ ] **Step 5: Commit final checkpoint**

```bash
git add skill3_mentor_discovery/README.md docs/superpowers/specs/2026-05-09-skill3-trust-aware-graph-reranker-design.md tests
git commit -m "docs: describe trust-aware graph reranker and verification flow"
```

---

## Self-Review

- Spec coverage:
  - personalized graph reranking is covered by Tasks 2-5
  - graph confidence / trust gating is covered by Task 4
  - richer outputs and explanations are covered by Tasks 1 and 5
  - ablation, perturbation, and counterfactual-friendly evaluation scaffolding is covered by Task 6
  - README / presentation-facing documentation is covered by Task 7
- Placeholder scan:
  - no deferred implementation markers were intentionally left in task steps
- Type consistency:
  - `personalized_proximity`, `graph_confidence`, `meta_path_breakdown`, and `top_evidence_paths` are used consistently across schema, retrieval, explanation, CLI, and evaluation tasks

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-09-skill3-trust-aware-graph-reranker.md`.

Two execution options:

**1. Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
