# Skill 2 — Regenerate kit (mini layout)

This folder is a **self-contained slice** of the course repo: scripts + `skills/academic_graph_builder` + `requirements.txt`. Use it if teammates only receive `skill2_academic_graph_builder/` but still need to **re-roll synthetic mentors/seeds** or **rebuild** the graph.

## Layout

```
regenerate_kit/
  requirements.txt
  scripts/
    generate_mentor_pool.py   # writes data/seeds/*.csv + mentor_profiles.json
    build_graph.py            # builds data/processed/*
    inspect_graph.py          # stats / ego PNG / GraphML
  skills/
    academic_graph_builder/
      ...
```

`generate_mentor_pool.py` and `build_graph.py` assume this folder is the **bundle root** (parent of `scripts/`). Skill 1 paths (`skill1_student_profiling/outputs/…`) are resolved by walking up to the **course repo root** (first ancestor that contains `skill1_student_profiling/`).

## Typical workflow (course repo on disk)

From **`regenerate_kit/`**:

```bash
pip install -r requirements.txt
python3 scripts/generate_mentor_pool.py   # creates ./data/seeds/ here
python3 scripts/build_graph.py
```

If you **skipped** the generator and only want to test the builder against the main repo’s seeds (still inside the full checkout):

```bash
mkdir -p data
ln -sf ../../../data/seeds data/seeds
python3 scripts/build_graph.py
```

(`../../../` reaches the course repo root from `skill2_academic_graph_builder/regenerate_kit/data/`.)

CSV-only students (no Skill 1):

```bash
python3 scripts/build_graph.py
```

With Skill 1 integration (paths default to `../../skill1_student_profiling/outputs/` when the full repo is checked out next to `skill2_academic_graph_builder/`):

```bash
python3 scripts/build_graph.py \
  --skill1-jsonl ../../skill1_student_profiling/outputs/student_profiles_normalized.jsonl \
  --skill1-max-students 1800
```

Adjust `--skill1-jsonl` / embeddings paths if your folder layout differs.

## Outputs

- Seeds: `data/seeds/` (created/overwritten by the generator)
- Processed: `data/processed/` (`academic_graph.json`, profile bundles, optional aligned embeddings)

## Re-pack

From the full repository root:

```bash
python3 scripts/export_skill2_academic_graph_builder.py
```

Refreshes `skill2_academic_graph_builder/regenerate_kit/` and `skill2_academic_graph_builder/outputs/`.
