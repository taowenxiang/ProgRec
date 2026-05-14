"""Automated evaluation metrics for Student Profiling Skill.

All metrics work without ground-truth labels (proxy/coverage metrics).
Gold-label metrics (precision/recall/F1) are computed separately in evaluate.py.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path


def load_profiles(path: str | Path) -> list[dict]:
    profiles = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                profiles.append(json.loads(line))
    return profiles


def load_major_skills(path: str | Path) -> dict[str, list[str]]:
    with open(path) as f:
        return json.load(f)


# ── Field completeness ────────────────────────────────────────────────────────

def field_completeness(profiles: list[dict]) -> dict[str, float]:
    """Fraction of profiles where each required field is non-empty."""
    required = ["student_id", "grade", "major", "skills", "interests",
                "experience_summary", "availability"]
    n = len(profiles)
    return {
        field: sum(1 for p in profiles if p.get(field)) / n
        for field in required
    }


# ── Coverage metrics ──────────────────────────────────────────────────────────

def skills_coverage(profiles: list[dict], min_count: int = 3) -> float:
    """Fraction of profiles with >= min_count skills."""
    return sum(1 for p in profiles if len(p.get("skills", [])) >= min_count) / len(profiles)


def interests_coverage(profiles: list[dict], min_count: int = 3) -> float:
    """Fraction of profiles with >= min_count interests."""
    return sum(1 for p in profiles if len(p.get("interests", [])) >= min_count) / len(profiles)


def experience_nonempty_rate(profiles: list[dict]) -> float:
    """Fraction of profiles with non-empty experience_summary."""
    return sum(1 for p in profiles if p.get("experience_summary", "").strip()) / len(profiles)


def count_stats(profiles: list[dict], field: str) -> dict:
    counts = [len(p.get(field, [])) for p in profiles]
    return {
        "min": min(counts),
        "max": max(counts),
        "avg": sum(counts) / len(counts),
        "pct_ge3": sum(1 for c in counts if c >= 3) / len(counts),
    }


# ── Consistency metrics ───────────────────────────────────────────────────────

def major_skill_consistency(
    profiles: list[dict],
    major_skills: dict[str, list[str]],
) -> float:
    """Fraction of profiles where >= 1 skill comes from the major taxonomy."""
    consistent = sum(
        1 for p in profiles
        if any(s in major_skills.get(p["major"], []) for s in p.get("skills", []))
    )
    return consistent / len(profiles)


def availability_distribution(profiles: list[dict]) -> dict[str, float]:
    """Distribution of availability values."""
    n = len(profiles)
    counts = Counter(p.get("availability") for p in profiles)
    return {k: counts[k] / n for k in ["high", "moderate", "low"]}


# ── Vocabulary metrics ────────────────────────────────────────────────────────

def vocabulary_stats(profiles: list[dict]) -> dict:
    """Unique term counts and frequency entropy."""
    all_skills = [s for p in profiles for s in p.get("skills", [])]
    all_interests = [i for p in profiles for i in p.get("interests", [])]

    skill_entropy = _shannon_entropy(Counter(all_skills))
    interest_entropy = _shannon_entropy(Counter(all_interests))

    return {
        "unique_skill_terms": len(set(all_skills)),
        "unique_interest_terms": len(set(all_interests)),
        "skill_frequency_entropy": round(skill_entropy, 3),
        "interest_frequency_entropy": round(interest_entropy, 3),
        "top10_skills": [t for t, _ in Counter(all_skills).most_common(10)],
        "top10_interests": [t for t, _ in Counter(all_interests).most_common(10)],
    }


def _shannon_entropy(counter: Counter) -> float:
    total = sum(counter.values())
    if total == 0:
        return 0.0
    return -sum((c / total) * math.log2(c / total) for c in counter.values() if c > 0)


# ── Gold-label metrics (precision / recall / F1) ─────────────────────────────

def set_precision_recall_f1(
    predicted: list[str],
    gold: list[str],
) -> dict[str, float]:
    """Compute P/R/F1 for a single profile's set of terms."""
    pred_set = set(predicted)
    gold_set = set(gold)
    if not pred_set and not gold_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not pred_set:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    if not gold_set:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    tp = len(pred_set & gold_set)
    precision = tp / len(pred_set)
    recall = tp / len(gold_set)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def macro_prf1(
    profiles: list[dict],
    gold_annotations: list[dict],
    field: str,
) -> dict[str, float]:
    """Macro-averaged P/R/F1 over all annotated profiles for a given field."""
    scores = []
    for profile, gold in zip(profiles, gold_annotations):
        pred = profile.get(field, [])
        gold_vals = gold.get(field, [])
        scores.append(set_precision_recall_f1(pred, gold_vals))

    return {
        "precision": sum(s["precision"] for s in scores) / len(scores),
        "recall": sum(s["recall"] for s in scores) / len(scores),
        "f1": sum(s["f1"] for s in scores) / len(scores),
    }


def availability_accuracy(
    profiles: list[dict],
    gold_annotations: list[dict],
) -> float:
    """Exact-match accuracy for availability field."""
    correct = sum(
        1 for p, g in zip(profiles, gold_annotations)
        if p.get("availability") == g.get("availability")
    )
    return correct / len(profiles)
