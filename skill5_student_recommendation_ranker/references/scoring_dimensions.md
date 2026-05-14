# Scoring Dimensions — Skill 5 Joint Ranker

## Overview

Skill 5 performs multi-objective joint scoring across three recommendation types:
- **Mentors** (fed from Skill 3 output)
- **Projects** (fed from Skill 4 output, per-mentor bundles)
- **Teammates** (fed from Skill 4 output, per-mentor bundles)

All sub-scores are in [0.0, 1.0]. Final scores are clipped to [0.0, 1.0].

---

## 1. Mentor Scoring

### Sub-scores

| Dimension | Description | Source (Skill 3 field) |
|-----------|-------------|------------------------|
| `topic_similarity` | Semantic match between student interests and mentor topics | `mentor.topic_score` |
| `skill_match` | Jaccard overlap of student skills and mentor skills | Computed from `mentor_profile.skills` vs `student.skills` |
| `network_distance` | Graph proximity: centrality + graph_score + network_proximity blend | `0.5*graph_score + 0.3*centrality_score + 0.2*network_proximity` |
| `community` | Shared research community bonus | `community_id` non-null → 0.7 + 0.3*centrality |
| `cold_start_bonus` | Bonus for mentors with sparse history | +`cold_start_bonus` if `publications=[]` and `topics < 2` |

### Default Weights (sum = 1.0)

```json
{
  "topic_similarity":  0.35,
  "skill_match":       0.20,
  "network_distance":  0.20,
  "community":         0.15,
  "cold_start_bonus":  0.10
}
```

### Formula

```
final_score = topic_similarity * w_topic
            + skill_match       * w_skill
            + network_distance  * w_network
            + community         * w_community
            + cold_start_bonus  * w_cold_start
```

Skill 3 formula (for reference, not directly re-used):
```
skill3_final = 0.60 * topic_score + 0.25 * graph_score + 0.15 * activity_score
```

---

## 2. Project Scoring

### Sub-scores

| Dimension | Description | Source (Skill 4 field) |
|-----------|-------------|------------------------|
| `topic_match` | Jaccard of student interests vs project topic_tags | `project.topic_match_score` |
| `skill_match` | Jaccard of student skills vs required_skills | `project.skill_match_score` |
| `difficulty_match` | Grade-difficulty compatibility | `project.difficulty_match_score` |
| `mentor_link` | Mentor quality as project sponsor score | `bundle.mentor_base_score` |

### Default Weights

```json
{
  "topic_match":     0.40,
  "skill_match":     0.30,
  "difficulty_match": 0.20,
  "mentor_link":     0.10
}
```

### Formula

```
final_score = topic_match  * w_topic
            + skill_match  * w_skill
            + difficulty   * w_difficulty
            + mentor_link  * w_mentor
```

Skill 4 formula (reference):
```
fit_score = 0.40*topic + 0.30*skill + 0.20*difficulty + 0.10*mentor_link
```

---

## 3. Teammate Scoring

### Sub-scores

| Dimension | Description | Source (Skill 4 field) |
|-----------|-------------|------------------------|
| `shared_interest` | Jaccard of student interests vs teammate interests | `teammate.shared_interest_score` |
| `complementarity` | Coverage of missing skills by teammate skills | `teammate.complementarity_score` |
| `availability` | High=1.0, Moderate=0.7, Low=0.4 | `teammate.availability_score` |
| `graph_relation` | `shared_interest` or `skill_complementarity` graph edge | `teammate.graph_relation_score` |

### Default Weights (two modes)

**Without graph signal:**
```json
{ "shared_interest": 0.45, "complementarity": 0.45, "availability": 0.10, "graph_relation": 0.0 }
```

**With graph signal (graph_relation > 0):**
```json
{ "shared_interest": 0.35, "complementarity": 0.35, "availability": 0.10, "graph_relation": 0.20 }
```

### Formula

```
if has_graph_signal:
    final_score = shared_interest * 0.35 + complementarity * 0.35 + availability * 0.10 + graph_relation * 0.20
else:
    final_score = shared_interest * 0.45 + complementarity * 0.45 + availability * 0.10
```

---

## 4. Cold-Start Compensation

A **student** is cold-start if:
- `experience_summary` word count < 20 AND `interests` < 2 items, OR
- `skills` list has fewer than 2 entries

A **mentor** is cold-start if:
- `publications` is empty AND `topics/matched_topics` has fewer than 2 entries

**Effect**: Cold-start entities receive `+cold_start_bonus` (default `0.10`) added to their `final_score`
before MMR re-ranking. Students that are cold-start receive an additional `0.5 * cold_start_bonus`
boost applied to all mentor scores (to ensure diverse exposure for new students).

---

## 5. MMR Diversity Re-Ranking

After initial scoring, Maximal Marginal Relevance (MMR) re-ranks each list:

```
MMR(item) = lambda * relevance_score - (1 - lambda) * max_similarity_to_selected
```

- **lambda** (default `0.7`): balance between relevance and diversity.
  - `lambda=1.0` → pure relevance rank
  - `lambda=0.0` → pure diversity
- **Similarity metric**: Jaccard over item tags (mentor topics, project topic_tags, teammate interests)

The `diversity_penalty` field in each output item reflects the similarity penalty applied.

---

## 6. Custom Weight Override

Create a `weights.json` and pass via `--weights`:

```json
{
  "mentor": {
    "topic_similarity":  0.40,
    "skill_match":       0.20,
    "network_distance":  0.15,
    "community":         0.15,
    "cold_start_bonus":  0.10
  },
  "project": {
    "topic_match":       0.35,
    "skill_match":       0.35,
    "difficulty_match":  0.20,
    "mentor_link":       0.10
  },
  "teammate": {
    "shared_interest":   0.40,
    "complementarity":   0.40,
    "availability":      0.10,
    "graph_relation":    0.10
  }
}
```

Weights within each category are automatically normalized to sum to 1.0.
