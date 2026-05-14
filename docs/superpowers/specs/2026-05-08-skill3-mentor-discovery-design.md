# Skill 3 Mentor Discovery Design

> For agentic workers: this document defines the approved design for Skill 3 in the ProgRec final project. Implementation should follow this spec before writing detailed task plans.

**Date:** 2026-05-08

**Owner:** Skill 3

**Project Context:** ProgRec is a course project agent for undergraduate research recommendation. Skill 3 is responsible for retrieving and scoring mentor candidates for a given student profile.

---

## 1. Goal

Build an independently testable `Mentor Discovery Skill` that:

- takes a structured student profile plus graph resources from Skill 2,
- retrieves a ranked set of mentor candidates,
- computes graph-aware features for each candidate,
- returns structured outputs that downstream skills can consume,
- provides concise, human-readable reasons for each recommendation.

Skill 3 is responsible for mentor candidate generation only. It does not produce final integrated recommendations with projects and teammates, and it does not own the final cross-entity ranking shown by the full agent.

---

## 2. Scope and Non-Goals

### In scope

- Reading standardized outputs from `skill2_academic_graph_builder/outputs/`
- Falling back to `skill2_academic_graph_builder/regenerate_kit/` when a complete graph is missing
- Accepting a `student_profile` directly or resolving one by `student_id`
- Computing topic/semantic mentor relevance
- Computing mentor-network features including community membership and centrality
- Producing a `mentor_candidate[]` output bundle with numeric scores and explanations
- Supporting standalone evaluation such as `Recall@K` and candidate coverage

### Out of scope

- Project recommendation
- Teammate recommendation
- Final whole-system reranking across mentors, projects, and teammates
- UI/frontend work
- Conversational orchestration logic for the final ProgRec agent

---

## 3. Required Inputs

### Primary student input

Skill 3 accepts either:

1. a full `student_profile` object, or
2. a `student_id` that can be resolved from standardized student resources.

Expected profile schema:

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

### Resource inputs from Skill 2

Skill 3 expects these resources:

- `skill2_academic_graph_builder/outputs/mentor_profiles_standard.json`
- `skill2_academic_graph_builder/outputs/student_profiles_standard.json`
- `academic_graph.json` if already available
- optionally `student_embeddings_aligned.npy` and `student_ids_aligned.json`

If `academic_graph.json` is not already available in usable form, Skill 3 must invoke the rebuild flow through:

- `skill2_academic_graph_builder/regenerate_kit/scripts/build_graph.py`

This matches the chosen operating mode: prefer existing outputs, but rebuild required resources automatically when they are incomplete.

---

## 4. Required Outputs

Skill 3 returns a list of mentor candidates. The minimal output record is:

```json
{
  "mentor_id": "string",
  "topic_score": 0.0,
  "graph_score": 0.0,
  "community_id": "string",
  "final_score": 0.0,
  "reasons": ["string"]
}
```

Recommended enriched output fields:

```json
{
  "mentor_id": "m_003",
  "mentor_name": "Jordan King",
  "topic_score": 0.84,
  "graph_score": 0.58,
  "activity_score": 0.63,
  "community_id": "community_2",
  "centrality_score": 0.44,
  "network_proximity": 0.35,
  "final_score": 0.72,
  "reasons": [
    "Strong match between your NLP interests and the mentor's research areas.",
    "This mentor belongs to a language-focused research community in the collaboration graph.",
    "The mentor shows solid research activity based on publication and profile signals."
  ]
}
```

The output must be machine-readable and stable enough for Skill 5 to consume later.

---

## 5. System Behavior

Skill 3 follows a five-stage pipeline.

### Stage 1: Resource resolution

- Check whether standardized mentor and student files are present.
- Check whether a complete `academic_graph.json` is available.
- If the graph is missing, rebuild it through `regenerate_kit`.
- Load all required resources into in-memory structures.

### Stage 2: Student resolution

- If the caller passes `student_profile`, use it directly.
- If the caller passes `student_id`, resolve the matching student from standardized student resources.
- Normalize the student profile into a common internal representation.

### Stage 3: Topic-first mentor recall

- Convert the student profile into a text representation using:
  - `major`
  - `skills`
  - `interests`
  - `experience_summary`
- Compare the student representation with each mentor profile using:
  - semantic similarity over profile text
  - keyword overlap between student skills/interests and mentor research areas/keywords/required skills
- Produce an initial candidate pool, such as Top-30 mentors by topic relevance.

### Stage 4: Graph feature enrichment

For mentors in the initial candidate pool:

- build a mentor-only graph from `collaboration` and `topic_similarity` edges,
- run community detection on the mentor graph,
- compute mentor centrality,
- compute activity-related signals,
- compute optional student-to-mentor network proximity when reliable graph paths exist.

### Stage 5: Final scoring and explanation

- combine topic and graph signals into a transparent weighted score,
- sort mentors by `final_score`,
- generate 2-3 short reasons per mentor,
- return Top-K candidates.

---

## 6. Scoring Design

Skill 3 uses a two-stage hybrid approach.

### 6.1 Topic score

`topic_score` is the main retrieval signal.

It is composed from:

- semantic similarity between student text and mentor profile text
- lexical overlap between:
  - student `skills`
  - student `interests`
  - mentor `research_areas`
  - mentor `keywords`
  - mentor `required_skills`

This is the most stable primary signal because mentor relevance should first reflect topical fit, and student-side graph edges may be synthetic or sparse depending on the Skill 2 build configuration.

### 6.2 Graph score

`graph_score` enriches candidates after the initial topical recall.

It is composed from:

- `centrality_score`
- `network_proximity`
- optional `community_bonus`

The graph score should not dominate the ranking. It exists to incorporate SNA structure and improve explainability.

### 6.3 Activity score

`activity_score` captures mentor activity and visibility using available structured signals such as:

- `h_index`
- authored paper count
- available project count if present

### 6.4 Final score

The initial default formula is:

```text
final_score = 0.60 * topic_score + 0.25 * graph_score + 0.15 * activity_score
```

This weighting is intentionally transparent and easy to report. It can later be tuned, but the first implementation should keep the formula explicit.

---

## 7. Graph Methods

### Mentor graph construction

Use only mentor-to-mentor edges for community and centrality calculations:

- `collaboration`
- `topic_similarity`

This keeps the graph analysis focused and stable.

### Community detection

Preferred baseline:

- `networkx.algorithms.community.greedy_modularity_communities`

Rationale:

- simple dependency profile,
- deterministic enough for course use,
- easy to explain in the report.

Each mentor receives a `community_id` such as `community_0`, `community_1`, and so on.

### Centrality

At least one centrality metric should be used. Recommended order:

1. degree centrality
2. PageRank

Degree centrality is the easiest baseline; PageRank can be added if it improves ranking quality or explanations.

### Network proximity

If the graph contains a reliable student-to-mentor path, compute a normalized proximity feature based on shortest-path distance. This feature must be down-weighted or omitted when student linkage is weak or entirely synthetic.

---

## 8. Explanations

Each mentor candidate should include short template-based reasons chosen from three evidence groups:

- topical fit
- graph/community evidence
- activity evidence

Example explanation patterns:

- "Your interests overlap strongly with this mentor's research areas in NLP and retrieval."
- "This mentor is part of a language-focused collaboration community connected through topic similarity."
- "This mentor appears active based on publication strength and profile signals."

Explanations should be concise, deterministic, and derived from available structured features.

---

## 9. Evaluation Plan

Skill 3 must be independently testable. The baseline evaluation should include:

### Quantitative metrics

- `Recall@K`
- candidate coverage
- average score distribution sanity checks

### Qualitative or weakly supervised evaluation

Because true mentor-ground-truth labels may be limited, Skill 3 may use:

- weak labels derived from interest/mentor-topic alignment, or
- manually curated case studies

### Required analysis views

- baseline retrieval with `topic_score` only
- retrieval with graph enhancement enabled
- a short ablation comparing the two

This ensures the report can discuss whether graph structure actually helps.

---

## 10. File and Module Design

Skill 3 should live in a dedicated folder, for example:

```text
skill3_mentor_discovery/
  loaders.py
  profile_utils.py
  graph_features.py
  retrieval.py
  explanations.py
  evaluate.py
  run_skill3.py
```

Responsibilities:

- `loaders.py`
  - load handoff resources
  - detect missing graph assets
  - trigger rebuild flow when necessary
- `profile_utils.py`
  - normalize student and mentor text/fields
  - compute set-based overlap helpers
- `graph_features.py`
  - build mentor subgraph
  - compute communities, centrality, proximity, activity features
- `retrieval.py`
  - compute topic-first recall
  - rerank with graph features
- `explanations.py`
  - convert structured evidence into short reasons
- `evaluate.py`
  - run `Recall@K`, coverage, and ablation evaluation
- `run_skill3.py`
  - provide a CLI for standalone execution

---

## 11. Execution Order

Implementation should proceed in this order:

1. Make resource loading and auto-rebuild work.
2. Build a topic-only mentor retrieval baseline.
3. Add mentor graph construction plus community and centrality features.
4. Add final scoring and explanation generation.
5. Add evaluation and demo cases.

This order ensures the skill remains usable even if later graph enhancements take longer than expected.

---

## 12. Risks and Handling

### Risk: missing full graph in current handoff

Handling:

- auto-rebuild through `regenerate_kit`

### Risk: student graph connectivity is weak or synthetic

Handling:

- use topic relevance as the primary retrieval signal
- keep network proximity optional and low-weighted

### Risk: no strong gold labels for mentor relevance

Handling:

- use weak labels and case-study evaluation
- include ablation and qualitative examples in the report

---

## 13. Final Design Decision

The approved design is a **topic-first, graph-enhanced mentor retrieval skill**.

Why this design was chosen:

- it is the safest path to a working course-project baseline,
- it integrates naturally with existing Skill 1 and Skill 2 outputs,
- it includes genuine SNA methods through mentor communities and network features,
- it is easy to evaluate, explain, and report.
