# Skill 2 — Academic Graph Builder: Handoff Package

---

## What Skill 2 Does

Skill 2 **fuses**:

1. **Synthetic mentor / paper / topic / project seeds** (`data/seeds/*.csv`, `mentor_profiles.json`) — reproducible CS faculty-style corpus.  
2. **Optional Skill 1 student layer** — `skill1_student_profiling/outputs/student_profiles_normalized.jsonl` (+ `embeddings.npy` + `student_ids.json`).

…and builds:

- A single **heterogeneous graph** (`mentor`, `paper`, `topic`, `project`, `student` nodes + typed edges).  
- **Standardized mentor JSON** for retrieval / ranking.  
- **Standardized student JSON** aligned to Skill 1 fields when `--skill1-jsonl` is used.  
- **Embedding subset** `student_embeddings_aligned.npy` whose rows match the exported student list order (sliced using Skill 1’s global index).

Skill communication follows the PRD: **structured payloads + shared paths**, not imports of other skills’ internals.

---

## Alignment With Skill 1 (✓)

| Skill 1 artifact | How Skill 2 uses it |
|------------------|---------------------|
| `student_profiles_normalized.jsonl` | Student **node attributes** (same 7 fields) + `profile_text_for_embedding` (major + skills + interests + experience summary, consistent with Skill 1 embedding input text) |
| `student_ids.json` + `embeddings.npy` | **Row-aligned** global index; Skill 2 exports **`student_embeddings_aligned.npy`** + **`student_ids_aligned.json`** in **the same order as** `student_profiles_standard.json` → `students[]` |

When Skill 1 files are missing, Skill 2 falls back to `data/seeds/students.csv` for student nodes (demo mode).

---

## Repository Layout (source code)

| Path | Role |
|------|------|
| `skills/academic_graph_builder/` | Python package: build, index, evaluate, Skill 1 bridge, embedding slice |
| `data/seeds/` | CSV + `mentor_profiles.json` (+ optional regeneration via `scripts/generate_mentor_pool.py`) |
| `scripts/build_graph.py` | **Main CLI** — graph + mentor bundle + student bundle + aligned embeddings |
| `scripts/inspect_graph.py` | Summary stats + ego PNG / GraphML export |
| `scripts/export_skill2_academic_graph_builder.py` | Copies deliverables into `skill2_academic_graph_builder/outputs/` + refreshes **`regenerate_kit/`** |
| `skill2_academic_graph_builder/regenerate_kit/` | **Portable mini-repo**: generator + builder + `skills/academic_graph_builder/` + `requirements.txt` (see `README.md` inside) |

---

## Outputs (downstream contract)

After running the build (see below), processed artifacts typically live under **`data/processed/`**:

| File | Description |
|------|-------------|
| `academic_graph.json` | Full graph: `nodes.{mentor,paper,topic,project,student}[]`, `edges[]` with `type`, `source`, `target`, `weight` |
| `mentor_profiles_standard.json` | `{ version, mentors[] }` — rich English profiles + `profile_text_for_embedding` |
| `student_profiles_standard.json` | `{ version, students[], build_meta }` — Skill 1 schema when JSONL mode; includes embedding export metadata |
| `student_embeddings_aligned.npy` | `(K, 384)` float32 — **row `i`** matches `students[i]` and `student_ids_aligned.json[i]` |
| `student_ids_aligned.json` | Length-`K` list of `student_id` strings |
| `graph_metrics.json` (optional) | Coverage / alignment / connectivity summary |

### Why Skill 1’s `embeddings.npy` is huge but Skill 2’s aligned file is smaller

They use the **same vector width** (384-dim `float32` per student). The size gap is almost entirely **row count**:

| Artifact | Typical shape | Order-of-magnitude size |
|----------|----------------|-------------------------|
| Skill 1 `embeddings.npy` | `(≈23_236, 384)` — **every** line in `student_profiles_normalized.jsonl` | ~**tens of MB** (e.g. 23236×384×4 B ≈ 35 MiB) |
| Skill 2 `student_embeddings_aligned.npy` | `(K, 384)` — only students that **after filtering + `--skill1-max-students`** end up in the graph export | **~K / 23236** of Skill 1’s file (e.g. K=1800 → ~a few MB) |

Skill 2 does **not** re-train embeddings; it **indexes into** Skill 1’s full matrix using `student_ids.json`. To get a Skill-2 export nearly as large as Skill 1’s, you must raise caps / relax filters — and expect heavier graph build (student–student edges are disabled above ~2800 students for performance).

**Large file note:** `academic_graph.json` can be tens of MB. Use `scripts/export_skill2_academic_graph_builder.py` with `--full-graph` only when you intentionally bundle it.

---

## Build Commands

From repo root:

```bash
pip install -r requirements.txt
```

### A — Demo graph (CSV students only)

```bash
python3 scripts/build_graph.py
```

### B — Integrated Skill 1 students + aligned embeddings (recommended for StuRec)

```bash
python3 scripts/build_graph.py \
  --skill1-jsonl skill1_student_profiling/outputs/student_profiles_normalized.jsonl \
  --skill1-max-students 1800 \
  --skill1-embeddings skill1_student_profiling/outputs/embeddings.npy \
  --skill1-student-ids-json skill1_student_profiling/outputs/student_ids.json \
  --embedding-out data/processed/student_embeddings_aligned.npy \
  --embedding-ids-out data/processed/student_ids_aligned.json \
  --eval-json data/processed/graph_metrics.json
```

Options:

- `--skill1-no-major-filter` — take the first N profiles without CS keyword filtering.  
- `--skip-skill1-embedding-export` — skip `.npy` slicing even if files exist.  
- Tune `--skill1-max-students` (pairwise student edges are skipped if count > ~2800 for performance).

---

## Regenerate kit (`skill2_academic_graph_builder/regenerate_kit/`)

Updated automatically whenever you run `scripts/export_skill2_academic_graph_builder.py` (unless `--skip-regenerate-kit`).

Contains everything needed to **re-generate synthetic mentor/seeds** and **rebuild** the graph in a small folder layout:

1. `pip install -r requirements.txt`
2. `python3 scripts/generate_mentor_pool.py` → writes `data/seeds/`
3. `python3 scripts/build_graph.py` (+ optional Skill 1 flags)

Skill 1 paths resolve relative to the **course repo root** (ancestor with `skill1_student_profiling/`). Details: `regenerate_kit/README.md`.

---

## Pack Handoff Folder (for teammates)

After (or before) building, export copies + checksums:

```bash
python3 scripts/export_skill2_academic_graph_builder.py --run-build
# or, without rebuilding:
python3 scripts/export_skill2_academic_graph_builder.py
# include the full graph JSON (large):
python3 scripts/export_skill2_academic_graph_builder.py --full-graph
# omit refreshing code bundle (not recommended):
python3 scripts/export_skill2_academic_graph_builder.py --skip-regenerate-kit
```

Deliverables:

- **`skill2_academic_graph_builder/outputs/`** — processed JSON/NPY (+ `outputs/MANIFEST.json`: SHA256 for each file). Includes a copy of this README for one-folder zips.
- **`skill2_academic_graph_builder/regenerate_kit/`** — code to regenerate data (`regenerate_kit/MANIFEST.json` lists bundled files).

---

## Python API (quick)

```python
from pathlib import Path
from skills.academic_graph_builder import GraphIndex, build_graph_from_seeds

payload = build_graph_from_seeds(
    Path("data/seeds"),
    skill1_jsonl=Path("skill1_student_profiling/outputs/student_profiles_normalized.jsonl"),
    skill1_max_students=800,
)
idx = GraphIndex(payload)
print(idx.topics_for_mentor("m_001"))
```

---

## Edge Types (for Skill 3 / 4 / 5)

Non-exhaustive list present in `edges[].type`:

`collaboration`, `advising`, `authored`, `paper_topic`, `mentor_topic`, `topic_similarity`, `project_leads`, `project_participation`, `skill_complementarity`, `shared_interest`.

---

## Troubleshooting: “invalid JSON” / `graph_status` fallback

Common causes:

1. **Truncated file** — graph JSON can be **10+ MB**; if the build process is interrupted while writing, you get a partial file that fails `JSON.parse`. Skill 2 now writes **`academic_graph.json` atomically** (temp file + `os.replace`) and refuses **NaN/Infinity** (`allow_nan=False`), then **re-reads** the file with `json.load` before finishing.
2. **Wrong path** — Skill 3 must point at the same `academic_graph.json` you just built (repo `data/processed/` vs `regenerate_kit/data/processed/`).
3. **Strict parsers** — RFC 8259 JSON does not allow `NaN`. If you ever fork `save_graph_json`, keep `allow_nan=False` or downstream JS may reject the file.

Refresh **`regenerate_kit/`** after Skill 2 fixes: `python3 scripts/export_skill2_academic_graph_builder.py`.

---

## Questions / Changes

Coordinate with Skill 2 owner if seed schema or export paths change so downstream JSON loaders stay in sync.
