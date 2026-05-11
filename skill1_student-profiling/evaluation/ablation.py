"""Ablation study - quantify contribution of each pipeline component.

Runs 5 configurations and compares coverage/consistency metrics:
  Baseline:          structured fields only (Major + Hobbies as-is)
  + Taxonomy:        add major→skills, hobby→interests mappings
  + UQ Mapping:      add Unique Quality inference
  + Story Extraction: add regex-based narrative extraction
  Full Pipeline:     all components combined
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from metrics import (
    count_stats,
    experience_nonempty_rate,
    load_major_skills,
    major_skill_consistency,
    vocabulary_stats,
)


def load_records(path: str) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def run_baseline(records: list[dict]) -> list[dict]:
    """Baseline: Major as-is, Hobbies as-is, no normalization."""
    profiles = []
    for i, r in enumerate(records):
        profiles.append({
            "student_id": f"baseline-{i:05d}",
            "grade": r["Year"],
            "major": r["Major"],
            "skills": [r["Major"].lower()],
            "interests": [h.lower() for h in r["Hobbies"]],
            "experience_summary": r["Story"][:100],
            "availability": "moderate",
        })
    return profiles


def run_with_taxonomy(records: list[dict]) -> list[dict]:
    """+ Taxonomy: major→skills, hobby→interests mappings."""
    from student_profiling.taxonomy.mappings import get_interests_from_hobbies, get_skills_from_major
    profiles = []
    for i, r in enumerate(records):
        skills, _ = get_skills_from_major(r["Major"])
        interests, _ = get_interests_from_hobbies(r["Hobbies"])
        profiles.append({
            "student_id": f"taxonomy-{i:05d}",
            "grade": r["Year"],
            "major": r["Major"],
            "skills": skills or [r["Major"].lower()],
            "interests": interests or [h.lower() for h in r["Hobbies"]],
            "experience_summary": r["Story"][:100],
            "availability": "moderate",
        })
    return profiles


def run_with_uq(records: list[dict]) -> list[dict]:
    """+ UQ Mapping: add Unique Quality inference."""
    from student_profiling.taxonomy.mappings import (
        get_interests_from_hobbies,
        get_skills_from_major,
        get_terms_from_uq,
    )
    profiles = []
    for i, r in enumerate(records):
        skills, _ = get_skills_from_major(r["Major"])
        interests, _ = get_interests_from_hobbies(r["Hobbies"])
        uq_skills, _, uq_interests, _ = get_terms_from_uq(r["Unique Quality"])
        skills = list(dict.fromkeys(skills + uq_skills))
        interests = list(dict.fromkeys(interests + uq_interests))
        profiles.append({
            "student_id": f"uq-{i:05d}",
            "grade": r["Year"],
            "major": r["Major"],
            "skills": skills or [r["Major"].lower()],
            "interests": interests or [h.lower() for h in r["Hobbies"]],
            "experience_summary": r["Story"][:100],
            "availability": "moderate",
        })
    return profiles


def run_full_pipeline(records: list[dict]) -> list[dict]:
    """Full pipeline: all components."""
    from student_profiling import StudentProfilingSkill
    skill = StudentProfilingSkill()
    return skill.batch_profile(records)


def compute_metrics(profiles: list[dict], major_skills: dict) -> dict:
    sk = count_stats(profiles, "skills")
    it = count_stats(profiles, "interests")
    return {
        "avg_skills": round(sk["avg"], 2),
        "avg_interests": round(it["avg"], 2),
        "skills_ge3_pct": round(sk["pct_ge3"] * 100, 1),
        "interests_ge3_pct": round(it["pct_ge3"] * 100, 1),
        "major_skill_consistency_pct": round(major_skill_consistency(profiles, major_skills) * 100, 1),
        "unique_skill_terms": vocabulary_stats(profiles)["unique_skill_terms"],
        "experience_nonempty_pct": round(experience_nonempty_rate(profiles) * 100, 1),
    }


def print_ablation_table(results: dict[str, dict]) -> None:
    configs = list(results.keys())
    metrics = ["avg_skills", "avg_interests", "skills_ge3_pct", "interests_ge3_pct",
               "major_skill_consistency_pct", "unique_skill_terms", "experience_nonempty_pct"]
    labels = ["Avg Skills", "Avg Interests", "Skills≥3 %", "Interests≥3 %",
              "Major-Skill %", "Unique Terms", "Exp Non-empty %"]

    print("\n" + "=" * 90)
    print("  Ablation Study — Component Contribution Analysis")
    print("=" * 90)
    header = f"{'Metric':<22}" + "".join(f"{c:<18}" for c in configs)
    print(header)
    print("-" * 90)
    for metric, label in zip(metrics, labels):
        row = f"{label:<22}"
        for config in configs:
            val = results[config].get(metric, "—")
            row += f"{str(val):<18}"
        print(row)
    print("=" * 90 + "\n")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Ablation study for Student Profiling Skill")
    parser.add_argument("--input", default="../student_profiles.jsonl")
    parser.add_argument("--limit", type=int, default=500, help="Records to use (default 500)")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    print(f"Loading {args.limit} records from {args.input}...")
    all_records = load_records(args.input)
    records = all_records[:args.limit]

    major_skills = load_major_skills(
        Path(__file__).parent.parent / "src/student_profiling/taxonomy/data/major_skills.json"
    )

    print("Running ablation configurations...")
    configs = {
        "Baseline": run_baseline(records),
        "+ Taxonomy": run_with_taxonomy(records),
        "+ UQ": run_with_uq(records),
        "Full Pipeline": run_full_pipeline(records),
    }

    results = {name: compute_metrics(profiles, major_skills) for name, profiles in configs.items()}
    print_ablation_table(results)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
