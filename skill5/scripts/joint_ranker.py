#!/usr/bin/env python3
"""
joint_ranker.py — Skill 5: Multi-Objective Joint Scoring & Re-Ranking
=======================================================================

Consumes Skill 3 (mentor candidates) and Skill 4 (project + teammate bundles)
outputs and produces a unified final_recommendation.json with:

  - Per-student ranked lists for mentors, projects, teammates
  - Per-dimension sub-scores (topic_similarity, skill_match, network_distance,
    community, cold_start_bonus, diversity_penalty)
  - MMR diversity re-ranking
  - Explanation feature strings

Usage
-----
  python joint_ranker.py \\
    --skill3  /path/to/skill3_output.json \\
    --skill4  /path/to/skill4_output.json \\
    --output  /path/to/final_recommendation.json \\
    [--students /path/to/student_profiles_normalized.jsonl] \\
    [--top-k 10] \\
    [--weights /path/to/weights.json] \\
    [--diversity-lambda 0.7] \\
    [--cold-start-bonus 0.10] \\
    [--format json|csv|markdown]

All --skill3 / --skill4 arguments accept:
  - a JSON list of mentor candidate objects
  - a JSON object with keys mentor_candidates / recommendations / mentor_project_teammate_recommendations
    (i.e. the raw output of Skill 3 or Skill 4)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Default scoring weights (sum = 1.0)
# ---------------------------------------------------------------------------
DEFAULT_MENTOR_WEIGHTS: dict[str, float] = {
    "topic_similarity":   0.35,
    "skill_match":        0.20,
    "network_distance":   0.20,
    "community":          0.15,
    "cold_start_bonus":   0.10,
}

DEFAULT_PROJECT_WEIGHTS: dict[str, float] = {
    "topic_match":        0.40,
    "skill_match":        0.30,
    "difficulty_match":   0.20,
    "mentor_link":        0.10,
}

DEFAULT_TEAMMATE_WEIGHTS: dict[str, float] = {
    "shared_interest":    0.40,
    "complementarity":    0.40,
    "availability":       0.10,
    "graph_relation":     0.10,
}

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _load_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def _load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load a JSONL file (one JSON object per line)."""
    rows: list[dict[str, Any]] = []
    p = Path(path)
    if not p.is_file():
        return rows
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def _extract_mentor_candidates(raw: Any) -> list[dict[str, Any]]:
    """Accept list or common dict wrappers from Skill 3 output."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("mentor_candidates", "recommendations", "mentors"):
            if isinstance(raw.get(key), list):
                return raw[key]
    return []


def _extract_skill4_bundles(raw: Any) -> tuple[str, list[dict[str, Any]]]:
    """Return (target_student_id, mentor_project_teammate_recommendations) from Skill 4 output."""
    if isinstance(raw, dict):
        bundles = raw.get("mentor_project_teammate_recommendations") or []
        sid = str(raw.get("target_student_id") or "")
        return sid, bundles
    return "", []


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(abs(v) for v in weights.values())
    if total == 0:
        return {k: 1 / len(weights) for k in weights}
    return {k: v / total for k, v in weights.items()}

# ---------------------------------------------------------------------------
# Cold-start detection
# ---------------------------------------------------------------------------

def _is_cold_start_student(profile: dict[str, Any]) -> bool:
    skills = profile.get("skills") or []
    exp = str(profile.get("experience_summary") or "")
    interests = profile.get("interests") or []
    word_count = len(exp.split())
    return len(skills) < 2 or (word_count < 20 and len(interests) < 2)


def _is_cold_start_mentor(mentor: dict[str, Any]) -> bool:
    pubs = mentor.get("publications") or mentor.get("mentor_profile", {}).get("publications") or []
    topics = (mentor.get("topics") or
              mentor.get("mentor_profile", {}).get("topics") or
              mentor.get("matched_topics") or [])
    return len(pubs) == 0 and len(topics) < 2

# ---------------------------------------------------------------------------
# Mentor scoring (Skill 5 re-scores on top of Skill 3 final_score)
# ---------------------------------------------------------------------------

def score_mentor(
    mentor: dict[str, Any],
    student_profile: dict[str, Any],
    weights: dict[str, float],
    cold_start_bonus: float,
) -> dict[str, float]:
    """
    Derive Skill-5 sub-scores from Skill 3 fields.
    
    Skill 3 already provides:
      topic_score, graph_score, activity_score, centrality_score, 
      network_proximity, community_id, final_score (= 0.60*topic + 0.25*graph + 0.15*activity)
    
    Skill 5 re-weights these into its own schema for joint ranking.
    """
    # Use Skill-3 scores as sub-scores
    topic_sim   = float(mentor.get("topic_score",       mentor.get("topic_similarity", 0.0)) or 0.0)
    graph_score = float(mentor.get("graph_score",       0.0) or 0.0)
    activity    = float(mentor.get("activity_score",    0.0) or 0.0)
    centrality  = float(mentor.get("centrality_score",  0.0) or 0.0)
    net_prox    = float(mentor.get("network_proximity", 0.0) or 0.0)

    # Skill-match: derive from mentor_profile or activity/centrality proxy
    mprof   = mentor.get("mentor_profile") or {}
    m_skills = (mprof.get("skills") or mprof.get("required_skills") or
                mentor.get("skills") or [])
    s_skills = student_profile.get("skills") or []
    skill_match = _jaccard(m_skills, s_skills)

    # Network distance: blend centrality + graph_score
    net_dist = min(1.0, 0.5 * graph_score + 0.3 * centrality + 0.2 * net_prox)

    # Community signal: 1.0 if community_id is non-null, else 0
    community_id = str(mentor.get("community_id") or "")
    community_score = 0.0
    if community_id and community_id not in ("unknown", "community_unknown", ""):
        community_score = min(1.0, 0.7 + 0.3 * centrality)

    # Cold-start bonus
    cs_bonus = cold_start_bonus if _is_cold_start_mentor(mentor) else 0.0

    raw = (
        weights.get("topic_similarity", 0.35) * topic_sim
        + weights.get("skill_match",       0.20) * skill_match
        + weights.get("network_distance",  0.20) * net_dist
        + weights.get("community",         0.15) * community_score
        + weights.get("cold_start_bonus",  0.10) * cs_bonus
    )
    final = min(1.0, max(0.0, raw))

    return {
        "topic_similarity":  round(topic_sim,    4),
        "skill_match":       round(skill_match,  4),
        "network_distance":  round(net_dist,     4),
        "community":         round(community_score, 4),
        "cold_start_bonus":  round(cs_bonus,     4),
        "activity_score":    round(activity,     4),
        "skill3_final_score": round(float(mentor.get("final_score", mentor.get("mentor_base_score", 0.0)) or 0.0), 4),
        "final_score":       round(final, 4),
    }

# ---------------------------------------------------------------------------
# Project scoring (from Skill 4 pre-computed fields)
# ---------------------------------------------------------------------------

def score_project(
    proj: dict[str, Any],
    mentor_base_score: float,
    weights: dict[str, float],
) -> dict[str, float]:
    tm  = float(proj.get("topic_match_score",    0.0) or 0.0)
    sm  = float(proj.get("skill_match_score",    0.0) or 0.0)
    dm  = float(proj.get("difficulty_match_score", 0.0) or 0.0)
    fit = float(proj.get("fit_score",            0.0) or 0.0)
    # Blend mentor quality into project score
    mentor_boost = 0.10 * mentor_base_score
    final = min(1.0, max(0.0,
        weights.get("topic_match",     0.40) * tm
        + weights.get("skill_match",   0.30) * sm
        + weights.get("difficulty_match", 0.20) * dm
        + weights.get("mentor_link",   0.10) * mentor_base_score
        + mentor_boost
    ))
    return {
        "topic_match":       round(tm,  4),
        "skill_match":       round(sm,  4),
        "difficulty_match":  round(dm,  4),
        "mentor_link":       round(mentor_base_score, 4),
        "skill4_fit_score":  round(fit, 4),
        "final_score":       round(final, 4),
    }

# ---------------------------------------------------------------------------
# Teammate scoring (from Skill 4 pre-computed fields)
# ---------------------------------------------------------------------------

def score_teammate(
    mate: dict[str, Any],
    weights: dict[str, float],
) -> dict[str, float]:
    sis  = float(mate.get("shared_interest_score",  0.0) or 0.0)
    comp = float(mate.get("complementarity_score",  0.0) or 0.0)
    av   = float(mate.get("availability_score",     0.0) or 0.0)
    gr   = float(mate.get("graph_relation_score",   0.0) or 0.0)
    skill4_ts = float(mate.get("teammate_score", 0.0) or 0.0)

    has_graph = gr > 0.0
    if has_graph:
        final = min(1.0, max(0.0,
            weights.get("shared_interest",  0.35) * sis
            + weights.get("complementarity", 0.35) * comp
            + weights.get("availability",    0.10) * av
            + weights.get("graph_relation",  0.20) * gr
        ))
    else:
        final = min(1.0, max(0.0,
            weights.get("shared_interest",  0.45) * sis
            + weights.get("complementarity", 0.45) * comp
            + weights.get("availability",    0.10) * av
        ))

    return {
        "shared_interest":   round(sis,  4),
        "complementarity":   round(comp, 4),
        "availability":      round(av,   4),
        "graph_relation":    round(gr,   4),
        "skill4_teammate_score": round(skill4_ts, 4),
        "final_score":       round(final, 4),
    }

# ---------------------------------------------------------------------------
# MMR diversity re-ranking
# ---------------------------------------------------------------------------

def _jaccard(a: list[str], b: list[str]) -> float:
    sa = {str(x).lower() for x in a}
    sb = {str(x).lower() for x in b}
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _item_tags(item: dict[str, Any], item_type: str) -> list[str]:
    """Extract representative tags for diversity comparison."""
    if item_type == "mentor":
        return (item.get("matched_topics") or item.get("topics") or
                [str(item.get("community_id", ""))])
    if item_type == "project":
        return (item.get("topic_tags") or item.get("matched_interests") or
                item.get("matched_skills") or [])
    # teammate
    return (item.get("shared_interests") or item.get("interests") or [])


def mmr_rerank(
    scored_items: list[tuple[float, dict[str, Any]]],
    item_type: str,
    lam: float = 0.7,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """
    Maximal Marginal Relevance re-ranking.
    lam=1.0 => pure relevance, lam=0.0 => pure diversity.
    """
    if not scored_items:
        return []

    remaining = list(scored_items)  # (score, item)
    selected: list[dict[str, Any]] = []
    selected_tags: list[list[str]] = []

    while remaining and len(selected) < top_k:
        best_score = -math.inf
        best_idx = 0
        for i, (rel, item) in enumerate(remaining):
            tags = _item_tags(item, item_type)
            if not selected_tags:
                sim_to_selected = 0.0
            else:
                sim_to_selected = max(_jaccard(tags, st) for st in selected_tags)
            mmr_score = lam * rel - (1 - lam) * sim_to_selected
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i
        _, chosen = remaining.pop(best_idx)
        chosen["diversity_penalty"] = round(
            -(1 - lam) * max(
                (_jaccard(_item_tags(chosen, item_type), st) for st in selected_tags),
                default=0.0,
            ),
            4,
        )
        selected.append(chosen)
        selected_tags.append(_item_tags(chosen, item_type))

    return selected

# ---------------------------------------------------------------------------
# Explanation builder
# ---------------------------------------------------------------------------

def build_mentor_explanation(
    mentor: dict[str, Any],
    sub: dict[str, float],
    student_profile: dict[str, Any],
) -> str:
    parts: list[str] = []
    if sub["topic_similarity"] >= 0.3:
        mt = mentor.get("matched_topics") or []
        topic_str = ", ".join(mt[:3]) if mt else "shared topics"
        parts.append(f"Strong topic alignment ({topic_str})")
    if sub["skill_match"] >= 0.2:
        parts.append("Skill overlap with student profile")
    if sub["network_distance"] >= 0.5:
        parts.append("Close network proximity or high centrality")
    if sub["community"] >= 0.5:
        cid = mentor.get("community_id", "")
        parts.append(f"Same research community ({cid})")
    if sub["cold_start_bonus"] > 0:
        parts.append("Cold-start bonus applied (emerging mentor)")
    reasons = mentor.get("mentor_skill3_reasons") or mentor.get("reasons") or []
    if reasons:
        parts.append(reasons[0])
    return ". ".join(parts) if parts else "Recommended based on combined multi-objective scoring."


def build_project_explanation(proj: dict[str, Any], sub: dict[str, float]) -> str:
    parts: list[str] = []
    mi = proj.get("matched_interests") or []
    ms = proj.get("matched_skills") or []
    missing = proj.get("missing_skills") or []
    if mi:
        parts.append(f"Matches student interests: {', '.join(mi[:3])}")
    if ms:
        parts.append(f"Skill overlap: {', '.join(ms[:3])}")
    if missing:
        parts.append(f"Skill gaps to address: {', '.join(missing[:3])}")
    if sub["difficulty_match"] >= 0.9:
        parts.append("Appropriate difficulty for student grade")
    return ". ".join(parts) if parts else (proj.get("reason") or "Recommended project.")


def build_teammate_explanation(mate: dict[str, Any], sub: dict[str, float]) -> str:
    parts: list[str] = []
    si = mate.get("shared_interests") or []
    cs = mate.get("complementary_skills") or []
    if si:
        parts.append(f"Shared interests: {', '.join(si[:3])}")
    if cs:
        parts.append(f"Complementary skills: {', '.join(cs[:3])}")
    if sub["graph_relation"] > 0:
        parts.append("Graph-connected (shared interest / skill complementarity edge)")
    if sub["availability"] >= 0.9:
        parts.append("High availability")
    return ". ".join(parts) if parts else (mate.get("reason") or "Recommended teammate.")

# ---------------------------------------------------------------------------
# Per-student ranker
# ---------------------------------------------------------------------------

def rank_for_student(
    student_id: str,
    student_profile: dict[str, Any],
    skill3_mentors: list[dict[str, Any]],
    skill4_bundles: list[dict[str, Any]],
    mentor_weights: dict[str, float],
    project_weights: dict[str, float],
    teammate_weights: dict[str, float],
    top_k: int,
    cold_start_bonus: float,
    diversity_lambda: float,
) -> dict[str, Any]:
    """Produce final ranked lists for one student."""

    cold_start_student = _is_cold_start_student(student_profile)

    # ---- Build mentor list from Skill3 (preferred) or Skill4 bundles ----
    mentors_raw: list[dict[str, Any]] = []
    if skill3_mentors:
        mentors_raw = skill3_mentors
    else:
        # Fallback: reconstruct mentor stubs from Skill4 bundles
        for b in skill4_bundles:
            stub = {
                "mentor_id": b.get("mentor_id", ""),
                "mentor_name": b.get("mentor_name", ""),
                "final_score": b.get("mentor_base_score", 0.0),
                "topic_score": b.get("topic_score", 0.0),
                "graph_score": b.get("graph_score", 0.0),
                "activity_score": b.get("activity_score", 0.0),
                "centrality_score": b.get("centrality_score", 0.0),
                "network_proximity": b.get("network_proximity", 0.0),
                "community_id": b.get("community_id", ""),
                "mentor_skill3_reasons": b.get("mentor_skill3_reasons", []),
                "matched_topics": b.get("matched_topics", []),
                "mentor_profile": b.get("mentor_profile", {}),
            }
            mentors_raw.append(stub)

    # ---- Score and rank mentors ----
    mentor_scored: list[tuple[float, dict[str, Any]]] = []
    for m in mentors_raw:
        sub = score_mentor(m, student_profile, mentor_weights, cold_start_bonus)
        if cold_start_student:
            sub["cold_start_bonus"] = round(sub["cold_start_bonus"] + cold_start_bonus * 0.5, 4)
            sub["final_score"] = min(1.0, round(sub["final_score"] + cold_start_bonus * 0.5, 4))
        explanation = build_mentor_explanation(m, sub, student_profile)
        ranked_m = dict(m)
        ranked_m["scores"] = sub
        ranked_m["final_score"] = sub["final_score"]
        ranked_m["explanation"] = explanation
        mentor_scored.append((sub["final_score"], ranked_m))

    mentor_scored.sort(key=lambda x: -x[0])
    mentor_final = mmr_rerank(mentor_scored, "mentor", diversity_lambda, top_k)
    for rank_i, m in enumerate(mentor_final, 1):
        m["rank"] = rank_i

    # ---- Score and rank projects + teammates per mentor bundle ----
    project_scored: list[tuple[float, dict[str, Any]]] = []
    teammate_scored: list[tuple[float, dict[str, Any]]] = []
    seen_projects: set[str] = set()
    seen_teammates: set[str] = set()

    # Build mentor_id -> skill4_bundle index
    bundle_by_mid = {str(b.get("mentor_id") or ""): b for b in skill4_bundles}

    # Process in mentor rank order for coherence
    mentor_ids_ordered = [m.get("mentor_id", "") for m in mentor_final]
    # Also include any bundles not in top mentor list
    for b in skill4_bundles:
        mid = str(b.get("mentor_id") or "")
        if mid not in mentor_ids_ordered:
            mentor_ids_ordered.append(mid)

    for mid in mentor_ids_ordered:
        bundle = bundle_by_mid.get(mid)
        if not bundle:
            continue
        mbase = float(bundle.get("mentor_base_score", 0.0) or 0.0)

        for proj in bundle.get("project_recommendations") or []:
            pid = str(proj.get("project_id") or "")
            if pid in seen_projects:
                continue
            seen_projects.add(pid)
            sub = score_project(proj, mbase, project_weights)
            explanation = build_project_explanation(proj, sub)
            ranked_p = dict(proj)
            ranked_p["mentor_id"] = mid
            ranked_p["scores"] = sub
            ranked_p["final_score"] = sub["final_score"]
            ranked_p["explanation"] = explanation
            project_scored.append((sub["final_score"], ranked_p))

        for mate in bundle.get("teammate_recommendations") or []:
            tid_m = str(mate.get("student_id") or "")
            if tid_m in seen_teammates or tid_m == student_id:
                continue
            seen_teammates.add(tid_m)
            sub = score_teammate(mate, teammate_weights)
            explanation = build_teammate_explanation(mate, sub)
            ranked_t = dict(mate)
            ranked_t["scores"] = sub
            ranked_t["final_score"] = sub["final_score"]
            ranked_t["explanation"] = explanation
            teammate_scored.append((sub["final_score"], ranked_t))

    # Deduplicate projects/teammates preserving best score if seen across bundles
    project_scored.sort(key=lambda x: -x[0])
    teammate_scored.sort(key=lambda x: -x[0])

    project_final = mmr_rerank(project_scored, "project", diversity_lambda, top_k)
    teammate_final = mmr_rerank(teammate_scored, "teammate", diversity_lambda, top_k)

    for rank_i, p in enumerate(project_final, 1):
        p["rank"] = rank_i
    for rank_i, t in enumerate(teammate_final, 1):
        t["rank"] = rank_i

    return {
        "student_id": student_id,
        "student_profile": student_profile,
        "is_cold_start": cold_start_student,
        "recommendations": {
            "mentors":   mentor_final,
            "projects":  project_final,
            "teammates": teammate_final,
        },
        "summary": {
            "total_mentor_candidates":   len(mentors_raw),
            "total_project_candidates":  len(project_scored),
            "total_teammate_candidates": len(teammate_scored),
            "ranked_mentors":   len(mentor_final),
            "ranked_projects":  len(project_final),
            "ranked_teammates": len(teammate_final),
        },
    }

# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def to_csv_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in results:
        sid = r["student_id"]
        for rtype, items in r["recommendations"].items():
            for item in items:
                cid = item.get("mentor_id") or item.get("project_id") or item.get("student_id") or ""
                scores = item.get("scores") or {}
                rows.append({
                    "student_id":   sid,
                    "type":         rtype.rstrip("s"),
                    "candidate_id": cid,
                    "rank":         item.get("rank", ""),
                    "final_score":  item.get("final_score", ""),
                    "explanation":  item.get("explanation", ""),
                    **{f"score_{k}": v for k, v in scores.items()},
                })
    return rows


def to_markdown(results: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for r in results:
        sid = r["student_id"]
        lines.append(f"\n## Student: {sid}\n")
        for rtype in ("mentors", "projects", "teammates"):
            items = r["recommendations"][rtype]
            if not items:
                continue
            lines.append(f"### {rtype.capitalize()}\n")
            lines.append("| Rank | ID | Final Score | Explanation |")
            lines.append("|------|----|-------------|-------------|")
            for item in items:
                cid = item.get("mentor_id") or item.get("project_id") or item.get("student_id") or ""
                lines.append(
                    f"| {item.get('rank','')} | {cid} | {item.get('final_score','')} "
                    f"| {item.get('explanation','')[:80]} |"
                )
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Skill 5: Multi-Objective Joint Scoring & Re-Ranking"
    )
    parser.add_argument("--skill3",  default="", help="Skill 3 output JSON (mentor candidates)")
    parser.add_argument("--skill4",  default="", help="Skill 4 output JSON (project+teammate bundles)")
    parser.add_argument("--students", default="", help="Student profiles JSONL (Skill 1 format)")
    parser.add_argument("--output",  default="final_recommendation.json")
    parser.add_argument("--student-id", default="", help="Run for a specific student_id only")
    parser.add_argument("--top-k",   type=int, default=10)
    parser.add_argument("--weights", default="", help="Path to weights JSON override")
    parser.add_argument("--diversity-lambda", type=float, default=0.7)
    parser.add_argument("--cold-start-bonus", type=float, default=0.10)
    parser.add_argument("--format", choices=["json", "csv", "markdown"], default="json")
    args = parser.parse_args()

    # ---- Load skill3 ----
    skill3_mentors: list[dict[str, Any]] = []
    skill3_student_id: str = ""
    if args.skill3:
        raw3 = _load_json(args.skill3)
        skill3_mentors = _extract_mentor_candidates(raw3)
        if isinstance(raw3, dict):
            skill3_student_id = str(raw3.get("student_id") or raw3.get("target_student_id") or "")

    # ---- Load skill4 ----
    skill4_student_id: str = ""
    skill4_bundles: list[dict[str, Any]] = []
    skill4_target_profile: dict[str, Any] = {}
    if args.skill4:
        raw4 = _load_json(args.skill4)
        skill4_student_id, skill4_bundles = _extract_skill4_bundles(raw4)
        if isinstance(raw4, dict):
            skill4_target_profile = raw4.get("target_student_profile") or {}

    # ---- Load student profiles ----
    students_by_id: dict[str, dict[str, Any]] = {}
    if args.students:
        for rec in _load_jsonl(args.students):
            sid = str(rec.get("student_id") or "")
            if sid:
                students_by_id[sid] = rec

    # Determine target student(s)
    target_id = (args.student_id or skill3_student_id or skill4_student_id).strip()

    if target_id:
        target_ids = [target_id]
    elif students_by_id:
        target_ids = list(students_by_id.keys())
    else:
        target_ids = [skill4_student_id] if skill4_student_id else ["unknown"]

    # ---- Load weights ----
    mentor_weights = dict(DEFAULT_MENTOR_WEIGHTS)
    project_weights = dict(DEFAULT_PROJECT_WEIGHTS)
    teammate_weights = dict(DEFAULT_TEAMMATE_WEIGHTS)
    if args.weights:
        override = _load_json(args.weights)
        if isinstance(override, dict):
            mentor_weights.update(override.get("mentor", override))
            project_weights.update(override.get("project", {}))
            teammate_weights.update(override.get("teammate", {}))

    mentor_weights   = _normalize_weights(mentor_weights)
    project_weights  = _normalize_weights(project_weights)
    teammate_weights = _normalize_weights(teammate_weights)

    # ---- Run ranking ----
    all_results: list[dict[str, Any]] = []
    for sid in target_ids:
        # Resolve profile: students file > skill4 embedded profile > empty
        profile = students_by_id.get(sid) or {}
        if not profile and sid == skill4_student_id and skill4_target_profile:
            profile = {**skill4_target_profile, "student_id": sid}
        if not profile:
            profile = {"student_id": sid}

        # skill3 mentors are valid only for the declared target student
        use_s3 = skill3_mentors if sid in (skill3_student_id, "") else []

        result = rank_for_student(
            student_id=sid,
            student_profile=profile,
            skill3_mentors=use_s3,
            skill4_bundles=skill4_bundles if sid == skill4_student_id or not skill4_student_id else [],
            mentor_weights=mentor_weights,
            project_weights=project_weights,
            teammate_weights=teammate_weights,
            top_k=args.top_k,
            cold_start_bonus=args.cold_start_bonus,
            diversity_lambda=args.diversity_lambda,
        )
        all_results.append(result)

    # ---- Write output ----
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "json":
        payload = all_results[0] if len(all_results) == 1 else all_results
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    elif args.format == "csv":
        rows = to_csv_rows(all_results)
        if rows:
            with out_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

    elif args.format == "markdown":
        out_path.write_text(to_markdown(all_results), encoding="utf-8")

    print(f"[Skill5] Wrote final_recommendation to {out_path}")
    if all_results:
        r = all_results[0]
        rec = r["recommendations"]
        print(
            f"[Skill5] Student {r['student_id']}: "
            f"{len(rec['mentors'])} mentors, "
            f"{len(rec['projects'])} projects, "
            f"{len(rec['teammates'])} teammates ranked"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
