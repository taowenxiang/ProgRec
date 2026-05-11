---
name: mentor-discovery
description: Use when a standardized student profile needs ranked mentor candidates from Skill 2 artifacts, or when debugging Skill 3 CLI path resolution, graph fallback, and mentor-ranking explanations.
---

# Mentor Discovery (Skill 3)

## Overview

Skill 3 ranks mentor candidates for one student.

It owns the mentor stage only:

- Input: one standardized student profile plus Skill 2 student, mentor, and graph artifacts
- Output: JSON with `student_id`, `graph_status`, `data_sources`, and `mentor_candidates[]`
- Downstream consumers: `skill4_handoff`, `progrec_agent`, or manual inspection

The ranking pipeline has two stages:

1. Topic recall from student `major`, `skills`, `interests`, and `experience_summary`
2. Trust-aware graph reranking with mentor authority, personalized proximity, meta-path evidence, graph confidence, and activity

Skill 3 does not recommend projects or teammates, and it does not perform final joint ranking across entity types.

## When to Use

Use Skill 3 when:

- you need mentor candidates for a single `student_id`
- you want a JSON artifact for Skill 4 or the ProgRec agent
- you need to compare default bundle behavior against explicit Skill 2 graph-mode paths
- you are debugging why mentor results changed after a graph rebuild
- you want lightweight offline evaluation for graph-aware reranking

Do not use Skill 3 when:

- you need to regenerate Skill 2 artifacts
- you need project or teammate recommendations
- you need final mentor/project/teammate fusion and reranking

## Inputs

Skill 3 expects one student record in the standardized schema used across Skills 1 and 2:

```json
{
  "student_id": "jamie-taylor-00008",
  "grade": "Junior",
  "major": "Computer Science",
  "skills": ["python", "ml"],
  "interests": ["nlp", "education"],
  "experience_summary": "Built tutoring and data projects.",
  "availability": "10 hours/week"
}
```

By default, Skill 3 resolves:

- `skill2_handoff/outputs/student_profiles_standard.json`
- `skill2_handoff/outputs/mentor_profiles_standard.json`
- graph candidates in this order:
  `skill2_handoff/outputs/academic_graph.json`
  then `skill2_handoff/regenerate_kit/data/processed/academic_graph.json`

You can also pass explicit Skill 2 paths:

- `--skill2-graph`
- `--skill2-students`
- `--skill2-mentors`

If an explicit path is passed, it must exist. Explicit mode does not silently fall back to `outputs/`.

## Ranking Flow

### 1. Topic recall

`retrieval.py` builds token counters for the student and each mentor, then scores:

```text
topic_score = 0.8 * cosine_similarity + 0.2 * term_overlap
```

Skill 3 sorts mentors by topic score, keeps a candidate pool, then enriches only that pool with graph features.

### 2. Graph preparation

`graph_features.prepare_graph_for_ranking()` decides how much graph to keep:

- If no usable graph is available, Skill 3 falls back away from graph ranking
- If the graph has at most `250000` edges, Skill 3 uses it as-is
- If the graph is larger, Skill 3 switches to a lightweight mentor subgraph

The lightweight mode preserves:

- mentor-to-mentor `collaboration` and `topic_similarity`
- mentor-to-project `project_leads`
- mentor-to-paper `authored`
- student-local trust edges relevant to the target student:
  `project_participation`, `shared_interest`, `skill_complementarity`, and linked `advising`

This mode is surfaced through:

- `graph_status: "loaded_lightweight_mentor_subgraph"`
- `graph_notice`

### 3. Trust-aware reranking

For each candidate mentor, Skill 3 combines:

- `mentor_authority`
- `personalized_proximity`
- `meta_path_breakdown`
- `graph_confidence`
- `activity_score`

Trust evidence is aggregated from path families such as:

- project paths
- shared-interest plus advising paths
- skill-complementarity plus advising paths

Current final score:

```text
final_score = 0.60 * normalized_topic
            + 0.25 * confidence_weighted_graph
            + 0.15 * normalized_activity
```

## CLI

Skill 3 prints JSON to stdout, so redirect it when you want an artifact on disk.

### Single-student run

```bash
python3 skill3_mentor_discovery/run_skill3.py \
  --student-id jamie-taylor-00008 \
  --top-k 5 \
  > /tmp/skill3.json
```

### Graph-aligned explicit run

Use this when you want Skill 3 to consume the same processed bundle as graph-mode `progrec_agent/run_agent.py`.

```bash
python3 skill3_mentor_discovery/run_skill3.py \
  --student-id jamie-taylor-00008 \
  --top-k 5 \
  --skill2-graph skill2_handoff/regenerate_kit/data/processed/academic_graph.json \
  --skill2-students skill2_handoff/regenerate_kit/data/processed/student_profiles_standard.json \
  --skill2-mentors skill2_handoff/regenerate_kit/data/processed/mentor_profiles_standard.json \
  > /tmp/skill3_graph.json
```

### Evaluation modes

```bash
python3 skill3_mentor_discovery/run_skill3.py --evaluation-mode ablation --top-k 5
python3 skill3_mentor_discovery/run_skill3.py --evaluation-mode perturbation --top-k 5
python3 -m skill3_mentor_discovery.evaluate
```

## Output Contract

Top-level payload:

```json
{
  "student_id": "jamie-taylor-00008",
  "graph_status": "loaded_lightweight_mentor_subgraph",
  "graph_notice": "optional",
  "data_sources": {
    "student_profiles": "/abs/path/to/student_profiles_standard.json",
    "mentor_profiles": "/abs/path/to/mentor_profiles_standard.json",
    "academic_graph": "/abs/path/to/academic_graph.json",
    "resource_mode": "default"
  },
  "mentor_candidates": []
}
```

Each `mentor_candidates[]` item comes from `MentorCandidate` in `models.py` and includes:

- `mentor_id`
- `mentor_name`
- `topic_score`
- `graph_score`
- `activity_score`
- `centrality_score`
- `network_proximity`
- `personalized_proximity`
- `graph_confidence`
- `mentor_authority`
- `meta_path_breakdown`
- `top_evidence_paths`
- `community_id`
- `final_score`
- `reasons`

## Resource Resolution and Fallbacks

`loaders.py` has two modes.

### Default mode

Triggered when no explicit `--skill2-*` paths are passed.

Behavior:

- student and mentor bundles come from `skill2_handoff/outputs/`
- graph is searched in `outputs/` first, then processed graph under `regenerate_kit/data/processed/`
- if a graph candidate exists but contains invalid JSON, Skill 3 looks for another `academic_graph*.json` in the same directory
- if no usable graph exists, Skill 3 may try rebuilding via Skill 2's regenerate kit
- if rebuild is unavailable, Skill 3 falls back to topic-only ranking

### Explicit mode

Triggered when any `--skill2-graph`, `--skill2-students`, or `--skill2-mentors` flag is passed.

Behavior:

- passed files must exist
- explicit invalid graph JSON raises an error
- explicit mode does not fall back to default bundle paths

### User-visible graph statuses

- `loaded`
- `loaded_lightweight_mentor_subgraph`
- `invalid_or_missing_graph_fallback_to_derived_mentor_graph`
- `unavailable_fallback_to_topic_only`

## Failure Modes

- Unknown `--student-id` prints the first 10 available ids to stderr and exits with code `2`
- Missing explicit Skill 2 files raise `FileNotFoundError`
- Invalid explicit graph JSON raises `ValueError`
- Evaluation modes that require a graph raise `RuntimeError` if no usable graph can be prepared

## Module Map

| Path | Role |
|------|------|
| `skill3_mentor_discovery/run_skill3.py` | CLI entrypoint and evaluation-mode switch |
| `skill3_mentor_discovery/loaders.py` | Default vs explicit resource resolution and graph rebuild fallback |
| `skill3_mentor_discovery/retrieval.py` | Topic recall, normalization, and final mentor ranking |
| `skill3_mentor_discovery/graph_features.py` | Graph preparation, authority, activity, community ids, graph confidence |
| `skill3_mentor_discovery/trust_signals.py` | Student-specific trust evidence and meta-path aggregation |
| `skill3_mentor_discovery/graph_index.py` | Indexed graph lookup and trust-tier helpers |
| `skill3_mentor_discovery/explanations.py` | Human-readable ranking reasons |
| `skill3_mentor_discovery/models.py` | `MentorCandidate` schema |
| `skill3_mentor_discovery/evaluate.py` | Recall, ablation, and perturbation summaries |

## Verification

Quick smoke test:

```bash
python3 skill3_mentor_discovery/run_skill3.py --student-id jamie-taylor-00008 --top-k 3 | python3 -m json.tool | head -n 80
```

Focused unit tests:

```bash
python3 -m unittest \
  tests.test_skill3_cli \
  tests.test_skill3_evaluate \
  tests.test_skill3_graph_features \
  tests.test_skill3_loaders \
  tests.test_skill3_retrieval \
  tests.test_skill3_trust_signals \
  -v
```

## Common Debugging Checks

Check whether a student exists in the bundle you are actually using:

```bash
python3 -c "import json; p='skill2_handoff/outputs/student_profiles_standard.json'; d=json.load(open(p)); ids={s['student_id'] for s in d.get('students',[])}; print('jamie-taylor-00008' in ids); print(len(ids))"
```

Check processed graph JSON validity:

```bash
python3 -c "import json,sys; p=sys.argv[1]; json.load(open(p)); print('OK', p)" skill2_handoff/regenerate_kit/data/processed/academic_graph.json
```

Inspect the declared data sources from a saved Skill 3 artifact:

```bash
python3 -c "import json; d=json.load(open('/tmp/skill3.json')); print(d['student_id']); print(d['graph_status']); print(d['data_sources'])"
```
