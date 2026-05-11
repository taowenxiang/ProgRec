# Skill 1 — Student Profiling Skill: Handoff Package

**Author:** Yueran (Skill 1)
**Date:** 2026-05-07
**For:** ProgRec Agent teammates (Skill 2, 3, 4, 5)

---

## What Skill 1 Does

Skill 1 takes raw student records (the original `student_profiles.jsonl` dataset) and converts each one into a **normalized, structured student profile** with extracted skills, interests, availability, and experience summary.

Raw input has no explicit research-relevant fields — everything is buried in a 2,000–3,300 character narrative (`Story` field) or needs to be inferred from `Major`, `Hobbies`, and `Unique Quality`. Skill 1 extracts and normalizes all of this.

---

## Files in This Folder

| File | Size | Description |
|------|------|-------------|
| `student_profiles_normalized.jsonl` | ~23 MB | **Main output.** 23,236 normalized profiles, one JSON per line |
| `embeddings.npy` | ~34 MB | 384-dimensional sentence embeddings, shape `(23236, 384)`, float32 |
| `student_ids.json` | ~500 KB | List of 23,236 `student_id` strings, in the same order as `embeddings.npy` |

---

## Profile Schema

Each line in `student_profiles_normalized.jsonl` is a JSON object with these fields:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `student_id` | string | Unique ID, format `firstname-lastname-NNNNN` | `"thomas-ibarra-00000"` |
| `grade` | string | One of: `Freshman`, `Sophomore`, `Junior`, `Senior` | `"Senior"` |
| `major` | string | Normalized major name | `"Biochemistry"` |
| `skills` | list[string] | 4–10 extracted skill terms | `["laboratory techniques", "data analysis"]` |
| `interests` | list[string] | 2–12 extracted interest terms | `["photography", "wildlife conservation"]` |
| `experience_summary` | string | 1–3 sentence summary extracted from Story | `"Wildlife conservationist advocating for..."` |
| `availability` | string | One of: `high`, `moderate`, `low` | `"low"` |

### Example Profile

```json
{
  "student_id": "thomas-ibarra-00000",
  "grade": "Senior",
  "major": "Biochemistry",
  "skills": [
    "laboratory techniques",
    "molecular analysis",
    "data analysis",
    "scientific writing"
  ],
  "interests": [
    "table tennis",
    "racket sports",
    "photography",
    "visual arts",
    "wildlife conservation",
    "ecology"
  ],
  "experience_summary": "His love for nature led him to become a wildlife conservationist, advocating for the protection and preservation of endangered species.",
  "availability": "low"
}
```

---

## How to Use the Files

### Option A — Read profiles directly (simplest, no install needed)

```python
import json

profiles = [json.loads(line) for line in open("student_profiles_normalized.jsonl")]

print(len(profiles))          # 23236
print(profiles[0]["skills"])  # ['laboratory techniques', 'molecular analysis', ...]

# Filter by grade
seniors = [p for p in profiles if p["grade"] == "Senior"]

# Filter by skill
ml_students = [p for p in profiles if "machine learning" in p["skills"]]
```

### Option B — Load embeddings (for Skill 2 graph construction / Skill 3 retrieval)

```python
import numpy as np
import json

embeddings = np.load("embeddings.npy")        # shape: (23236, 384)
student_ids = json.load(open("student_ids.json"))  # list of 23236 IDs

# embeddings[i] is the 384-dim vector for student_ids[i]
print(embeddings.shape)   # (23236, 384)
print(student_ids[0])     # "thomas-ibarra-00000"

# Example: cosine similarity between two students
from numpy.linalg import norm
def cosine_sim(a, b):
    return float(np.dot(a, b) / (norm(a) * norm(b)))

sim = cosine_sim(embeddings[0], embeddings[1])
```

### Option C — Use the Python API (if you want to process new records on the fly)

First install the skill package (one-time setup):

```bash
# Clone or copy the student_profiling_skill/ folder to your machine, then:
pip install -e /path/to/student_profiling_skill
```

Then call it:

```python
from student_profiling import StudentProfilingSkill

skill = StudentProfilingSkill()

# Process a single raw record (dict matching the original dataset format)
raw_record = {
    "Name": "Alice Chen",
    "Age": 20,
    "Sex": "Female",
    "Major": "Computer Science",
    "Year": "Junior",
    "GPA": 3.8,
    "Hobbies": ["Chess", "Photography"],
    "Country": "USA",
    "State/Province": "California",
    "Unique Quality": "Competitive programmer",
    "Story": "Alice has been coding since age 12..."
}

profile = skill.profile(raw_record, index=0)
# Returns the same schema as above
```

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| Total profiles | 23,236 |
| Avg skills per profile | 5.55 |
| Avg interests per profile | 5.70 |
| Unique skill terms | 1,470 |
| Unique interest terms | 6,436 |
| Field completeness | 100% (all 7 fields) |
| Availability: high | 26.5% |
| Availability: moderate | 39.2% |
| Availability: low | 34.2% |

---

## Availability Logic

| Grade | Default | Modifiers |
|-------|---------|-----------|
| Freshman / Sophomore | `high` | Story mentions "busy", "job" → `moderate` |
| Junior | `moderate` | Story mentions "graduating", "job offer" → `low` |
| Senior | `low` | Story mentions "eager", "looking for opportunities" → `moderate` |

---

## Embeddings

- Model: `all-MiniLM-L6-v2` (sentence-transformers)
- Dimensions: 384
- Input text: concatenation of `major + skills + interests + experience_summary`
- Use case: semantic similarity search, graph edge weights, clustering

The `student_ids.json` list is **index-aligned** with `embeddings.npy` — row `i` in the numpy array corresponds to `student_ids[i]`.

---

## Questions

Contact Yueran
