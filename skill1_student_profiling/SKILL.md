---
name: student-profiling
description: "Extracts structured student profiles from raw narrative data. Use when you need to parse student records, extract skills and interests, infer availability, or generate student embeddings for mentor matching. Trigger phrases: profile student, extract skills, student profiling, parse student record."
author: stepbyeee
version: 1.0.0
tags:
  - profiling
  - NLP
  - information-extraction
  - education
  - student
  - SNA
  - StuRec
---

# Student Profiling Skill

Converts raw student records (Major, Hobbies, Unique Quality, Story narrative) into normalized structured profiles with extracted skills, interests, experience summary, and availability — ready for downstream mentor matching, graph construction, and ranking.

## Input

A raw student record dict with fields: `Name`, `Age`, `Sex`, `Major`, `Year`, `GPA`, `Hobbies`, `Country`, `State/Province`, `Unique Quality`, `Story`.

## Output

Normalized `StudentProfile` with 7 fields:
- `student_id` — unique identifier (name slug + index)
- `grade` — Freshman / Sophomore / Junior / Senior
- `major` — normalized major name
- `skills[]` — 4–10 extracted skill terms
- `interests[]` — 2–12 extracted interest terms
- `experience_summary` — 1–3 sentence summary from narrative
- `availability` — high / moderate / low

## Usage

```python
from student_profiling import StudentProfilingSkill

skill = StudentProfilingSkill()
profile = skill.profile(raw_record_dict, index=0)

# Extended output with confidence scores, source tracking, quality score
profile_ext = skill.profile_extended(raw_record_dict, index=0)
```

## Pipeline

Four-source extraction fused by confidence weight:
1. **Structured mapping** (conf 1.0) — Year → grade, Major → major
2. **Taxonomy lookup** (conf 0.85–0.95) — 337 entries: 70 majors → skills, 117 hobbies → interests, 150 unique qualities → skill/interest
3. **Narrative extraction** (conf 0.70) — bounded regex on Story text
4. **Heuristic inference** (conf 0.65–0.85) — availability from Year + story signals; experience summary from action-verb sentences

## Evaluation (n=23,236)

- Field completeness: 100%
- Skills ≥ 3 per profile: 100%
- Major-skill consistency: 100%
- Avg skills: 5.55 | Avg interests: 5.70
- Skill vocabulary entropy: 8.22 bits (target > 4.0)

## Installation

```bash
pip install -e .
```
