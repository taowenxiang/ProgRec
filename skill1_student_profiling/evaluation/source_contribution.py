"""Export source contribution counts from extended profile outputs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from student_profiling import StudentProfilingSkill


def load_profiles(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def build_source_contribution(profiles: list[dict]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for profile in profiles:
        for source_lists in profile.get("sources", {}).get("skills", {}).values():
            counter.update(source_lists)
        for source_lists in profile.get("sources", {}).get("interests", {}).values():
            counter.update(source_lists)
    return dict(counter)


def build_extended_profiles_from_raw(path: Path, limit: int | None = None) -> list[dict]:
    skill = StudentProfilingSkill()
    profiles: list[dict] = []
    for index, line in enumerate(path.read_text().splitlines()):
        if not line.strip():
            continue
        if limit is not None and len(profiles) >= limit:
            break
        profiles.append(skill.profile_extended(json.loads(line), index=index))
    return profiles


def main() -> None:
    parser = argparse.ArgumentParser(description="Export source contribution summary")
    parser.add_argument(
        "--profiles",
        default=None,
        help="Optional path to extended profile JSONL",
    )
    parser.add_argument(
        "--raw-input",
        default=None,
        help="Optional raw input JSONL used to generate extended profiles on the fly",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit when generating from raw input",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write JSON output",
    )
    args = parser.parse_args()

    if args.profiles:
        profiles = load_profiles(Path(args.profiles))
    elif args.raw_input:
        profiles = build_extended_profiles_from_raw(Path(args.raw_input), limit=args.limit)
    else:
        raise SystemExit("Pass either --profiles or --raw-input.")

    payload = build_source_contribution(profiles)
    text = json.dumps(payload, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
