# Verified graph-mode demo

This folder documents a **known-good graph-mode** ProgRec Agent run (Skills **3 → 4 → 5**) using the regenerated Skill 2 processed bundle. It does not duplicate large JSON artifacts; see the paths below for example outputs already in `outputs/`.

## Student ID

- **`jamie-taylor-00008`** (present in `skill2_academic_graph_builder/regenerate_kit/data/processed/student_profiles_standard.json`)

## Mode

- **`graph`** — `progrec_agent/config.py` resolves:
  - `skill2_academic_graph_builder/regenerate_kit/data/processed/academic_graph.json`
  - `skill2_academic_graph_builder/regenerate_kit/data/processed/student_profiles_standard.json`
  - `skill2_academic_graph_builder/regenerate_kit/data/processed/mentor_profiles_standard.json`
- Skill 3 uses the same three paths as Skill 4 (`data_sources.resource_mode` = `explicit` on Skill 3 when wired through the Agent).

## Pipeline

1. **Skill 3** — mentor candidates (topic + graph rerank).
2. **Skill 4** — projects and teammates per mentor (`data_sources.project_source` = `skill2_graph` when the real graph is used).
3. **Skill 5** — `joint_ranker.py` global ranking across mentors, projects, teammates.

Before Skill 5, the orchestrator runs a **hard `student_id` alignment** check (Skill 3 id, Skill 4 `target_student_id`, and the selected run id must match).

## Example final outputs (frozen in repo)

These were produced with graph mode and show **non-zero** ranked mentors, projects, and teammates in `summary`:

| File | Notes |
|------|--------|
| `outputs/final_recommendation_graph_phase5.json` | Full pipeline; `summary` shows positive `ranked_mentors`, `ranked_projects`, and `ranked_teammates`. |
| `outputs/final_demo_graph_verified.json` | Same shape; alternate verified snapshot. |

Reproduce a similar run from the repository root:

```bash
python3 progrec_agent/run_agent.py \
  --mode graph \
  --student-id jamie-taylor-00008 \
  --top-k 10 \
  --output outputs/final_recommendation_graph.json \
  --artifacts-dir outputs/run_artifacts_graph
```

Inspect any final JSON:

```bash
python3 progrec_agent/inspect_output.py --output outputs/final_recommendation_graph_phase5.json
```

## What the final file contains

- **`summary`** — counts of candidates and how many were ranked (mentors / projects / teammates).
- **`recommendations.mentors`**, **`recommendations.projects`**, **`recommendations.teammates`** — ranked lists with scores and explanations (Skill 5 output shape).

If your run shows `ranked_projects: 0`, see `AGENTS.md` (graph coverage, mentor–project edges, Skill 4 `data_sources`).
