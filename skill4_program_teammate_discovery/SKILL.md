# Skill 4 — Project & Teammate Discovery

Skill 4 sits after student profiling (Skill 1), graph construction (Skill 2), and mentor candidate recall (Skill 3). It turns **mentor candidates** into an actionable path: **projects** the student can join and **teammates** who cover skill gaps, using the heterogeneous academic graph when available.

## What Skill 4 does

- For each mentor candidate, load **mentor-linked projects** from `academic_graph.json` (`project_leads`) when possible; otherwise fall back to `data/mock_projects.json`.
- Score projects with a transparent mix of **topic match**, **skill match**, **difficulty vs grade**, and a placeholder **mentor–project link** term.
- Rank **teammates** from the student pool using **shared interests**, **complementarity** on missing project skills, **availability**, and optional **graph edges** (`shared_interest`, `skill_complementarity`).
- Emit **short reasons**, **reason paths**, and optional **node–link graphs** for demos or reports.

## Using Skill 1 output

- `student_profiles_normalized.jsonl` supplies the **target student** and the **candidate teammate pool** when Skill 2’s `student_profiles_standard.json` is missing.
- Each profile contributes `skills`, `interests`, `grade`, `availability`, etc. Skill 1 adapter lowercases and dedupes tags, defaults missing `availability` to `moderate` and `grade` to `unknown`.

## Using Skill 2 output

- **`student_profiles_standard.json` is preferred over Skill 1 JSONL** when both exist: student IDs align with Skill 2 graph nodes and with `student_embeddings_aligned.npy` / `student_ids_aligned.json`.
- **`academic_graph.json`** drives mentor–project links, student–project participation (if present), and teammate-related edges for explanation and `graph_relation_score`.
- **`mentor_profiles_standard.json`** is used when the graph file is absent to still obtain a **mentor candidate list** (fallback).
- **Embeddings** (`.npy` + aligned IDs) are loaded only if present and **row-count matches**; otherwise scoring stays **keyword-based** without errors.

## Important: use the same student ID space across Skill 3 and Skill 4

Skill 3 ranks mentors for **one** student. Skill 4 extends that student into **projects + teammates**. Both skills must agree on **which** `student_id` that is, and on **which Skill 2 student bundle + graph** that ID lives in.

This repository currently ships **two** Skill 2 student profile bundles. Their **`student_id` namespaces do not overlap**.

### Two Skill 2 student bundles (do not mix)

| Mode | Student profiles path | Rough size | `student_id` examples | Typical graph |
|------|-------------------------|------------|-------------------------|----------------|
| **Demo / original handoff** | `skill2_academic_graph_builder/outputs/student_profiles_standard.json` | ~140 students | `s_001`, `s_002`, `s_003`, … | Often **no** `skill2_academic_graph_builder/outputs/academic_graph.json`; use Skill 4’s **mock** graph or another small graph fallback |
| **Regenerated graph** | `skill2_academic_graph_builder/regenerate_kit/data/processed/student_profiles_standard.json` | ~300 students | Skill 1–style IDs, e.g. `jamie-taylor-00008`, `jeffrey-weaver-00044`, `lisa-perry-00052` | `skill2_academic_graph_builder/regenerate_kit/data/processed/academic_graph.json` (large but `json.load`-able; on the order of ~200 mentors, ~300 students, ~57k edges) |

Default **Skill 3** (`skill3_mentor_discovery/run_skill3.py`) loads students from **`skill2_academic_graph_builder/outputs/student_profiles_standard.json`**, so **`s_002`** and friends work out of the box for **demo** runs. The **regenerated** bundle uses **different** IDs; Skill 3 will raise **Unknown student_id** for `jamie-taylor-00008` until its resource paths are pointed at the **same** `student_profiles_standard.json` (and graph) you use for Skill 4 (see `skill3_mentor_discovery/loaders.py` and the Skill 3 README).

### 1. Why `student_id` mismatch happens

- `s_002` belongs to the **demo** Skill 2 output (CSV-style seed IDs).
- `jamie-taylor-00008` belongs to **Skill 1 JSONL + regenerated** Skill 2 graph / processed bundle.
- If Skill 3 ranks mentors for **`s_002`** but Skill 4 loads **`regenerate_kit/.../student_profiles_standard.json`** and **`--target-student-id jamie-taylor-00008`**, the two skills are talking about **different cohorts**. You may see unknown IDs, empty profiles, or misleading overlap between Skill 3 mentor lists and Skill 4’s student pool / graph.
- Skill 4 **guardrails** (when **`--skill3-output`** points at an existing file):
  - Missing or unknown **`--target-student-id`** in the merged Skill 1 + Skill 2 index → **`ValueError`**, exit code **2**, plus up to **10 sample** `student_id`s from the bundle Skill 4 actually loaded.
  - No silent fallback to the “first student” unless you pass **`--allow-target-fallback-with-skill3`** explicitly.
  - If the Skill 3 JSON top-level **`student_id`** / **`target_student_id`** disagrees with Skill 4’s **`effective_target_student_id`**: **`--strict-target-student`** → **`ValueError`**; otherwise a warning prefix **`skill3_target_student_id_mismatch:`** is recorded.

### 2. Demo mode: quick Skill 3 → Skill 4 smoke test (`s_*` space)

Use **demo** students + a **small** graph (Skill 4 mock or your own slice). Example: generate Skill 3 JSON for `s_002`, then run Skill 4 with the **same** `--target-student-id` and **`skill2_academic_graph_builder/outputs/student_profiles_standard.json`**.

```bash
# From repo root — Skill 3 (writes JSON to stdout)
python3 skill3_mentor_discovery/run_skill3.py \
  --student-id s_002 \
  --top-k 10 > /tmp/skill3_s002.json

# Skill 4 — same student_id space as Skill 3; demo graph often absent, so point at mock graph explicitly
python3 skill4_program_teammate_discovery/main.py \
  --target-student-id s_002 \
  --skill3-output /tmp/skill3_s002.json \
  --skill2-students skill2_academic_graph_builder/outputs/student_profiles_standard.json \
  --skill2-mentors skill2_academic_graph_builder/outputs/mentor_profiles_standard.json \
  --skill2-graph skill4_program_teammate_discovery/data/mock_academic_graph.json \
  --skill1-profiles skill1_student_profiling/outputs/student_profiles_normalized.jsonl \
  --projects skill4_program_teammate_discovery/data/mock_projects.json \
  --output skill4_program_teammate_discovery/outputs/skill4_output_with_skill3_demo.json
```

### 3. Regenerated graph mode (Skill 1–style IDs)

Use **regenerated** students **and** the matching **`academic_graph.json`**. **`--target-student-id`** must appear in **`regenerate_kit/data/processed/student_profiles_standard.json`**. Skill 3 must rank mentors for **that same ID** from **that same bundle** (adjust Skill 3 resource paths if the default `outputs/` bundle does not contain your ID).

```bash
# Example target (must exist in the regenerated student JSON you configure for Skill 3 and Skill 4)
STUDENT_ID="jamie-taylor-00008"

python3 skill3_mentor_discovery/run_skill3.py \
  --student-id "$STUDENT_ID" \
  --top-k 10 > /tmp/skill3_regen.json

python3 skill4_program_teammate_discovery/main.py \
  --target-student-id "$STUDENT_ID" \
  --skill3-output /tmp/skill3_regen.json \
  --skill2-students skill2_academic_graph_builder/regenerate_kit/data/processed/student_profiles_standard.json \
  --skill2-graph skill2_academic_graph_builder/regenerate_kit/data/processed/academic_graph.json \
  --skill2-mentors skill2_academic_graph_builder/regenerate_kit/data/processed/mentor_profiles_standard.json \
  --skill1-profiles skill1_student_profiling/outputs/student_profiles_normalized.jsonl \
  --projects skill4_program_teammate_discovery/data/mock_projects.json \
  --output skill4_program_teammate_discovery/outputs/skill4_output_with_skill3.json
```

If `run_skill3.py` still loads only **`outputs/`** students, fix **Skill 3** paths first (or symlink) so `--student-id "$STUDENT_ID"` resolves; otherwise Skill 3 will fail before Skill 4 runs.

## Input file formats

| Input | Format |
|--------|--------|
| Skill 1 profiles | JSONL, one JSON per line (`student_id`, `grade`, `major`, `skills[]`, `interests[]`, `experience_summary`, `availability`) |
| `academic_graph.json` | `{ "version", "nodes": { mentor, paper, topic, project, student }, "edges": [ { type, source, target, weight, metadata? } ] }` with `source`/`target` as `{ "type", "id" }` (Skill 2 export) |
| `student_profiles_standard.json` | `{ "version", "students": [...], "build_meta"? }` |
| `mentor_profiles_standard.json` | `{ "version", "mentors": [...] }` |
| Skill 3 output (`--skill3-output` / `--mentor-candidates`) | JSON array or object with a mentor list key (`mentor_candidates`, `recommendations`, …). Optional top-level **`student_id`** / **`target_student_id`** for alignment checks |
| `mock_projects.json` | JSON array of standardized project dicts (see code: `project_id`, `mentor_id`, `title`, `topic_tags`, `required_skills`, `difficulty`, `description`) |

## Output format

`outputs/skill4_output.json` contains:

- `target_student_id`, `target_student_profile`
- `data_sources` — which paths were used (graph, profiles, mentor list, embedding status)
- `mentor_project_teammate_recommendations` — per-mentor blocks with scored projects, teammates, and `reason_paths`
- `reason_graphs` — node–link structures (NetworkX export when installed)

Downstream **Skill 5 (Social Ranking)** can consume `mentor_project_teammate_recommendations` and merge these signals with global mentor scores.

## How to run

**Skill 3 + Skill 4:** use the same `student_id` and the same Skill 2 bundle as in the section [Important: use the same student ID space across Skill 3 and Skill 4](#important-use-the-same-student-id-space-across-skill-3-and-skill-4).

From the **course repo root** (the directory that contains `skill1_student_profiling/` and `skill4_program_teammate_discovery/`):

```bash
python3 skill4_program_teammate_discovery/main.py \
  --target-student-id s_002 \
  --skill1-profiles ./skill1_student_profiling/outputs/student_profiles_normalized.jsonl \
  --skill2-graph ./skill2_academic_graph_builder/outputs/academic_graph.json \
  --skill2-students ./skill2_academic_graph_builder/outputs/student_profiles_standard.json \
  --skill2-mentors ./skill2_academic_graph_builder/outputs/mentor_profiles_standard.json \
  --mentor-candidates ./skill4_program_teammate_discovery/data/mock_mentor_candidates.json \
  --projects ./skill4_program_teammate_discovery/data/mock_projects.json \
  --output ./skill4_program_teammate_discovery/outputs/skill4_output.json
```

Omit `--target-student-id` only when **not** using `--skill3-output` (then the first student in the Skill 2 bundle is used, or Skill 1 order if Skill 2 students are missing).

Auto-resolve (leave `--skill2-graph` / `--skill2-students` empty) picks, in order:

- `skill2_academic_graph_builder/outputs/…`, then `skill2_academic_graph_builder/regenerate_kit/data/processed/…`, then `data/processed/…`

## How to test

```bash
pip install -r skill4_program_teammate_discovery/requirements.txt
pytest skill4_program_teammate_discovery/tests -q
```

## Current limitations

- Without `academic_graph.json`, mentor–project links rely on **mock projects** or empty project lists per mentor.
- **Skill 3** mentor ranking is optional; missing file falls back to mentors from the graph or `mentor_profiles_standard.json`, then `mock_mentor_candidates.json`.
- Embedding-based similarity is **not** blended into numeric scores yet; embeddings are detected only for future use / transparency in `data_sources`.

## Hooking Skill 3

1. Export Skill 3 JSON (list of mentor rows or an object with `mentor_candidates` / similar list keys). Include **`student_id`** or **`target_student_id`** at the top level when possible so Skill 4 can verify alignment.
2. Pass **`--skill3-output /path/to/skill3.json`** (preferred; same path is used for mentor rows and triggers strict target rules) or **`--mentor-candidates`** if you only have mentor JSON without the Skill 3 alignment contract.
3. Skill 4 uses `final_score` (or `score` / `overall_score`) as `mentor_base_score` in the output.

See **[Important: use the same student ID space across Skill 3 and Skill 4](#important-use-the-same-student-id-space-across-skill-3-and-skill-4)** for the two Skill 2 bundles (`s_*` demo vs Skill 1–style regenerated IDs), example commands, and guardrails.

## Handing off to Skill 5

Skill 5 should read `mentor_project_teammate_recommendations[*].project_recommendations[*].fit_score`, teammate scores, and `mentor_base_score`, then re-rank globally with diversity / cold-start rules as needed.
