# Student Profiling Skill

**StuRec Agent — Skill 1**

Extracts structured student profiles from raw narrative data using taxonomy mapping and NLP-based information extraction. Converts unstructured student records into standardized JSON profiles ready for downstream mentor matching, graph construction, and ranking, with source-aware confidence metadata and cleanup for generic terms.

---

## Overview

Raw student data contains narrative "Story" fields (2000–3300 chars) with no explicit research skills or interests. This skill:

1. Maps structured fields (Major, Year, Hobbies, Unique Quality) through curated taxonomy JSONs
2. Extracts additional skills/interests from narrative text using regex patterns
3. Infers availability from year + story signals
4. Generates experience summaries from action sentences
5. Produces a standardized `StudentProfile` JSON for all downstream skills
6. Cleans generic or visually weak terms before final export

**Dataset**: 23,236 student profiles — 100% field completeness, avg 5.52 skills, avg 5.74 interests per profile.

---

## Installation

```bash
pip install -e .                          # Tier 1 (MVP)
pip install -e ".[embeddings]"            # + sentence-transformer embeddings
pip install -e ".[eval]"                  # + evaluation metrics
pip install -e ".[all]"                   # everything
```

---

## Quick Start

```python
from student_profiling import StudentProfilingSkill

skill = StudentProfilingSkill()

# Single record (Tier 1 — public interface)
record = {
    "Name": "Nancy Brown",
    "Age": 23,
    "Sex": "Female",
    "Major": "Archaeology",
    "Year": "Sophomore",
    "GPA": 3.44,
    "Hobbies": ["dancing", "bouldering"],
    "Country": "USA",
    "State/Province": "Iowa",
    "Unique Quality": "Graphic design guru",
    "Story": "Nancy was fascinated by the history of her hometown..."
}

profile = skill.profile(record, index=0)
# {
#   "student_id": "nancy-brown-00000",
#   "grade": "Sophomore",
#   "major": "Archaeology",
#   "skills": ["field excavation", "artifact analysis", "historical research",
#              "spatial data analysis", "graphic design", "visual communication"],
#   "interests": ["dancing", "performance arts", "bouldering", "rock climbing", "archaeology"],
#   "experience_summary": "She designed posters for the university archaeology exhibition.",
#   "availability": "high"
# }

# Extended profile (Tier 2 — with confidence, sources, quality score)
profile_ext = skill.profile_extended(record, index=0)
# Adds: gpa, confidence{skills, interests, availability}, sources, metadata{quality_score, ...}

# Batch processing
import json
records = [json.loads(line) for line in open("../student_profiles.jsonl")]
profiles = skill.batch_profile(records)
```

---

## CLI

```bash
# Process full dataset
python -m student_profiling.skill \
    --input ../student_profiles.jsonl \
    --output outputs/

# Process first 100 records
python -m student_profiling.skill \
    --input ../student_profiles.jsonl \
    --output outputs/ \
    --limit 100
```

---

## Output Schema

### Tier 1 — Public Interface (required by PLAN.md)

| Field | Type | Description |
|-------|------|-------------|
| `student_id` | `str` | URL-safe slug: `name-slug-NNNNN` |
| `grade` | `"Freshman"\|"Sophomore"\|"Junior"\|"Senior"` | Direct from Year |
| `major` | `str` | Direct from Major |
| `skills` | `list[str]` | 4–10 normalized lowercase terms |
| `interests` | `list[str]` | 2–12 normalized lowercase terms |
| `experience_summary` | `str` | 1–3 action sentences, max 300 chars |
| `availability` | `"high"\|"moderate"\|"low"` | Inferred from Year + Story signals |

### Tier 2 — Extended Fields

| Field | Type | Description |
|-------|------|-------------|
| `gpa` | `float` | Direct from GPA |
| `confidence.skills` | `dict[str, float]` | Per-skill confidence (0.0–1.0) |
| `confidence.interests` | `dict[str, float]` | Per-interest confidence |
| `confidence.availability` | `float` | Availability inference confidence |
| `sources.skills` | `dict[str, list[str]]` | Source tags per skill term |
| `sources.interests` | `dict[str, list[str]]` | Source tags per interest term |
| `metadata.profile_quality_score` | `float` | Composite quality score (0.0–1.0) |
| `metadata.extraction_timestamp` | `str` | ISO 8601 timestamp |

**Source tags**: `major_taxonomy`, `hobby_direct`, `unique_quality`, `story_explicit`

---

## Downstream Handoff

Downstream skills consume profiles via:

```python
# Option 1: Python API
from student_profiling import StudentProfilingSkill
skill = StudentProfilingSkill()
profile = skill.profile(record, index=i)

# Option 2: Read pre-generated JSONL
import json
profiles = [json.loads(l) for l in open("outputs/student_profiles_normalized.jsonl")]

# Option 3: Embeddings (Tier 2)
import numpy as np, json
embeddings = np.load("outputs/embeddings.npy")
student_ids = json.load(open("outputs/student_ids.json"))
```

---

## Evaluation

```bash
# Run automated metrics (no ground truth needed)
python evaluation/evaluate.py \
    --profiles outputs/student_profiles_normalized.jsonl

# Run with gold annotations
python evaluation/evaluate.py \
    --profiles outputs/student_profiles_normalized.jsonl \
    --gold evaluation/gold_annotations.json \
    --output evaluation/results.json
```

### Automated Metrics (full dataset, n=23,236)

| Metric | Value | Target |
|--------|-------|--------|
| Field completeness | 100% | 100% |
| Skills coverage (≥3) | 100% | 100% |
| Interests coverage (≥3) | 100% | 95%+ |
| Experience non-empty | 100% | 90%+ |
| Major-skill consistency | 100% | 100% |
| Skill entropy | 8.21 | >4.0 |
| Unique skill terms | 1,468 | — |
| Unique interest terms | 6,932 | — |

### Current Upgrade Notes

- Generic UQ terms such as `technology` and `science` are now filtered when stronger paired terms are available.
- Narrative cleanup removes noisy outputs such as `several` and malformed phrases such as `nature with others`.
- The main report-facing ablation now uses the progression `baseline -> taxonomy -> UQ -> full pipeline`.

---

## Tests

```bash
pytest tests/ -v
```

29 tests covering: schema validation, field completeness, taxonomy mapping, availability inference, batch processing, student ID generation, and targeted cleanup behavior.

---

## Project Structure

```
student_profiling_skill/
├── src/student_profiling/
│   ├── skill.py              # Main entry: StudentProfilingSkill
│   ├── schemas.py            # Pydantic input/output models
│   ├── extractors/
│   │   ├── structured.py     # Structured field parsing
│   │   ├── narrative.py      # Regex-based Story extraction
│   │   └── inference.py      # Availability + experience summary
│   ├── taxonomy/
│   │   ├── mappings.py       # Load and apply taxonomy
│   │   └── data/
│   │       ├── major_skills.json      # 70 majors → skills
│   │       ├── hobby_interests.json   # 117 hobbies → interests
│   │       └── uq_mapping.json        # 150 UQs → skill/interest/personality
│   ├── embeddings/
│   │   └── encoder.py        # SentenceTransformer wrapper [Tier 2]
│   └── scoring/
│       ├── confidence.py     # Per-field confidence scoring [Tier 2]
│       └── quality.py        # Profile quality scoring [Tier 2]
├── evaluation/
│   ├── metrics.py            # All evaluation metrics
│   └── evaluate.py           # Evaluation runner
├── tests/
│   └── test_integration.py   # 23 integration tests
├── outputs/                  # Generated profiles (gitignore)
└── examples/                 # Sample input/output
```

---

## StudyClawHub

See `skill_manifest.json` for publishing metadata.

**Tags**: `profiling`, `NLP`, `information-extraction`, `education`, `student`, `SNA`, `StuRec`
