---
name: student-recommendation-ranker
description: >
  This skill implements a multi-objective joint scoring and re-ranking system for
  student-mentor-project-teammate recommendations. Given normalized student profiles
  (student_profiles_normalized.jsonl with fields: student_id, grade, major, skills,
  interests, experience_summary, availability) along with Skill 3 mentor candidate JSON
  and Skill 4 project+teammate bundle JSON, it performs joint scoring and re-ranking using:
  topic similarity, network distance, community membership, skill matching,
  cold-start compensation, and MMR result diversity. Outputs final_recommendation.json
  with ranked lists, per-dimension scores, and explanation features.
  This skill should be used when a user needs to combine Skill 3 and Skill 4 outputs
  into a final unified recommendation, or when multi-criteria re-ranking with explainability
  is needed for mentors, projects, and teammates.
agent_created: true
---

# Student Recommendation Ranker (Skill 5)

## Purpose

Consume **Skill 3** (mentor candidates) and **Skill 4** (project + teammate bundles) outputs
and produce a **final_recommendation.json** with:

- Per-student ranked lists for **mentors**, **projects**, **teammates**
- Per-dimension sub-scores (`topic_similarity`, `skill_match`, `network_distance`,
  `community`, `cold_start_bonus`, `diversity_penalty`)
- MMR diversity re-ranking to avoid topic-redundant results
- Explanation feature strings per recommendation

## Input Files

| File | Format | Description |
|------|--------|-------------|
| Skill 3 output | JSON | Mentor candidates from `run_skill3.py`. Key: `mentor_candidates[]` |
| Skill 4 output | JSON | Project + teammate bundles from `main.py`. Key: `mentor_project_teammate_recommendations[]` |
| Student profiles (optional) | JSONL | Skill 1 format: `student_id`, `grade`, `major`, `skills[]`, `interests[]`, `experience_summary`, `availability` |

For full field definitions, load `references/skill3_skill4_schemas.md`.

## Critical: Student ID Alignment

Skill 3 and Skill 4 **must** use the same `student_id` namespace:

- **Demo mode** (`s_001`, `s_002`, ...): both tools read from `skill2_handoff/outputs/student_profiles_standard.json`
- **Regenerated mode** (`jamie-taylor-00008`, ...): both read from `skill2_handoff/regenerate_kit/data/processed/student_profiles_standard.json`

Mixing namespaces causes mismatched student IDs and empty or wrong recommendations.

## Execution Workflow

### Step 1 — Validate Inputs

1. Check that `--skill3` and `--skill4` paths exist and are non-empty
2. Verify the `student_id` in Skill 3 output matches `target_student_id` in Skill 4 output
3. If both are present, confirm alignment; log a warning on mismatch and continue
4. Load `--students` JSONL for richer student profiles (optional but recommended)

### Step 2 — Run the Joint Ranker Script

```bash
python scripts/joint_ranker.py \
  --skill3  /path/to/skill3_output.json \
  --skill4  /path/to/skill4_output.json \
  --output  /path/to/final_recommendation.json \
  [--students /path/to/student_profiles_normalized.jsonl] \
  [--student-id <specific_student_id>] \
  [--top-k 10] \
  [--weights /path/to/weights.json] \
  [--diversity-lambda 0.7] \
  [--cold-start-bonus 0.10] \
  [--format json|csv|markdown]
```

**Key flags:**
- `--top-k` (default: `10`): number of top recommendations per category
- `--diversity-lambda` (default: `0.7`): MMR lambda; 1.0 = pure relevance, 0.0 = pure diversity
- `--cold-start-bonus` (default: `0.10`): score bonus for mentors with sparse history
- `--format`: output format (`json`, `csv`, `markdown`)

**Minimal example (demo mode):**
```bash
python scripts/joint_ranker.py \
  --skill3 skill3_output.json \
  --skill4 skill4_output.json \
  --output final_recommendation.json
```

**Full pipeline integration example:**
```bash
# Step 1: Run Skill 3 for target student
python skill3_mentor_discovery/run_skill3.py \
  --student-id s_002 --top-k 10 > /tmp/skill3_s002.json

# Step 2: Run Skill 4 with Skill 3 output
python skill4_handoff/main.py \
  --target-student-id s_002 \
  --skill3-output /tmp/skill3_s002.json \
  --output /tmp/skill4_s002.json

# Step 3: Run Skill 5 to produce final recommendations
python scripts/joint_ranker.py \
  --skill3 /tmp/skill3_s002.json \
  --skill4 /tmp/skill4_s002.json \
  --output final_recommendation.json \
  --top-k 10
```

### Step 3 — Interpret Output

The script writes `final_recommendation.json` with structure:

```json
{
  "student_id": "s_002",
  "is_cold_start": false,
  "recommendations": {
    "mentors":   [{ "rank": 1, "mentor_id": "m_090", "final_score": 0.72, "scores": {...}, "explanation": "..." }],
    "projects":  [{ "rank": 1, "project_id": "p_005", "final_score": 0.55, "scores": {...}, "explanation": "..." }],
    "teammates": [{ "rank": 1, "student_id": "s_015", "final_score": 0.61, "scores": {...}, "explanation": "..." }]
  },
  "summary": { "ranked_mentors": 10, "ranked_projects": 10, "ranked_teammates": 10 }
}
```

### Step 4 — Present Results

- Display a summary table for each category (mentor / project / teammate)
- Show top-K entries with rank, final score, dominant scoring dimension, and explanation
- If `is_cold_start: true`, note that diversity-boosting was applied
- If `diversity_penalty` values are large (< -0.15), note that many candidates shared similar topics

## Scoring Dimensions

Load `references/scoring_dimensions.md` for full formulas, default weights, and tuning guidance.

### Quick Reference

**Mentor final score formula:**
```
0.35 * topic_similarity + 0.20 * skill_match + 0.20 * network_distance
+ 0.15 * community + 0.10 * cold_start_bonus
```

**Project final score formula:**
```
0.40 * topic_match + 0.30 * skill_match + 0.20 * difficulty_match + 0.10 * mentor_link
```

**Teammate final score formula (no graph signal):**
```
0.45 * shared_interest + 0.45 * complementarity + 0.10 * availability
```

**Teammate final score formula (with graph signal):**
```
0.35 * shared_interest + 0.35 * complementarity + 0.10 * availability + 0.20 * graph_relation
```

## Custom Weight Override

To override default weights, create a `weights.json`:

```json
{
  "mentor":   { "topic_similarity": 0.40, "skill_match": 0.20, "network_distance": 0.15, "community": 0.15, "cold_start_bonus": 0.10 },
  "project":  { "topic_match": 0.35, "skill_match": 0.35, "difficulty_match": 0.20, "mentor_link": 0.10 },
  "teammate": { "shared_interest": 0.40, "complementarity": 0.40, "availability": 0.10, "graph_relation": 0.10 }
}
```

Pass via `--weights weights.json`. Weights per category are auto-normalized to sum to 1.0.

## Cold-Start Behavior

A **mentor** is cold-start if `publications` is empty AND `topics` has fewer than 2 entries.
A **student** is cold-start if `skills < 2` OR (`experience_summary` word count < 20 AND `interests < 2`).

Cold-start mentor: receives `+cold_start_bonus` (default `0.10`) on `final_score`.  
Cold-start student: an extra `0.5 * cold_start_bonus` is applied to all mentor scores to ensure diverse exposure.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `FileNotFoundError` | Check `--skill3` and `--skill4` paths |
| `student_id` mismatch warning | Ensure both Skill 3 and Skill 4 used the same student bundle (demo vs regenerated) |
| Empty mentor/project recommendations | Skill 4 may lack graph data; project_recommendations may be empty for some mentors |
| All scores identical | Likely all candidates lack skill/topic data; check input data quality |
| `diversity_penalty` all zero | All candidates have non-overlapping tags; diversity is naturally high |

## References

- `references/scoring_dimensions.md` — Full formulas, weight defaults, tuning guide
- `references/skill3_skill4_schemas.md` — Input/output schemas for Skill 3, Skill 4, and final_recommendation
