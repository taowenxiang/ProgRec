# ProgRec Agent — Multi-Skill Architecture

This document describes how the **ProgRec** recommendation stack is organized as separate skills, how they chain together, and how to run and debug the pipeline. It reflects the **current repository layout** (handoff folders, CLI entrypoints, and the `progrec_agent/` package).

For a short repo map, see also the root `README.md`.

---

## Call hierarchy (conceptual)

The end-to-end flow is modeled as one virtual agent root and five stable skill identifiers:

```
/progrec-agent
  → /student-profiling
  → /academic-graph
  → /mentor-discovery
  → /project-teammate-discovery
  → /social-ranking
```

In practice, **Skills 1 and 2** are usually **artifact producers** (batch jobs or pre-built JSON/NPY). **Skills 3–5** are the runtime chain most often executed for a single `student_id`.

---

## Existing `progrec_agent/` (interactive prototype)

The repo already includes a small Python package that orchestrates Skills 3–5 and exposes an interactive CLI:

| Module | Role |
|--------|------|
| `progrec_agent/orchestrator.py` | `ProgRecOrchestrator`: loads a student profile, runs Skill 3 (in-process), Skill 4 (dataset or custom mode), Skill 5 (subprocess to `joint_ranker.py`), returns a combined result dict. |
| `progrec_agent/repl.py` | Interactive REPL (`python3 -m progrec_agent.repl`): commands such as `recommend`, `show mentor`, `show profile`, `help`, `exit`. |
| `progrec_agent/session.py` | Session state for the REPL (current profile, mode, cached results). |
| `progrec_agent/render.py` | Terminal-friendly formatting of recommendations. |
| `progrec_agent/adapters/skill1_adapter.py` | Normalizes **manual** CLI profile fields into the Skill-1-shaped dict used downstream (`custom_profile_mode`). |
| `progrec_agent/adapters/skill2_adapter.py` | Resolves which Skill 2 **bundle** exists on disk (`outputs/` vs `regenerate_kit/data/processed/` vs `data/processed/`). |
| `progrec_agent/adapters/skill3_adapter.py` | Calls Skill 3 ranking APIs in-process (`load_standardized_resources`, `rank_mentors_for_student`). Optional explicit Skill 2 paths (`skill2_graph`, `skill2_students`, `skill2_mentors`) match the graph-mode `ResourceConfig` bundle. |
| `progrec_agent/adapters/skill4_adapter.py` | Runs Skill 4 pipeline (`run_pipeline_from_cli_config` or `discover_projects_and_teammates` for custom profiles). |
| `progrec_agent/adapters/skill5_adapter.py` | Runs `skill5_student_recommendation_ranker/scripts/joint_ranker.py` as a subprocess with `--skill3`, `--skill4`, `--output`, `--student-id`, `--students`. |

**Note:** The REPL remains the interactive entrypoint; batch runs use `progrec_agent/run_agent.py` (see Phase 3 below).

---

## Phase 3 — Agent package layout (`config`, `registry`, `schemas`, `run_agent`)

| Module | Role |
|--------|------|
| `progrec_agent/config.py` | `ResourceConfig` + `resolve_repo_root()` + `resolve_resource_config(mode, repo_root)` — central **demo** vs **graph** paths. Graph mode **raises** if `academic_graph.json` is missing, invalid JSON, has no `nodes.project`, or has no `project_leads` edges (**no silent fallback** to demo). |
| `progrec_agent/skill_registry.py` | `SKILL_REGISTRY` metadata for the five stable `/…` identifiers; `get_skill()`, `list_skills()`. |
| `progrec_agent/schemas.py` | Lightweight JSON checks: `validate_student_profiles`, `validate_skill3_output`, `validate_skill4_output`, `validate_skill5_output`, `get_skill3_student_id`, `get_skill4_student_id`, `assert_agent_student_alignment`, `assert_same_student_id` (delegates to alignment; used by `orchestrator` before Skill 5 and by `run_agent` post-run). |
| `progrec_agent/run_agent.py` | Non-interactive CLI: `--mode {demo,graph}`, `--list-students`, `--skip-skill5`, `--verbose`, `--artifacts-dir`, etc. Paths come from `config`. **Demo** mode: Skill 3 uses default loaders (`skill2_academic_graph_builder/outputs/` bundles). **Graph** mode: Skill 3 receives the same `ResourceConfig` graph + student + mentor paths as Skill 4 (regenerated processed bundle); `run_agent` warns if Skill 3’s `data_sources` disagree with the bundle. |

**Tests:** `python3 -m unittest discover -s progrec_agent/tests -v` (stdlib only). `skill4_program_teammate_discovery/tests/` still use **pytest**-style tests; run `pytest skill4_program_teammate_discovery/tests -q` when pytest is installed.

---

## Stable skill identifiers

| Identifier | Maps to (in this repo) |
|------------|-------------------------|
| `/student-profiling` | Skill 1 — `skill1_student_profiling/` (`outputs/` contains normalized artifacts) |
| `/academic-graph` | Skill 2 — `skill2_academic_graph_builder/` (outputs + `regenerate_kit/`) |
| `/mentor-discovery` | Skill 3 — `skill3_mentor_discovery/` |
| `/project-teammate-discovery` | Skill 4 — `skill4_program_teammate_discovery/` |
| `/social-ranking` | Skill 5 — canonical tree `skill5_student_recommendation_ranker/`; entrypoint `skill5_student_recommendation_ranker/scripts/joint_ranker.py` (used by `progrec_agent`). |

---

## `/student-profiling` (Skill 1)

- **Function:** Normalize raw student narratives into structured profiles (skills, interests, grade, major, availability, experience summary) and optional global embeddings aligned with `student_ids.json`.
- **Input:** Raw student records (outside this repo’s batch CLI); generated artifacts now live under `skill1_student_profiling/outputs/`.
- **Output:** `student_profiles_normalized.jsonl`, `embeddings.npy`, `student_ids.json` (see `skill1_student_profiling/outputs/SKILL1_README.md`).
- **Entrypoint:** No first-party batch script in this repo; README documents an optional installable package API (`StudentProfilingSkill`).
- **Trigger examples:** Prepare or refresh handoff files before Skill 2 graph builds that consume Skill 1 JSONL + embeddings.
- **Notes / limitations:** Skill 1 does **not** build the academic graph or rank mentors; it only supplies standardized student artifacts.

---

## `/academic-graph` (Skill 2)

- **Function:** Fuse synthetic mentor/paper/topic/project seeds with optional Skill 1 students; export heterogeneous `academic_graph.json` plus standardized mentor/student JSON and optional row-aligned embedding slices.
- **Input:** Seeds under `skill2_academic_graph_builder/regenerate_kit/data/seeds/` (after generator scripts if needed); optional `--skill1-jsonl`, `--skill1-embeddings`, `--skill1-student-ids-json` for integrated builds (see `skill2_academic_graph_builder/SKILL2_README.md`).
- **Output:** Typically `academic_graph.json`, `mentor_profiles_standard.json`, `student_profiles_standard.json`, `student_embeddings_aligned.npy`, `student_ids_aligned.json` — either under `skill2_academic_graph_builder/outputs/` or `skill2_academic_graph_builder/regenerate_kit/data/processed/` depending on how you export/run the kit.
- **Entrypoint:** `python3 skill2_academic_graph_builder/regenerate_kit/scripts/build_graph.py` (with flags as documented in `SKILL2_README.md`); related: `generate_mentor_pool.py`, `inspect_graph.py`.
- **Trigger examples:** After updating Skill 1 JSONL, rebuild the graph for graph-mode demos; use documented caps for large classes.
- **Notes / limitations:** Large `academic_graph.json` files are normal; not every clone ships a full graph in `outputs/` — **graph mode requires you to generate artifacts** (see below).

---

## `/mentor-discovery` (Skill 3)

- **Function:** Topic recall plus trust-aware graph reranking to produce ranked **mentor candidates** for one student.
- **Input:** One standardized student record (same fields as Skill 1/2 bundles). By default, Skill 3 resolves paths via `skill3_mentor_discovery/loaders.py`: `skill2_academic_graph_builder/outputs/mentor_profiles_standard.json`, `skill2_academic_graph_builder/outputs/student_profiles_standard.json`, and graph from `skill2_academic_graph_builder/outputs/academic_graph.json` if present, otherwise `skill2_academic_graph_builder/regenerate_kit/data/processed/academic_graph.json` when that file exists. **Optional explicit Skill 2 paths** (CLI or adapter): `--skill2-graph`, `--skill2-students`, `--skill2-mentors`. If any of these are passed, that path must exist (`FileNotFoundError` otherwise; no silent fallback to `outputs/` for missing explicit files). The JSON payload includes `data_sources` with resolved paths and `resource_mode` (`default` vs `explicit`).
- **Output:** JSON on **stdout**: `student_id`, `graph_status`, `mentor_candidates[]`, `data_sources`, optional `graph_notice` (see `skill3_mentor_discovery/README.md` and `MentorCandidate` in `models.py`).
- **Entrypoint:** `python3 skill3_mentor_discovery/run_skill3.py --student-id <id> --top-k <K>`; evaluation: `python3 -m skill3_mentor_discovery.evaluate`.
- **Trigger examples:**  
  Default bundle: `python3 skill3_mentor_discovery/run_skill3.py --student-id jamie-taylor-00008 --top-k 5 > /tmp/skill3.json`  
  Same regenerated resources as graph-mode Agent: add `--skill2-graph`, `--skill2-students`, `--skill2-mentors` pointing at `skill2_academic_graph_builder/regenerate_kit/data/processed/*.json`.
- **Notes / limitations:** Redirect stdout to capture JSON. If graph load/rebuild fails in **default** mode, Skill 3 may **degrade** (topic-only path) — see Fallbacks. Unknown `student_id` prints the first 10 available ids and exits with code 2.

---

## `/project-teammate-discovery` (Skill 4)

- **Function:** Expand each mentor candidate into **project** recommendations and **teammate** recommendations using the heterogeneous graph when available, plus reasons and `reason_paths`.
- **Input:** Skill 1 JSONL path, Skill 2 graph + student + mentor bundles (or auto-resolve), optional Skill 3 JSON (`--skill3-output` or `--mentor-candidates`), mock projects path, target `student_id`. See `skill4_program_teammate_discovery/main.py` and `skill4_program_teammate_discovery/Skill4_README.md`.
- **Output:** JSON file (default `skill4_program_teammate_discovery/outputs/skill4_output.json`): `target_student_id`, `target_student_profile`, `data_sources`, `mentor_project_teammate_recommendations[]` (projects, teammates, `reason_paths`), optional `warnings` / `reason_graphs` depending on pipeline.
- **Entrypoint:** `python3 skill4_program_teammate_discovery/main.py` with the documented flags.
- **Trigger examples:**  
  `python3 skill4_program_teammate_discovery/main.py --target-student-id <id> --skill3-output /tmp/skill3.json --output /tmp/skill4.json`  
  (plus explicit `--skill2-*` paths when auto-resolve is wrong for your mode.)
- **Notes / limitations:** With `--skill3-output`, Skill 4 can enforce alignment between Skill 3’s declared `student_id` / `target_student_id` and the resolved target; use `--strict-target-student` for hard failures. Without a real graph, projects fall back to mocks or empty lists per mentor.

---

## `/social-ranking` (Skill 5)

- **Function:** Joint re-scoring and MMR-style diversity over **mentors**, **projects**, and **teammates** using Skill 3 + Skill 4 JSON plus optional Skill 1 JSONL for richer profiles.
- **Input:** `--skill3` path, `--skill4` path, optional `--students` (Skill 1 JSONL), `--student-id`, `--top-k`, optional `--weights`, `--format`.
- **Output:** `final_recommendation.json` (or path from `--output`) with ranked lists and per-dimension scores (see `skill5_student_recommendation_ranker/SKILL.md`).
- **Entrypoint:** `python3 skill5_student_recommendation_ranker/scripts/joint_ranker.py …` (same script path invoked from `progrec_agent/adapters/skill5_adapter.py`).
- **Trigger examples:**  
  `python3 skill5_student_recommendation_ranker/scripts/joint_ranker.py --skill3 /tmp/skill3.json --skill4 /tmp/skill4.json --output /tmp/final.json --student-id <id> --top-k 10`
- **Notes / limitations:** The ranker script may **not fail loudly** if Skill 3’s `student_id` and Skill 4’s `target_student_id` disagree. **`progrec_agent` enforces a hard alignment check** (`assert_agent_student_alignment` in `schemas.py`, called from `orchestrator.py` after Skill 4 writes disk artifacts and before Skill 5, including when `--skip-skill5` is set) so mismatches raise `ValueError` and Skill 5 is never invoked with inconsistent inputs.

---

## Skill boundaries (downstream contract)

| Skill | Owns |
|-------|------|
| **Skill 3** (`/mentor-discovery`) | **Mentor candidates** only: scores, graph/trust signals, short reasons. |
| **Skill 4** (`/project-teammate-discovery`) | **Project and teammate expansion** per mentor: fit scores, teammate scores, `reason_paths`, `data_sources` transparency. |
| **Skill 5** (`/social-ranking`) | **Final social ranking** across mentors, projects, and teammates (global ordering, MMR, optional weight overrides). |

Skills 1–2 supply **artifacts**; they do not replace 3–5’s ranking roles.

---

## Demo mode vs graph mode

| Aspect | **Demo mode** | **Graph mode** (regenerated / integrated) |
|--------|----------------|-----------------------------------------------|
| **Goal** | Fast smoke tests of **Skills 3 → 4 → 5** wiring and JSON contracts. | End-to-end behavior with a **real** heterogeneous graph and cohort-sized student bundles. |
| **Typical student bundle** | Small or legacy handoff under `skill2_academic_graph_builder/outputs/student_profiles_standard.json` (content varies by what the team exported; **always inspect the file** for which `student_id` values exist). | Built outputs under `skill2_academic_graph_builder/regenerate_kit/data/processed/` after `build_graph.py` (plus aligned mentor/student JSON there). |
| **Graph file** | Often missing or replaced with `skill4_program_teammate_discovery/data/mock_academic_graph.json` for local demos (see `Skill4_README.md` examples). | `academic_graph.json` from Skill 2 (large JSON is expected). |
| **When to use** | CI, classroom demos, adapter tests. | Final reports, realistic mentor–project links from the graph. |

**Important:** Course docs may still mention `s_001`-style demo IDs. Your **on-disk** `student_profiles_standard.json` might use **Skill-1-style** ids (e.g. `firstname-lastname-00000`). **Do not assume id format** — grep or parse the bundle you actually use.

---

## `student_id` alignment (risks)

1. **Do not mix two different `student_profiles_standard.json` files** across Skill 3, Skill 4, and Skill 5 for the same run. In **`progrec_agent/run_agent.py --mode graph`**, Skill 3 and Skill 4 both use the **`ResourceConfig`** processed bundle (`regenerate_kit/data/processed/`). For manual runs, pass the same `--skill2-students` (and graph/mentors) to Skill 3 and Skill 4, or rely on Skill 3 defaults only when you intentionally use the `outputs/` cohort.
2. **Use one `student_id` namespace end-to-end:** the same string must exist in the student bundle, match Skill 3’s `--student-id`, match Skill 4’s `--target-student-id`, and match Skill 5’s `--student-id` (or embedded ids in the JSON).
3. **Agent hard gate (not a warning):** before Skill 5, `ProgRecOrchestrator` requires the selected `student_id`, Skill 3’s on-disk `student_id` (else `target_student_id`), and Skill 4’s `target_student_id` to **all match**. Any mismatch is a **`ValueError`** with paths and the three id strings in the message; Skill 5 is **not** called. This prevents the joint ranker from silently mixing mentors/projects for different students.

---

## Graph mode prerequisites

Before claiming “graph mode” works:

1. Run Skill 2’s graph build from the regenerate kit (see `skill2_academic_graph_builder/SKILL2_README.md`).
2. Ensure **`skill2_academic_graph_builder/regenerate_kit/data/processed/academic_graph.json`** exists (alongside matching `student_profiles_standard.json` and `mentor_profiles_standard.json` in the same processed folder).
3. Use a `student_id` that exists in **that** processed `student_profiles_standard.json` (graph mode wires Skill 3 to the same file).

Until `academic_graph.json` exists, `run_agent --mode graph` fails at config resolution; demo mode may still run with reduced graph signal.

---

## Fallback behavior (what to expect)

| Stage | When | Behavior |
|-------|------|----------|
| **Skill 3** | No usable graph or rebuild fails | Falls back to **topic-only** (or similar) ranking; payload includes `graph_status` / `graph_notice` explaining the path (see `run_skill3.py` + `loaders.py`). |
| **Skill 4** | No `academic_graph.json` or mentor–project edges missing | Uses **mock projects** and/or mentor lists from `mentor_profiles_standard.json` or `data/mock_mentor_candidates.json` as documented in `Skill4_README.md`. |
| **Skill 5** | Skill 3 vs Skill 4 `student_id` mismatch | **ProgRec orchestrator blocks the run** before invoking `joint_ranker.py` (`assert_agent_student_alignment`). The ranker itself may still be permissive if invoked standalone without that gate. |

---

## CLI quick reference

**Skill 3 (single student, JSON to stdout):**

```bash
python3 skill3_mentor_discovery/run_skill3.py --student-id <student_id> --top-k 5 > /tmp/skill3.json
```

Explicit Skill 2 paths (aligned with graph-mode `ResourceConfig`):

```bash
python3 skill3_mentor_discovery/run_skill3.py \
  --student-id <valid_graph_student_id> \
  --top-k 5 \
  --skill2-graph skill2_academic_graph_builder/regenerate_kit/data/processed/academic_graph.json \
  --skill2-students skill2_academic_graph_builder/regenerate_kit/data/processed/student_profiles_standard.json \
  --skill2-mentors skill2_academic_graph_builder/regenerate_kit/data/processed/mentor_profiles_standard.json \
  > /tmp/skill3_graph.json
```

**Skill 4 (consume Skill 3 file — align `--skill2-*` with your mode):**

```bash
python3 skill4_program_teammate_discovery/main.py \
  --target-student-id <student_id> \
  --skill3-output /tmp/skill3.json \
  --output /tmp/skill4.json
```

**Skill 5:**

```bash
python3 skill5_student_recommendation_ranker/scripts/joint_ranker.py \
  --skill3 /tmp/skill3.json \
  --skill4 /tmp/skill4.json \
  --output /tmp/final.json \
  --student-id <student_id> \
  --top-k 10 \
  --students skill1_student_profiling/outputs/student_profiles_normalized.jsonl
```

**Interactive ProgRec agent (current repo):**

```bash
python3 -m progrec_agent.repl
```

**Agent batch runner (`run_agent.py`) — Demo mode**

Uses `skill2_academic_graph_builder/outputs/` student + mentor bundles, **`skill4_program_teammate_discovery/data/mock_academic_graph.json`** as the Skill 4 graph, and `skill1_student_profiling/outputs/student_profiles_normalized.jsonl`. Omit `--student-id` to default to the **first** student in the outputs bundle.

```bash
python3 progrec_agent/run_agent.py \
  --mode demo \
  --student-id <valid_demo_student_id> \
  --top-k 10 \
  --output outputs/final_recommendation_demo.json \
  --artifacts-dir outputs/run_artifacts_demo
```

**Agent batch runner — Graph mode**

Requires a prior Skill 2 build: **`skill2_academic_graph_builder/regenerate_kit/data/processed/academic_graph.json`** (plus matching `student_profiles_standard.json` and `mentor_profiles_standard.json` in the same folder). Graph mode **does not** silently fall back to demo assets if the graph is missing or structurally invalid. Skill 3 and Skill 4 both consume this same processed triple; after a successful run, compare `skill3_result.data_sources` in artifacts (or stderr warnings) if anything looks misaligned.

```bash
python3 progrec_agent/run_agent.py \
  --mode graph \
  --student-id <valid_graph_student_id> \
  --top-k 10 \
  --output outputs/final_recommendation_graph.json \
  --artifacts-dir outputs/run_artifacts_graph
```

### Verified Graph Mode Run

The repo includes **documented** graph-mode parameters and example finals under [`outputs/verified_demo/README.md`](outputs/verified_demo/README.md) (verified `student_id`, processed graph paths, and pointers to frozen `outputs/*.json` where `summary.ranked_*` are all non-zero).

**Recommended reproduce command** (from repository root; requires a built processed bundle):

```bash
python3 progrec_agent/run_agent.py \
  --mode graph \
  --student-id jamie-taylor-00008 \
  --top-k 10 \
  --output outputs/final_recommendation_graph.json \
  --artifacts-dir outputs/run_artifacts_graph
```

**`--artifacts-dir` copies** (after a successful run):

| File | Meaning |
|------|--------|
| `skill3.json` | Skill 3 mentor candidate list + `data_sources` (which Skill 2 files were loaded). |
| `skill4.json` | Skill 4 expansion: projects/teammates per mentor + `data_sources` (e.g. `project_source`). |
| `skill5.json` | Same body as `--output` when Skill 5 runs: joint ranker result with `summary` and `recommendations`. |

**Before Skill 5**, `ProgRecOrchestrator` calls **`assert_agent_student_alignment`**: the selected `student_id`, Skill 3’s on-disk `student_id` (or `target_student_id`), and Skill 4’s `target_student_id` must match; otherwise a **`ValueError`** is raised and **`joint_ranker.py` is not invoked** (this is a hard error, not a warning).

**Inspect a final JSON** (read-only):

```bash
python3 progrec_agent/inspect_output.py --output outputs/final_recommendation_graph.json
```

**Other useful flags**

- `--list-students` — print up to 20 `student_id` values from the mode’s student bundle and exit.
- `--skip-skill5` — stop after Skill 4; writes Skill 4 JSON (not `joint_ranker` shape) to `--output`.
- `--verbose` — extra validation details on stderr.
- `--top-k` / `--top-k-mentors` — mentor top‑K for Skill 3 and ranking cap for Skill 5.

**`student_id` rules for `run_agent`**

- The id must exist in the **mode’s** `student_profiles_standard.json` (outputs for demo, processed for graph). There is **no** silent fallback to another bundle.
- In **demo** mode, Skill 3’s default loaders read **`skill2_academic_graph_builder/outputs/`** mentor + student bundles. In **graph** mode, Skill 3 uses the **processed** bundle from `config` (same paths as Skill 4).
- After Skill 4, the orchestrator runs **`assert_agent_student_alignment`** (same checks as `assert_same_student_id`) so the pipeline-selected `student_id` matches both JSON files **before** Skill 5. `run_agent` also re-validates with `assert_same_student_id` after a successful run.

---

## Debugging guide

If you see **`Student ID mismatch before Skill 5`**, open the printed `skill3_path` and `skill4_path` and compare top-level ids to `expected_student_id`. Fix the upstream step that produced the wrong id; do not patch Skill 5 to ignore the error.

### 1. Check whether `student_id` exists in your bundle

```bash
python3 -c "import json; p='skill2_academic_graph_builder/outputs/student_profiles_standard.json'; d=json.load(open(p)); ids={s['student_id'] for s in d.get('students',[])}; print('jamie-taylor-00008' in ids); print(len(ids))"
```

Adjust the path if you use `skill2_academic_graph_builder/regenerate_kit/data/processed/student_profiles_standard.json`.

### 2. Check `academic_graph.json` is valid JSON

```bash
python3 -c "import json,sys; p=sys.argv[1]; json.load(open(p)); print('OK', p)" skill2_academic_graph_builder/regenerate_kit/data/processed/academic_graph.json
```

If the path does not exist, graph mode artifacts were not built yet.

### 3. Inspect Skill 3 output

```bash
python3 skill3_mentor_discovery/run_skill3.py --student-id <id> --top-k 3 | python3 -m json.tool | head -n 80
```

Confirm top-level `student_id` and `mentor_candidates[0].mentor_id`.

### 4. Inspect Skill 4 output

```bash
python3 -c "import json; d=json.load(open('skill4_program_teammate_discovery/outputs/skill4_output.json')); print(d.get('target_student_id')); print(list(d.get('data_sources',{}).keys()))"
```

Check `data_sources` for which graph and mentor candidate paths were used, and scan `warnings` if present.

### 5. REPL / orchestration issues

- Run unit tests: `python3 -m unittest discover -s tests -v` (see root `README.md`).
- Trace which bundle `progrec_agent/adapters/skill2_adapter.py` picks (`outputs_bundle` vs `regenerate_bundle`).

---

## Summary (documentation + Agent layer)

- **`AGENTS.md`** (this file): architecture, skills, demo/graph contracts, CLI, debugging, and **Phase 3** package layout.
- **`progrec_agent/`**: `config.py`, `skill_registry.py`, `schemas.py`, `run_agent.py`, `tests/`, plus existing orchestration and adapters. Skill **1–5 core algorithms** stay in their own trees.

---
