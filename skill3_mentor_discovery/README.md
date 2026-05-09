# Skill 3 — Mentor Discovery Skill

---

## What Skill 3 Does

Skill 3 takes a structured student profile plus graph resources from Skill 2 and returns a ranked list of **mentor candidates**.

This skill is designed for the StuRec course project baseline:

- **primary goal:** retrieve suitable mentors for a student
- **core signals:** topic fit + graph-aware mentor features
- **downstream contract:** structured mentor candidates for later skills / final agent ranking

Skill 3 does **not** recommend projects or teammates. Those belong to later skills in the full StuRec pipeline.

---

## Current Design

Skill 3 uses a **topic-first, graph-enhanced** ranking pipeline:

1. Build a student text/profile representation from:
   - `major`
   - `skills`
   - `interests`
   - `experience_summary`
2. Compare the student profile against standardized mentor profiles from Skill 2.
3. Compute a **topic score** using:
   - token-based semantic similarity
   - overlap between student terms and mentor topics / keywords / required skills
4. Add graph-aware mentor features:
   - community membership
   - degree-style centrality
   - mentor activity score
5. Return Top-K mentors with:
   - `topic_score`
   - `graph_score`
   - `community_id`
   - `final_score`
   - short explanation strings

Current scoring formula:

```text
final_score = 0.60 * topic_score + 0.25 * graph_score + 0.15 * activity_score
```

---

## Inputs

### Student input

Skill 3 expects one student profile in the Skill 1 / PRD schema:

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

In the CLI, the common path is to pass a `student_id` from Skill 2’s standardized student bundle.

### Resource inputs from Skill 2

Skill 3 reads:

- `skill2_handoff/outputs/mentor_profiles_standard.json`
- `skill2_handoff/outputs/student_profiles_standard.json`
- `skill2_handoff/outputs/academic_graph.json` **(preferred)**

If the graph is missing, Skill 3 can fall back to `skill2_handoff/regenerate_kit/` and try to rebuild it.

---

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
      "graph_score": 0.6543,
      "activity_score": 0.5750,
      "centrality_score": 0.9347,
      "network_proximity": 0.0,
      "community_id": "community_0",
      "final_score": 0.3410,
      "reasons": [
        "Topic fit is supported by overlap in software.",
        "This mentor belongs to community_0 in the mentor collaboration graph.",
        "The mentor shows solid research activity based on profile and graph signals."
      ]
    }
  ]
}
```

### Important output fields

- `graph_status`
  - `loaded`: full graph loaded directly
  - `loaded_lightweight_mentor_subgraph`: full graph was too large, so Skill 3 switched to a lightweight mentor-focused subgraph
  - `invalid_or_missing_graph_fallback_to_derived_mentor_graph`: no usable graph JSON, so Skill 3 derived a mentor-only graph from standardized mentor metadata
  - `unavailable_fallback_to_topic_only`: rebuild failed and no graph was available

- `graph_notice`
  - present when Skill 3 changes graph mode and should explicitly tell the caller what happened

---

## Large-Graph Behavior

This README calls out one important design choice:

Skill 2’s full graph can become **very large**, especially when `skill_complementarity` edges are present at scale. Loading and indexing the whole graph can slow down downstream skills.

To keep Skill 3 stable:

- it **prefers** `skill2_handoff/outputs/academic_graph.json`
- if that graph is too large, it automatically switches to a **lightweight mentor subgraph**
- when this happens, it **tells you explicitly** via:
  - `graph_status = "loaded_lightweight_mentor_subgraph"`
  - a human-readable `graph_notice`

The lightweight mentor subgraph keeps only the edge types Skill 3 needs most:

- `collaboration`
- `topic_similarity`
- `authored`
- `project_leads`

This keeps mentor discovery usable even when the full heterogeneous graph is too expensive for ranking.

---

## Repository Layout

| Path | Role |
|------|------|
| `skill3_mentor_discovery/loaders.py` | Load Skill 2 resources, prefer `outputs/academic_graph.json`, rebuild if needed |
| `skill3_mentor_discovery/profile_utils.py` | Normalize student / mentor text and topic terms |
| `skill3_mentor_discovery/retrieval.py` | Topic-first mentor ranking |
| `skill3_mentor_discovery/graph_features.py` | Community, centrality, activity, graph-mode switching |
| `skill3_mentor_discovery/explanations.py` | Short explanation generation |
| `skill3_mentor_discovery/evaluate.py` | Weak-label Recall@K evaluation |
| `skill3_mentor_discovery/run_skill3.py` | CLI entrypoint |
| `tests/` | Unit tests for loader, retrieval, graph fallback, CLI, and evaluation |

---

## How To Run

From the project root:

### 1. Run mentor discovery for one student

```bash
python3 skill3_mentor_discovery/run_skill3.py --student-id <student_id> --top-k 5
```

Example:

```bash
python3 skill3_mentor_discovery/run_skill3.py --student-id jamie-taylor-00008 --top-k 3
```

### 2. Run the simple evaluation

```bash
python3 -m skill3_mentor_discovery.evaluate
```

This returns a weak-label summary like:

```json
{
  "recall_at_k": 1.0,
  "evaluated_students": 20,
  "students_with_hits": 20
}
```

### 3. Run tests

```bash
python3 -m unittest discover -s tests -v
```

---

## Evaluation

Current offline evaluation is intentionally simple and course-project-friendly.

### Quantitative baseline

- `Recall@K`
- number of evaluated students
- number of students with at least one weak-label hit

### Weak-label rule

For evaluation, a mentor counts as a hit if at least one of the mentor’s topic terms overlaps with the student’s interest or skill terms.

This is **not** a gold-standard label set. It is a lightweight baseline that makes Skill 3 independently testable for the course project.

---

## Alignment With Skill 2

Skill 3 assumes Skill 2 provides:

- standardized mentor profiles
- standardized student profiles
- an exported graph JSON

The most important current integration choices are:

1. Prefer `skill2_handoff/outputs/academic_graph.json`
2. If that file is too large for direct ranking, switch to lightweight mentor subgraph mode
3. If the graph is invalid or unavailable, fall back gracefully instead of crashing

This makes Skill 3 resilient to both:

- very large graph exports
- imperfect handoff states

---

## Known Limitations

1. Current topic matching is token-based and relatively simple.
2. `network_proximity` is currently conservative and often `0.0`.
3. The current evaluation uses weak labels, not manually curated relevance judgments.
4. Full graph loading can still be expensive because the JSON itself is large, even before subgraph reduction happens.

---

## Suggested Report Framing

If you describe this skill in your individual report, the clearest framing is:

- **Function:** mentor candidate retrieval
- **Methods:** topic similarity, community-aware mentor graph analysis, activity-aware reranking
- **Why graph mode switching exists:** full heterogeneous graph can be too large for direct downstream ranking, so Skill 3 uses a lightweight mentor subgraph when needed
- **Evaluation:** weak-label `Recall@K` + example case studies

---

## Questions

If Skill 2 schema or paths change, update `loaders.py` first. That is the main integration surface for this skill.
