# Skill 3 & Skill 4 Output Schemas

## Skill 3 Output Schema

File: `skill3_output.json`

```json
{
  "student_id": "s_002",
  "graph_status": "loaded | loaded_lightweight_mentor_subgraph | unavailable_fallback_to_topic_only",
  "graph_notice": "(optional string)",
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
      "reasons": ["Topic fit supported by overlap in software.", "..."]
    }
  ]
}
```

### Key Fields Used by Skill 5

| Field | Type | Notes |
|-------|------|-------|
| `student_id` | str | Alignment check with Skill 4 |
| `mentor_candidates` | list | May also appear as `recommendations` or `mentors` key |
| `mentor_id` | str | Unique mentor identifier |
| `topic_score` | float [0,1] | Skill 3 topic similarity |
| `graph_score` | float [0,1] | Community + centrality signal |
| `activity_score` | float [0,1] | Research activity proxy |
| `centrality_score` | float [0,1] | Graph degree-style centrality |
| `network_proximity` | float [0,1] | Direct graph distance (often 0.0) |
| `community_id` | str | Mentor community (e.g. `community_0`) |
| `final_score` | float [0,1] | `0.60*topic + 0.25*graph + 0.15*activity` |
| `reasons` | list[str] | Human-readable Skill 3 explanations |

---

## Skill 4 Output Schema

File: `skill4_output.json`

```json
{
  "target_student_id": "s_002",
  "target_student_profile": {
    "grade": "Year 2",
    "major": "Computer Engineering",
    "skills": ["c++", "sql", "tensorflow"],
    "interests": ["computer vision", "robotics"],
    "availability": "moderate"
  },
  "mentor_project_teammate_recommendations": [
    {
      "mentor_id": "m_001",
      "mentor_base_score": 0.368,
      "topic_score": 0.197,
      "graph_score": 0.654,
      "community_id": "community_0",
      "activity_score": 0.575,
      "centrality_score": 0.934,
      "network_proximity": 0.0,
      "mentor_name": "Joseph Foster",
      "skill3_rank": 1,
      "mentor_skill3_reasons": ["..."],
      "matched_topics": ["machine learning", "robotics"],
      "mentor_profile": {},
      "project_recommendations": [
        {
          "project_id": "p_001",
          "title": "Graph-based Research Matching",
          "fit_score": 0.3,
          "topic_match_score": 0.0,
          "skill_match_score": 0.0,
          "difficulty_match_score": 1.0,
          "matched_interests": [],
          "matched_skills": [],
          "missing_skills": ["python", "data analysis"],
          "reason": "..."
        }
      ],
      "teammate_recommendations": [
        {
          "student_id": "s_059",
          "teammate_score": 0.4718,
          "shared_interest_score": 0.75,
          "complementarity_score": 0.1429,
          "availability_score": 0.7,
          "graph_relation_score": 0.0,
          "shared_interests": ["robotics", "security"],
          "complementary_skills": ["python"],
          "availability": "moderate",
          "reason": "..."
        }
      ],
      "reason_paths": [["student → mentor → project → teammate"]]
    }
  ],
  "data_sources": { "..." : "..." },
  "reason_graphs": []
}
```

### Key Fields Used by Skill 5

**Mentor bundle:**

| Field | Type | Notes |
|-------|------|-------|
| `mentor_id` | str | Join key |
| `mentor_base_score` | float | Skill 3 `final_score` forwarded |
| `project_recommendations` | list | Top-N projects for this mentor |
| `teammate_recommendations` | list | Top-N teammates for this mentor |

**Project item:**

| Field | Type | Notes |
|-------|------|-------|
| `project_id` | str | Unique |
| `fit_score` | float | Skill 4 composite (0.40t+0.30s+0.20d+0.10m) |
| `topic_match_score` | float | Jaccard interests vs topic_tags |
| `skill_match_score` | float | Jaccard skills vs required_skills |
| `difficulty_match_score` | float | Grade vs difficulty compatibility |
| `matched_interests` | list[str] | Overlapping interest tags |
| `matched_skills` | list[str] | Overlapping skill tags |
| `missing_skills` | list[str] | Skills the student lacks |

**Teammate item:**

| Field | Type | Notes |
|-------|------|-------|
| `student_id` | str | Candidate teammate |
| `teammate_score` | float | Skill 4 composite |
| `shared_interest_score` | float | Jaccard interests |
| `complementarity_score` | float | Coverage of missing skills |
| `availability_score` | float | high=1.0, moderate=0.7, low=0.4 |
| `graph_relation_score` | float | Graph edge weight (0.0 if no edge) |
| `shared_interests` | list[str] | Overlapping interest tags |
| `complementary_skills` | list[str] | Skills the teammate contributes |

---

## Student ID Alignment Warning

Skill 3 and Skill 4 **must** use the same `student_id` namespace:

| Mode | Student IDs | Bundle |
|------|-------------|--------|
| Demo | `s_001`, `s_002`, ... | `skill2_academic_graph_builder/outputs/student_profiles_standard.json` |
| Regenerated | `jamie-taylor-00008`, ... | `skill2_academic_graph_builder/regenerate_kit/data/processed/student_profiles_standard.json` |

Mixing demo and regenerated IDs will cause mismatches. Skill 5 will log a warning and
continue but results may be incomplete.

---

## final_recommendation.json Output Schema

```json
{
  "student_id": "s_002",
  "student_profile": { "grade": "...", "major": "...", "skills": [], "interests": [] },
  "is_cold_start": false,
  "recommendations": {
    "mentors": [
      {
        "rank": 1,
        "mentor_id": "m_090",
        "final_score": 0.721,
        "scores": {
          "topic_similarity": 0.15,
          "skill_match": 0.10,
          "network_distance": 0.65,
          "community": 0.73,
          "cold_start_bonus": 0.0,
          "activity_score": 0.575,
          "skill3_final_score": 0.341,
          "final_score": 0.721
        },
        "diversity_penalty": -0.05,
        "explanation": "Close network proximity or high centrality. Same research community (community_0)."
      }
    ],
    "projects": [
      {
        "rank": 1,
        "project_id": "p_005",
        "title": "...",
        "mentor_id": "m_090",
        "final_score": 0.55,
        "scores": { "topic_match": 0.3, "skill_match": 0.4, "difficulty_match": 1.0, "mentor_link": 0.368, "skill4_fit_score": 0.3, "final_score": 0.55 },
        "diversity_penalty": 0.0,
        "explanation": "Matches student interests: robotics. Skill overlap: c++."
      }
    ],
    "teammates": [
      {
        "rank": 1,
        "student_id": "s_015",
        "final_score": 0.61,
        "scores": { "shared_interest": 0.6, "complementarity": 0.6, "availability": 0.7, "graph_relation": 0.0, "skill4_teammate_score": 0.61, "final_score": 0.61 },
        "diversity_penalty": 0.0,
        "explanation": "Shared interests: computer vision, robotics. Complementary skills: c++, sql."
      }
    ]
  },
  "summary": {
    "total_mentor_candidates": 10,
    "total_project_candidates": 15,
    "total_teammate_candidates": 30,
    "ranked_mentors": 10,
    "ranked_projects": 10,
    "ranked_teammates": 10
  }
}
```
