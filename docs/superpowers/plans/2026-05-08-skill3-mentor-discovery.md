# Skill 3 Mentor Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Skill 3 baseline that loads Skill 1/2 handoff data, rebuilds the graph when needed, retrieves mentor candidates for a student profile, computes graph-aware features, and returns ranked, explainable mentor recommendations.

**Architecture:** Implement a small Python package with clear modules for loading resources, computing lexical/topic relevance, extracting mentor-network features, producing explanations, and running offline evaluation. Keep the baseline dependency-light by using the Python standard library for retrieval logic, while reusing Skill 2's regenerate kit for graph reconstruction when the complete graph is missing.

**Tech Stack:** Python 3.13, `unittest`, standard library (`json`, `math`, `subprocess`, `pathlib`, `heapq`, `collections`), optional Skill 2 dependencies (`networkx`, `numpy`) only when invoking the regenerate kit.

---

### Task 1: Scaffold the Skill 3 package and CLI entrypoint

**Files:**
- Create: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/__init__.py`
- Create: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/models.py`
- Create: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/run_skill3.py`
- Test: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_cli.py`

- [ ] **Step 1: Write the failing CLI smoke test**

```python
import json
import subprocess
import sys
import unittest
from pathlib import Path


class Skill3CliTest(unittest.TestCase):
    def test_cli_prints_ranked_candidates_for_sample_student(self):
        repo_root = Path(__file__).resolve().parents[1]
        cmd = [
            sys.executable,
            str(repo_root / "skill3_mentor_discovery" / "run_skill3.py"),
            "--student-id",
            "s_001",
            "--top-k",
            "3",
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(len(payload["mentor_candidates"]), 3)
        self.assertIn("mentor_id", payload["mentor_candidates"][0])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_skill3_cli -v`

Expected: FAIL because `skill3_mentor_discovery/run_skill3.py` does not exist yet.

- [ ] **Step 3: Add the minimal package shell**

```python
# __init__.py
"""Skill 3 mentor discovery package."""
```

```python
# models.py
from dataclasses import dataclass


@dataclass
class MentorCandidate:
    mentor_id: str
    topic_score: float
    graph_score: float
    community_id: str
    final_score: float
```

```python
# run_skill3.py
import json


if __name__ == "__main__":
    print(json.dumps({"mentor_candidates": []}))
```

- [ ] **Step 4: Run the test to verify the failure becomes more specific**

Run: `python3 -m unittest tests.test_skill3_cli -v`

Expected: FAIL because the placeholder output does not contain 3 candidates.

- [ ] **Step 5: Commit checkpoint**

If this becomes a git repo later, use:

```bash
git add skill3_mentor_discovery tests
git commit -m "test: scaffold skill3 package and cli smoke test"
```

---

### Task 2: Implement resource loading and graph rebuild fallback

**Files:**
- Create: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/loaders.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/run_skill3.py`
- Test: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_loaders.py`

- [ ] **Step 1: Write the failing resource-resolution test**

```python
import tempfile
import unittest
from pathlib import Path

from skill3_mentor_discovery.loaders import resolve_resource_paths


class LoaderResolutionTest(unittest.TestCase):
    def test_prefers_existing_outputs_without_rebuild(self):
        repo_root = Path(__file__).resolve().parents[1]
        resolved = resolve_resource_paths(repo_root)
        self.assertTrue(resolved.mentor_profiles_path.is_file())
        self.assertTrue(resolved.student_profiles_path.is_file())
        self.assertEqual(resolved.needs_graph_rebuild, True)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_skill3_loaders -v`

Expected: FAIL because `loaders.py` and `resolve_resource_paths` do not exist yet.

- [ ] **Step 3: Implement minimal resource path resolution**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ResourcePaths:
    mentor_profiles_path: Path
    student_profiles_path: Path
    graph_path: Path
    needs_graph_rebuild: bool


def resolve_resource_paths(repo_root: Path) -> ResourcePaths:
    outputs = repo_root / "skill2_academic_graph_builder" / "outputs"
    graph_path = repo_root / "skill2_academic_graph_builder" / "regenerate_kit" / "data" / "processed" / "academic_graph.json"
    return ResourcePaths(
        mentor_profiles_path=outputs / "mentor_profiles_standard.json",
        student_profiles_path=outputs / "student_profiles_standard.json",
        graph_path=graph_path,
        needs_graph_rebuild=not graph_path.is_file(),
    )
```

- [ ] **Step 4: Add rebuild helper and wire the CLI to call it only when needed**

```python
import subprocess


def ensure_graph_available(repo_root: Path, resources: ResourcePaths) -> Path:
    if resources.graph_path.is_file():
        return resources.graph_path
    kit_root = repo_root / "skill2_academic_graph_builder" / "regenerate_kit"
    subprocess.run(
        ["python3", "scripts/build_graph.py"],
        cwd=kit_root,
        check=True,
    )
    return resources.graph_path
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_skill3_loaders -v`

Expected: PASS

---

### Task 3: Implement profile normalization and topic-first retrieval

**Files:**
- Create: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/profile_utils.py`
- Create: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/retrieval.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/run_skill3.py`
- Test: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_retrieval.py`

- [ ] **Step 1: Write the failing retrieval test**

```python
import unittest
from pathlib import Path

from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.retrieval import rank_mentors_for_student


class RetrievalTest(unittest.TestCase):
    def test_returns_ranked_topic_candidates(self):
        repo_root = Path(__file__).resolve().parents[1]
        resources = load_standardized_resources(repo_root)
        result = rank_mentors_for_student(resources.students[0], resources.mentors, top_k=5)
        self.assertEqual(len(result), 5)
        self.assertGreaterEqual(result[0].topic_score, result[-1].topic_score)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_skill3_retrieval -v`

Expected: FAIL because resource loading and ranking helpers are missing.

- [ ] **Step 3: Implement normalized token extraction**

```python
import re


TOKEN_RE = re.compile(r"[a-z0-9\+\#]+")


def normalize_terms(values):
    text = " ".join(v.lower() for v in values if v)
    return TOKEN_RE.findall(text)
```

- [ ] **Step 4: Implement baseline ranking**

```python
from collections import Counter
from math import sqrt


def cosine_counter(a: Counter, b: Counter) -> float:
    numer = sum(a[t] * b[t] for t in set(a) & set(b))
    denom = sqrt(sum(v * v for v in a.values())) * sqrt(sum(v * v for v in b.values()))
    return 0.0 if denom == 0 else numer / denom
```

Use the student's `major`, `skills`, `interests`, and `experience_summary` to build a token counter.  
Use each mentor's `research_areas`, `keywords`, `required_skills`, and `profile_text_for_embedding` to build a token counter.  
Set `topic_score` from the cosine similarity and simple overlap bonuses.

- [ ] **Step 5: Run the retrieval tests**

Run: `python3 -m unittest tests.test_skill3_retrieval -v`

Expected: PASS

---

### Task 4: Add mentor graph features, final scoring, and explanations

**Files:**
- Create: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/graph_features.py`
- Create: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/explanations.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/retrieval.py`
- Test: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_graph_features.py`

- [ ] **Step 1: Write the failing graph-feature test**

```python
import unittest
from pathlib import Path

from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.retrieval import rank_mentors_for_student


class GraphFeatureTest(unittest.TestCase):
    def test_ranked_candidates_include_graph_fields_and_reasons(self):
        repo_root = Path(__file__).resolve().parents[1]
        resources = load_standardized_resources(repo_root)
        ranked = rank_mentors_for_student(resources.students[0], resources.mentors, resources.graph, top_k=3)
        first = ranked[0]
        self.assertIn("community_", first.community_id)
        self.assertGreaterEqual(first.final_score, 0.0)
        self.assertGreaterEqual(len(first.reasons), 1)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_skill3_graph_features -v`

Expected: FAIL because graph enrichment and explanations are not implemented yet.

- [ ] **Step 3: Implement mentor graph feature extraction**

Implement:

- mentor adjacency from `collaboration` and `topic_similarity`
- connected-component-based `community_id` baseline
- normalized degree centrality
- activity score from `h_index`, authored paper count, and project count

Use connected components as the minimal fallback if a more advanced community method is unavailable.

- [ ] **Step 4: Implement final scoring and explanations**

Use:

```text
final_score = 0.60 * topic_score + 0.25 * graph_score + 0.15 * activity_score
```

Generate short explanation strings from:

- topical overlap
- community or centrality evidence
- activity evidence

- [ ] **Step 5: Run the graph feature tests**

Run: `python3 -m unittest tests.test_skill3_graph_features -v`

Expected: PASS

---

### Task 5: Add offline evaluation and finish the CLI flow

**Files:**
- Create: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/evaluate.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/run_skill3.py`
- Modify: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_cli.py`
- Test: `/Users/mount/Desktop/Programming/ProgRec/tests/test_skill3_evaluate.py`

- [ ] **Step 1: Write the failing evaluation test**

```python
import unittest
from pathlib import Path

from skill3_mentor_discovery.evaluate import evaluate_recall_at_k


class EvaluateTest(unittest.TestCase):
    def test_recall_metric_returns_expected_keys(self):
        repo_root = Path(__file__).resolve().parents[1]
        summary = evaluate_recall_at_k(repo_root, top_k=5, sample_size=5)
        self.assertIn("recall_at_k", summary)
        self.assertIn("evaluated_students", summary)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_skill3_evaluate -v`

Expected: FAIL because `evaluate.py` does not exist yet.

- [ ] **Step 3: Implement weak-label evaluation**

Use a simple weak label:

- a mentor is counted as a hit if at least one mentor `research_area` or `keyword` overlaps with the student's interests or skills

Return:

```python
{
    "recall_at_k": 0.0,
    "evaluated_students": 0,
    "students_with_hits": 0,
}
```

- [ ] **Step 4: Finalize CLI output**

Make `run_skill3.py` support:

- `--student-id`
- `--top-k`
- `--json-indent`

and print:

```json
{
  "student_id": "...",
  "mentor_candidates": [...]
}
```

- [ ] **Step 5: Run the focused test suite**

Run: `python3 -m unittest discover -s tests -v`

Expected: PASS for all Skill 3 tests.

---

### Task 6: Manual verification against real handoff data

**Files:**
- Modify: `/Users/mount/Desktop/Programming/ProgRec/skill3_mentor_discovery/run_skill3.py`
- Verify: `/Users/mount/Desktop/Programming/ProgRec/skill2_academic_graph_builder/outputs/mentor_profiles_standard.json`
- Verify: `/Users/mount/Desktop/Programming/ProgRec/skill2_academic_graph_builder/outputs/student_profiles_standard.json`

- [ ] **Step 1: Run the real CLI flow for one seed student**

Run:

```bash
python3 skill3_mentor_discovery/run_skill3.py --student-id s_001 --top-k 5
```

Expected: JSON output with 5 ranked mentor candidates.

- [ ] **Step 2: Run the evaluation command**

Run:

```bash
python3 -m skill3_mentor_discovery.evaluate
```

Expected: JSON summary with `recall_at_k` and student counts.

- [ ] **Step 3: Inspect explanation quality**

Check that at least the top candidate includes:

- one topic-fit reason
- one graph/activity reason

- [ ] **Step 4: Record known limitations in code comments or module docstrings**

Document:

- graph rebuild depends on Skill 2 runtime dependencies
- current recall metric uses weak labels
- student-to-mentor proximity is conservative when graph links are sparse

- [ ] **Step 5: Commit checkpoint**

If this becomes a git repo later, use:

```bash
git add skill3_mentor_discovery tests docs/superpowers
git commit -m "feat: implement skill3 mentor discovery baseline"
```
