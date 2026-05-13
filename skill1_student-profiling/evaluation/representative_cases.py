"""Export small representative cases for appendix use."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from student_profiling import StudentProfilingSkill


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def build_profiles_from_raw(raw_records: list[dict], limit: int) -> list[dict]:
    skill = StudentProfilingSkill()
    return [skill.profile(record, index=index) for index, record in enumerate(raw_records[:limit])]


def build_cases(raw_records: list[dict], profiles: list[dict], limit: int) -> list[dict]:
    selected: list[dict] = []
    for raw, profile in zip(raw_records[:limit], profiles[:limit]):
        selected.append(
            {
                "name": raw["Name"],
                "major": raw["Major"],
                "story_excerpt": raw["Story"][:220],
                "skills": profile["skills"],
                "interests": profile["interests"],
                "availability": profile["availability"],
            }
        )
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Export representative Skill 1 cases")
    parser.add_argument("--raw-input", default="../student_profiles.jsonl")
    parser.add_argument("--profiles", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", default="evaluation/representative_cases.json")
    args = parser.parse_args()

    raw_records = load_jsonl(Path(args.raw_input))
    if args.profiles:
        profiles = load_jsonl(Path(args.profiles))
    else:
        profiles = build_profiles_from_raw(raw_records, args.limit)

    payload = build_cases(raw_records, profiles, args.limit)
    Path(args.output).write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
