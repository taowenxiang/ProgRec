# Skill 3 - Mentor Discovery Skill

## What Skill 3 Does

Skill 3 takes a standardized student profile plus graph resources from Skill 2 and returns a ranked list of mentor candidates.

- Primary goal: retrieve suitable mentors for a student
- Core signals: topic recall plus trust-aware graph reranking
- Downstream contract: structured mentor candidates for later skills or final agent ranking

## Current Design

Skill 3 uses a two-stage mentor recommendation pipeline:

1. Topic recall builds a student representation from `major`, `skills`, `interests`, and `experience_summary`, then retrieves a candidate pool with semantic similarity plus term overlap.
2. Trust-aware graph reranking enriches recalled mentors with:
   - `mentor_authority`
   - `personalized_proximity`
   - meta-path evidence across project, interest, complementarity, and advising signals
   - `graph_confidence` that downweights weak graph evidence
3. Final ranking combines normalized topic fit, confidence-weighted graph score, and activity score.

Current final score:

```text
final_score = 0.60 * normalized_topic + 0.25 * confidence_weighted_graph + 0.15 * normalized_activity
```

## Inputs

Skill 3 expects one student profile in the standardized Skill 1 / Skill 2 schema:

```json
{
  "student_id": "string",
  "grade": "string",
  "major": "string",
  "skills": ["string"],
  "interests": ["string"],
  "experience_summary": "string",
  "availability": "string"
}
```

It reads:

- `skill2_handoff/outputs/mentor_profiles_standard.json`
- `skill2_handoff/outputs/student_profiles_standard.json`
- `skill2_handoff/outputs/academic_graph.json` when available

If the graph export is missing, Skill 3 can attempt a rebuild and otherwise falls back gracefully.

## Outputs

Skill 3 returns a JSON payload like:

```json
{
  "student_id": "jamie-taylor-00008",
  "graph_status": "loaded_lightweight_mentor_subgraph",
  "graph_notice": "Skill 3 switched to a lightweight mentor subgraph because the full graph had 1253538 edges.",
  "mentor_candidates": [
    {
      "mentor_id": "m_090",
      "mentor_name": "Joseph Foster",
      "topic_score": 0.1519,
      "graph_score": 0.4384,
      "activity_score": 0.575,
      "centrality_score": 0.9347,
      "network_proximity": 0.0,
      "personalized_proximity": 0.63,
      "graph_confidence": 0.78,
      "mentor_authority": 0.9347,
      "meta_path_breakdown": {
        "project_path_score": 0.4,
        "interest_path_score": 0.18,
        "complementarity_path_score": 0.05,
        "advising_path_score": 0.25
      },
      "top_evidence_paths": [
        "student->project->mentor",
        "student->shared_interest->student->mentor"
      ],
      "community_id": "community_0",
      "final_score": 0.341,
      "reasons": [
        "Topic fit is supported by overlap in software.",
        "Representative graph path: student->project->mentor.",
        "Graph evidence is supported by multiple trust-weighted paths."
      ]
    }
  ]
}
```

Important fields:

- `personalized_proximity`: student-specific graph closeness built from trust-weighted meta-path evidence
- `graph_confidence`: confidence multiplier for graph evidence, higher when stronger path types support the match
- `mentor_authority`: mentor-side authority derived from graph connectivity
- `meta_path_breakdown`: contribution of each path family to the trust signal
- `top_evidence_paths`: short human-readable evidence paths used in explanations
- `graph_status` / `graph_notice`: whether Skill 3 used the full graph, a lightweight mentor subgraph, or a fallback path

## Repository Layout

| Path | Role |
|------|------|
| `skill3_mentor_discovery/loaders.py` | Load Skill 2 resources and handle graph fallback |
| `skill3_mentor_discovery/profile_utils.py` | Normalize student and mentor text features |
| `skill3_mentor_discovery/retrieval.py` | Topic recall plus trust-aware reranking |
| `skill3_mentor_discovery/graph_features.py` | Candidate graph features, graph preparation, and graph confidence |
| `skill3_mentor_discovery/graph_index.py` | Typed heterogeneous graph index and trust-tier lookup |
| `skill3_mentor_discovery/trust_signals.py` | Personalized trust signals and meta-path evidence aggregation |
| `skill3_mentor_discovery/explanations.py` | Candidate explanation strings |
| `skill3_mentor_discovery/evaluate.py` | Weak-label recall, ablation, and perturbation summaries |
| `skill3_mentor_discovery/run_skill3.py` | CLI entrypoint |

## How To Run

From the project root:

Single-student mode:

```bash
python3 skill3_mentor_discovery/run_skill3.py --student-id jamie-taylor-00008 --top-k 3
```

Weak-label evaluation:

```bash
python3 -m skill3_mentor_discovery.evaluate
```

Ablation summary:

```bash
python3 skill3_mentor_discovery/run_skill3.py --evaluation-mode ablation --top-k 5
```

Perturbation summary:

```bash
python3 skill3_mentor_discovery/run_skill3.py --evaluation-mode perturbation --top-k 5
```

Focused test suite:

```bash
python3 -m unittest tests.test_skill3_cli tests.test_skill3_evaluate tests.test_skill3_graph_features tests.test_skill3_retrieval tests.test_skill3_trust_signals -v
```

## Evaluation

Skill 3 reports three evaluation views:

- Weak-label `Recall@K`: a student counts as a hit when at least one returned mentor shares topic terms with the student's interests or skills
- Ablation summary: compares `topic_only`, `topic_plus_authority`, `topic_plus_personalized_graph`, and `topic_plus_personalized_graph_plus_trust`
- Perturbation summary: measures top-k stability for the full trust-aware reranker under low-trust edge removal and random edge drop

These are lightweight offline checks rather than gold-label relevance judgments, but they make the trust-aware reranker easy to sanity-check and compare.

## Alignment With Skill 2

Skill 3 assumes Skill 2 provides standardized mentor profiles, standardized student profiles, and a graph export. It prefers the exported heterogeneous graph, can switch to a lightweight mentor subgraph when the full graph is too large, and falls back without crashing if graph preparation is unavailable.

## Known Limitations

1. Topic matching is still token-based and lightweight.
2. Weak-label recall is not a substitute for curated relevance labels.
3. Large graph JSON files can still be expensive to load even when ranking later uses a reduced mentor subgraph.

## Suggested Report Framing

For an individual report, the cleanest framing is:

- Function: trust-aware heterogeneous graph mentor recommendation
- Methods: topic recall, mentor authority, personalized proximity, graph confidence, and meta-path evidence reranking
- Rationale for graph mode switching: full heterogeneous exports may be too large for direct ranking, so Skill 3 can reduce to a mentor-focused subgraph while preserving useful trust signals
