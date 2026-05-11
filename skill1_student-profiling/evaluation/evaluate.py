"""Main evaluation script - runs all automated metrics and optionally gold-label metrics.

Usage:
    python evaluation/evaluate.py --profiles outputs/student_profiles_normalized.jsonl
    python evaluation/evaluate.py --profiles outputs/student_profiles_normalized.jsonl \
        --gold evaluation/gold_annotations.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

sys.path.insert(0, str(Path(__file__).parent))
from metrics import (
    availability_accuracy,
    availability_distribution,
    count_stats,
    experience_nonempty_rate,
    field_completeness,
    interests_coverage,
    load_major_skills,
    load_profiles,
    macro_prf1,
    major_skill_consistency,
    skills_coverage,
    vocabulary_stats,
)


def run_automated_metrics(profiles: list[dict], major_skills: dict) -> dict:
    n = len(profiles)
    results = {}

    # Field completeness
    results["field_completeness"] = field_completeness(profiles)

    # Coverage
    results["skills_coverage_ge3"] = skills_coverage(profiles, min_count=3)
    results["interests_coverage_ge3"] = interests_coverage(profiles, min_count=3)
    results["experience_nonempty_rate"] = experience_nonempty_rate(profiles)

    # Count stats
    results["skills_stats"] = count_stats(profiles, "skills")
    results["interests_stats"] = count_stats(profiles, "interests")

    # Consistency
    results["major_skill_consistency"] = major_skill_consistency(profiles, major_skills)

    # Availability distribution
    results["availability_distribution"] = availability_distribution(profiles)

    # Vocabulary
    results["vocabulary"] = vocabulary_stats(profiles)

    results["total_profiles"] = n
    return results


def print_report(results: dict, gold_results: dict | None = None) -> None:
    n = results["total_profiles"]
    print(f"\n{'='*60}")
    print(f"  Student Profiling Skill — Evaluation Report")
    print(f"  Total profiles: {n:,}")
    print(f"{'='*60}")

    print("\n── Field Completeness ──────────────────────────────────")
    for field, rate in results["field_completeness"].items():
        status = "✓" if rate == 1.0 else ("~" if rate >= 0.9 else "✗")
        print(f"  {status} {field:<25} {rate*100:.1f}%")

    print("\n── Coverage ────────────────────────────────────────────")
    sk = results["skills_stats"]
    it = results["interests_stats"]
    print(f"  Skills:    min={sk['min']}, max={sk['max']}, avg={sk['avg']:.2f}, "
          f">=3: {sk['pct_ge3']*100:.1f}%")
    print(f"  Interests: min={it['min']}, max={it['max']}, avg={it['avg']:.2f}, "
          f">=3: {it['pct_ge3']*100:.1f}%")
    print(f"  Experience non-empty: {results['experience_nonempty_rate']*100:.1f}%")

    print("\n── Consistency ─────────────────────────────────────────")
    cons = results["major_skill_consistency"]
    print(f"  Major-skill consistency: {cons*100:.1f}%  (target: 100%)")

    print("\n── Availability Distribution ───────────────────────────")
    for k, v in results["availability_distribution"].items():
        print(f"  {k:<10} {v*100:.1f}%")

    print("\n── Vocabulary ──────────────────────────────────────────")
    voc = results["vocabulary"]
    print(f"  Unique skill terms:    {voc['unique_skill_terms']:,}")
    print(f"  Unique interest terms: {voc['unique_interest_terms']:,}")
    print(f"  Skill entropy:         {voc['skill_frequency_entropy']:.3f}  (target: >4.0)")
    print(f"  Interest entropy:      {voc['interest_frequency_entropy']:.3f}")
    print(f"  Top 10 skills:    {voc['top10_skills']}")
    print(f"  Top 10 interests: {voc['top10_interests']}")

    if gold_results:
        print("\n── Gold-Label Metrics ──────────────────────────────────")
        for field in ["skills", "interests"]:
            m = gold_results.get(f"{field}_prf1", {})
            print(f"  {field.capitalize():<12} P={m.get('precision',0):.3f}  "
                  f"R={m.get('recall',0):.3f}  F1={m.get('f1',0):.3f}")
        acc = gold_results.get("availability_accuracy", None)
        if acc is not None:
            print(f"  Availability accuracy: {acc*100:.1f}%")

    print(f"\n{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Student Profiling Skill")
    parser.add_argument(
        "--profiles",
        default="outputs/student_profiles_normalized.jsonl",
        help="Path to normalized profiles JSONL",
    )
    parser.add_argument(
        "--gold",
        default=None,
        help="Path to gold annotations JSON (optional)",
    )
    parser.add_argument(
        "--taxonomy",
        default="src/student_profiling/taxonomy/data/major_skills.json",
        help="Path to major_skills.json",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Save results to JSON file (optional)",
    )
    args = parser.parse_args()

    profiles = load_profiles(args.profiles)
    major_skills = load_major_skills(args.taxonomy)

    results = run_automated_metrics(profiles, major_skills)

    gold_results = None
    if args.gold and Path(args.gold).exists():
        with open(args.gold) as f:
            gold_data = json.load(f)

        # Match profiles to gold by student_id
        gold_by_id = {g["student_id"]: g for g in gold_data}
        matched_profiles = []
        matched_gold = []
        for p in profiles:
            if p["student_id"] in gold_by_id:
                matched_profiles.append(p)
                matched_gold.append(gold_by_id[p["student_id"]])

        if matched_profiles:
            gold_results = {
                "skills_prf1": macro_prf1(matched_profiles, matched_gold, "skills"),
                "interests_prf1": macro_prf1(matched_profiles, matched_gold, "interests"),
                "availability_accuracy": availability_accuracy(matched_profiles, matched_gold),
                "n_annotated": len(matched_profiles),
            }

    print_report(results, gold_results)

    if args.output:
        combined = {"automated": results}
        if gold_results:
            combined["gold_label"] = gold_results
        with open(args.output, "w") as f:
            json.dump(combined, f, indent=2)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
