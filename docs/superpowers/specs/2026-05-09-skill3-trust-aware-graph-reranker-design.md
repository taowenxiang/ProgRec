# Skill 3 Trust-Aware Graph Reranker Design

> For agentic workers: this document defines the approved upgrade design for Skill 3 in the StuRec final project. Implementation should follow this spec before writing the detailed implementation plan.

**Date:** 2026-05-09

**Owner:** Skill 3

**Project Context:** StuRec is a course project agent for undergraduate research recommendation. Skill 3 is responsible for retrieving and scoring mentor candidates for a given student profile. This design upgrades Skill 3 from a baseline graph-enhanced ranker into a trust-aware, graph-centric mentor recommender with stronger social-network-analysis depth and clearer trustworthiness analysis.

---

## 1. Goal

Upgrade Skill 3 so that it:

- keeps topic relevance as the primary retrieval signal,
- adds stronger personalized graph-based mentor reranking,
- explicitly models whether graph evidence is trustworthy,
- produces recommendation outputs with path-level explanations,
- supports evaluation that is suitable for a course project with a social network trustworthiness emphasis.

The upgraded system should still be lightweight enough to implement and explain clearly in a course project report. It should not require a full graph neural network stack.

---

## 2. Why the Current Baseline Is Not Enough

The current Skill 3 baseline is useful but still too ordinary for a graph-focused course project:

- topic relevance is based on simple lexical / token overlap and bag-of-words cosine similarity,
- graph structure is used mainly through mentor-only community membership and degree-style centrality,
- `network_proximity` is not meaningfully used in ranking,
- graph explanations are short but shallow,
- evaluation mainly checks weak-label topical hits and does not convincingly show graph-specific value or trustworthiness.

This means the current design can serve as a baseline, but it does not yet make a strong argument that the graph contributes meaningful, reliable, student-specific signal.

---

## 3. Design Principles

The upgraded Skill 3 should follow these principles:

1. **Topic fit remains primary.**
   The system must not allow graph prestige alone to overpower mentor-topic relevance.

2. **Graph signals must be personalized.**
   Graph features should reflect how a specific student connects to a specific mentor, not just how globally central the mentor is.

3. **Graph signals must be trust-aware.**
   The model should represent uncertainty and reduce reliance on noisy, synthetic, or weakly supported edges.

4. **Graph signals must be explainable.**
   The output should expose which path families and edge types supported a recommendation.

5. **The method must be report-friendly.**
   Every major component should be easy to explain, ablate, and justify in a final presentation.

---

## 4. Upgraded System Overview

Skill 3 will become a three-stage mentor recommendation pipeline:

### Stage 1: Topic Recall

- Use the current topic-oriented mentor relevance logic to score all mentors.
- Keep topic relevance as the first-stage retrieval signal.
- Produce a candidate pool such as Top-30 or Top-50 mentors before graph reranking.

Purpose:

- preserve relevance,
- reduce graph noise by avoiding full-graph ranking across every mentor,
- make graph reranking more focused and computationally cheaper.

### Stage 2: Trust-Aware Graph Reranking

For each student and each candidate mentor, compute:

- personalized graph proximity,
- meta-path evidence scores,
- mentor authority / bridge features,
- graph confidence.

These graph signals rerank the topic-recalled candidate pool rather than replacing topic relevance.

### Stage 3: Explanation and Trust Report

For each recommended mentor, return:

- final scores,
- path-family evidence,
- trust/confidence summary,
- top supporting paths.

This allows the project to present not only which mentor was recommended, but also why the graph evidence should be trusted.

---

## 5. Graph Signal Design

### 5.1 Personalized Proximity

Skill 3 should compute a student-specific mentor proximity score using a constrained propagation method such as:

- short-hop personalized random walk, or
- constrained Personalized PageRank (recommended).

This propagation must begin at the target student node and spread only through approved edge types. The goal is to estimate how strongly the student is connected to each candidate mentor through meaningful graph structure.

Recommended allowed edge families:

- `student -> shared_interest -> student`
- `student -> skill_complementarity -> student`
- `student -> project_participation -> project -> project_leads -> mentor`
- `student -> shared_interest / skill_complementarity -> student -> advising <- mentor`

Design constraint:

- propagation must be limited by hop depth, restart probability, and candidate filtering so that the signal remains local and interpretable.

### 5.2 Meta-Path Evidence

In addition to a single proximity score, Skill 3 should compute explicit path-family evidence features for each mentor:

- `interest_path_score`
- `complementarity_path_score`
- `project_path_score`
- `advising_path_score`

These features should summarize how much evidence came from each path family. They serve two purposes:

- enrich reranking,
- support path-level explanation and trust analysis.

The system does not need to enumerate every possible path. It only needs to surface the strongest small set of evidence paths and path-family totals.

### 5.3 Mentor Authority

Skill 3 should keep a mentor-only authority signal, but it should become a secondary feature rather than the core graph signal.

Recommended authority features:

- mentor-only PageRank on the mentor subgraph,
- optional bridge-style score that rewards mentors who connect different communities.

Recommended mentor subgraph edge types:

- `collaboration`
- `topic_similarity`

This feature captures whether a mentor is structurally influential, but it should not dominate student-specific proximity signals.

### 5.4 Graph Confidence

Skill 3 should explicitly estimate whether graph evidence is trustworthy for a given student-mentor recommendation.

Recommended graph confidence factors:

- `path_reliability`
  Higher when supporting paths rely on stronger edge types.
- `signal_consistency`
  Higher when multiple path families independently support the same mentor.
- `synthetic_edge_ratio`
  Lower when too much of the evidence depends on synthetic or weakly grounded edges.
- `path_depth_penalty`
  Lower when evidence is only available through long, indirect paths.
- `local_graph_support`
  Higher when the student has enough meaningful nearby neighbors and the graph neighborhood is not too sparse.

Graph confidence should act as a gate on graph influence rather than as a standalone reward. A natural design is:

```text
effective_graph_score = graph_confidence * raw_graph_score
```

This lets the model use graph information aggressively when support is strong, while backing off when graph evidence is weak or noisy.

---

## 6. Edge Trust Tiers

To align with the trustworthiness theme, Skill 3 should explicitly classify edge types by reliability.

### High-trust edges

- `project_participation`
- `project_leads`
- `advising`

Reason:

- these reflect stronger structured interaction or assignment relationships.

### Medium-trust edges

- `shared_interest`
- `topic_similarity`
- `collaboration`

Reason:

- these are meaningful but more indirect indicators of suitability.

### Low-trust edges

- `skill_complementarity`

Reason:

- these edges are useful for exploration and team formation but are more synthetic and should not dominate mentor recommendation.

Expected behavior:

- high-trust edges should receive the largest propagation / explanation weight,
- low-trust edges may still help but should reduce graph confidence if they dominate the evidence.

---

## 7. Final Scoring Design

The upgraded scoring should remain transparent.

### 7.1 Topic score

Retain the current topic-based score as the main relevance anchor.

Possible minor improvement:

- keep the current lexical/cosine baseline initially,
- optionally add embedding-based semantic similarity in a later enhancement if time permits.

### 7.2 Raw graph score

Combine:

- personalized proximity,
- meta-path evidence,
- mentor authority.

Suggested structure:

```text
raw_graph_score =
  w1 * personalized_proximity +
  w2 * meta_path_score +
  w3 * mentor_authority
```

where:

- `meta_path_score` is a summary over explicit path-family evidence,
- `mentor_authority` is lower-weight than the personalized signals.

### 7.3 Effective graph score

Apply trust gating:

```text
effective_graph_score = graph_confidence * raw_graph_score
```

### 7.4 Final score

Suggested final combination:

```text
final_score =
  alpha * topic_score +
  beta * effective_graph_score +
  gamma * activity_score
```

Constraints:

- `alpha` should remain the largest weight,
- graph influence should be meaningful but not overpower topic fit,
- features should be normalized before fusion to avoid scale mismatch.

Initial recommendation:

- normalize each component to a comparable range,
- start with manually chosen weights,
- optionally tune them later through lightweight validation.

---

## 8. Output Contract

The upgraded Skill 3 output should preserve existing fields and add new graph-specific explanation fields.

### Existing core fields

- `mentor_id`
- `mentor_name`
- `topic_score`
- `graph_score`
- `activity_score`
- `community_id`
- `final_score`
- `reasons`

### New required fields

- `personalized_proximity`
- `graph_confidence`
- `meta_path_breakdown`
- `top_evidence_paths`

### Example enriched output

```json
{
  "mentor_id": "m_090",
  "mentor_name": "Joseph Foster",
  "topic_score": 0.61,
  "graph_score": 0.48,
  "personalized_proximity": 0.57,
  "graph_confidence": 0.74,
  "activity_score": 0.58,
  "community_id": "community_0",
  "meta_path_breakdown": {
    "interest_path_score": 0.31,
    "complementarity_path_score": 0.10,
    "project_path_score": 0.42,
    "advising_path_score": 0.27
  },
  "top_evidence_paths": [
    "student -> shared_interest -> student -> advising <- mentor",
    "student -> project_participation -> project -> project_leads -> mentor"
  ],
  "final_score": 0.64,
  "reasons": [
    "Topic fit is strong for software and data-related interests.",
    "The recommendation is supported by project and advising paths in the academic graph.",
    "Graph confidence is high because multiple high-trust path families agree."
  ]
}
```

---

## 9. Evaluation Design

The upgraded Skill 3 should not rely only on a single weak-label recall number.

### 9.1 Core ranking comparison

At minimum, compare these four settings:

1. `Topic Only`
2. `Topic + Authority`
3. `Topic + Personalized Graph`
4. `Topic + Personalized Graph + Trust Gating`

Purpose:

- isolate the value of graph signals,
- show whether personalization matters,
- show whether trust gating improves robustness or ranking quality.

### 9.2 Ranking metrics

Recommended metrics:

- `Recall@K`
- `MRR` or `NDCG@K`
- candidate hit rate

Weak-label evaluation may still be used, but the report should clearly say that it is only a course-project baseline rather than a gold-standard benchmark.

### 9.3 Robustness / trustworthiness experiments

Run graph perturbation experiments such as:

- random edge removal,
- random weak edge injection,
- remove one edge family at a time,
- remove only low-trust edges.

Measure:

- ranking metric drop,
- Top-K overlap,
- ranking stability under perturbation.

The complete model should ideally be more stable than a graph model without trust gating.

### 9.4 Case studies

Include 2-3 student recommendation case studies showing:

- top mentors,
- score breakdown,
- strongest evidence paths,
- how rankings change when key edges or path families are removed.

### 9.5 Counterfactual analysis

For selected recommendations, test statements like:

- if project paths are removed, how much does the rank change?
- if low-trust complementarity edges are removed, does the recommendation stay stable?
- if graph confidence is low, does the model correctly lean back toward topic relevance?

This section is especially important for the trustworthiness story.

---

## 10. Implementation Scope

This upgrade should remain within a course-project-friendly scope.

### In scope

- constrained personalized propagation,
- meta-path evidence extraction,
- mentor PageRank / bridge-style authority,
- graph confidence estimation,
- richer output schema,
- stronger ablation and perturbation evaluation.

### Out of scope

- heavy GNN training pipelines,
- end-to-end learned graph embeddings across the whole heterogeneous graph,
- external large-scale benchmark collection,
- UI redesign.

This keeps the work technically strong without turning the project into a research-infrastructure build.

---

## 11. Risks and Mitigations

### Risk 1: Student-side graph edges are partly synthetic

Mitigation:

- use edge trust tiers,
- downweight low-trust evidence,
- expose synthetic-edge dependence through graph confidence.

### Risk 2: Graph score overwhelms topic relevance

Mitigation:

- keep topic recall as the first stage,
- normalize all features,
- enforce topic-dominant final weighting,
- verify with ablation.

### Risk 3: Personalized graph methods become too expensive

Mitigation:

- run graph reranking only on topic-recalled candidates,
- constrain propagation depth and edge families,
- cache mentor-subgraph statistics when useful.

### Risk 4: Explanations become noisy or too long

Mitigation:

- return only the strongest path families and top few evidence paths,
- keep explanations templated and grounded in actual scores.

---

## 12. Success Criteria

The upgraded Skill 3 should be considered successful if it:

- clearly improves the sophistication of the graph component over the baseline,
- introduces student-specific graph reasoning rather than only global mentor centrality,
- provides a convincing trustworthiness story around graph usage,
- supports ablation, perturbation, and counterfactual analysis,
- remains understandable enough to explain in a course project presentation,
- produces outputs that downstream skills can still consume with minimal breakage.

---

## 13. Recommended Report Framing

For the course report or final presentation, the upgraded Skill 3 should be framed as:

**Trust-Aware Hybrid Mentor Recommendation on a Heterogeneous Academic Graph**

Suggested narrative:

1. Topic-only retrieval is necessary but incomplete.
2. Personalized graph evidence helps recover mentor relevance beyond text overlap.
3. Not all graph evidence is equally trustworthy.
4. A trust-aware reranker can improve recommendation quality while staying more stable under noisy graph structure.

This framing better matches a graph trustworthiness audience than a generic "graph-enhanced recommender" description.
