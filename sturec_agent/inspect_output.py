#!/usr/bin/env python3
"""Read-only inspection of Skill 5-style final recommendation JSON (stdout + optional stderr warnings)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Print summary and recommendation list sizes from a joint_ranker / run_agent final JSON.",
    )
    p.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to final JSON (e.g. outputs/final_recommendation_graph.json).",
    )
    args = p.parse_args(argv)
    path = args.output
    if not path.is_file():
        print(f"ERROR: not a file: {path}", file=sys.stderr)
        return 1

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {path}: {exc}", file=sys.stderr)
        return 1

    summary = data.get("summary")
    if not isinstance(summary, dict):
        print(
            "Note: this file has no object 'summary' — likely Skill 4-only output (--skip-skill5), not joint_ranker.",
            file=sys.stderr,
        )
        return 0

    print(f"File: {path.resolve()}\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print()

    recs = data.get("recommendations")
    if isinstance(recs, dict):
        mentors = recs.get("mentors")
        projects = recs.get("projects")
        teammates = recs.get("teammates")
        nm = len(mentors) if isinstance(mentors, list) else 0
        np_ = len(projects) if isinstance(projects, list) else 0
        nt = len(teammates) if isinstance(teammates, list) else 0
        print("Top-level list lengths under recommendations:")
        print(f"  mentors:   {nm}")
        print(f"  projects: {np_}")
        print(f"  teammates: {nt}")
    else:
        print("(No 'recommendations' object; summary only.)")

    ranked_projects = summary.get("ranked_projects")
    if ranked_projects == 0:
        print(
            "\nWARNING: ranked_projects is 0 — no projects made it into the final ranked list. "
            "Check Skill 4 project_source, graph mentor–project coverage, and Skill 3 mentor overlap.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
