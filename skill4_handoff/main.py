#!/usr/bin/env python3
"""CLI entry for Skill 4 — Project & Teammate Discovery."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Package root (directory containing `skill/`)
_PTD = Path(__file__).resolve().parent
if str(_PTD) not in sys.path:
    sys.path.insert(0, str(_PTD))

from skill.discovery import run_pipeline_from_cli_config, try_load_embedding_context  # noqa: E402


def _repo_root() -> Path:
    """Course repo root: parent of ``skill4_handoff``."""
    return _PTD.parent


def _first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.is_file():
            return p
    return None


def build_arg_parser() -> argparse.ArgumentParser:
    root = _repo_root()
    p = argparse.ArgumentParser(description="Skill 4: project & teammate discovery")
    p.add_argument("--target-student-id", default="", help="Target student_id (default: first in bundle)")
    p.add_argument(
        "--skill1-profiles",
        default=str(root / "skill1_handoff/student_profiles_normalized.jsonl"),
        help="Skill 1 JSONL",
    )
    p.add_argument(
        "--skill2-graph",
        default="",
        help="academic_graph.json (empty = auto-resolve)",
    )
    p.add_argument(
        "--skill2-students",
        default="",
        help="student_profiles_standard.json (empty = auto-resolve)",
    )
    p.add_argument(
        "--skill2-mentors",
        default="",
        help="mentor_profiles_standard.json (empty = auto-resolve)",
    )
    p.add_argument(
        "--skill2-embeddings",
        default=str(root / "skill2_handoff/outputs/student_embeddings_aligned.npy"),
        help="Optional aligned embeddings (missing = keyword-only)",
    )
    p.add_argument(
        "--skill2-student-ids",
        default=str(root / "skill2_handoff/outputs/student_ids_aligned.json"),
        help="IDs aligned with embeddings rows",
    )
    p.add_argument(
        "--mentor-candidates",
        default="",
        help="Skill 3 mentor JSON path (optional; list or {mentor_candidates: [...]})",
    )
    p.add_argument(
        "--skill3-output",
        default="",
        help="Same as --mentor-candidates if set; takes precedence when both are provided",
    )
    p.add_argument(
        "--projects",
        default=str(_PTD / "data/mock_projects.json"),
        help="Fallback project list JSON",
    )
    p.add_argument(
        "--mock-mentor-candidates",
        default=str(_PTD / "data/mock_mentor_candidates.json"),
        help="Used only if graph + mentor JSON yield no candidates",
    )
    p.add_argument(
        "--output",
        default=str(_PTD / "outputs/skill4_output.json"),
        help="Write Skill 4 JSON here",
    )
    p.add_argument("--top-n-projects", type=int, default=3)
    p.add_argument("--top-n-teammates", type=int, default=3)
    p.add_argument("--max-candidate-teammates", type=int, default=120)
    p.add_argument("--fallback-mentor-top-k", type=int, default=10)
    p.add_argument(
        "--strict-target-student",
        action="store_true",
        help="Fail if --target-student-id is missing from merged Skill 1 + Skill 2 student sources",
    )
    p.add_argument(
        "--allow-target-fallback-with-skill3",
        action="store_true",
        help="When combined with --skill3-output, allow missing target_student_id to fall back to the first student in the bundle (default: forbid fallback to stay aligned with Skill 3)",
    )
    return p


def resolve_paths(args: argparse.Namespace) -> dict[str, object]:
    root = _repo_root()
    graph = args.skill2_graph or _first_existing(
        [
            root / "skill2_handoff/outputs/academic_graph.json",
            root / "skill2_handoff/regenerate_kit/data/processed/academic_graph.json",
            root / "data/processed/academic_graph.json",
        ]
    )
    students = args.skill2_students or _first_existing(
        [
            root / "skill2_handoff/outputs/student_profiles_standard.json",
            root / "skill2_handoff/regenerate_kit/data/processed/student_profiles_standard.json",
            root / "data/processed/student_profiles_standard.json",
        ]
    )
    mentors = args.skill2_mentors or _first_existing(
        [
            root / "skill2_handoff/outputs/mentor_profiles_standard.json",
            root / "skill2_handoff/regenerate_kit/data/processed/mentor_profiles_standard.json",
            root / "data/processed/mentor_profiles_standard.json",
        ]
    )
    emb_ctx = try_load_embedding_context(
        Path(args.skill2_embeddings) if args.skill2_embeddings else None,
        Path(args.skill2_student_ids) if args.skill2_student_ids else None,
    )
    skill3_out = (args.skill3_output or "").strip()
    mentor_can = (args.mentor_candidates or "").strip()
    return {
        "target_student_id": args.target_student_id,
        "skill1_profiles_path": args.skill1_profiles,
        "skill2_graph_path": str(graph) if graph else "",
        "skill2_students_path": str(students) if students else "",
        "skill2_mentors_path": str(mentors) if mentors else "",
        "mentor_candidates_path": skill3_out or mentor_can,
        "skill3_output_path": skill3_out,
        "mock_projects_path": args.projects,
        "mock_mentor_candidates_path": args.mock_mentor_candidates,
        "output_path": args.output,
        "top_n_projects": args.top_n_projects,
        "top_n_teammates": args.top_n_teammates,
        "max_candidate_teammates": args.max_candidate_teammates,
        "fallback_mentor_top_k": args.fallback_mentor_top_k,
        "strict_target_student": args.strict_target_student,
        "allow_target_fallback_with_skill3": args.allow_target_fallback_with_skill3,
        "_embedding_context": emb_ctx,
    }


def main() -> int:
    args = build_arg_parser().parse_args()
    cfg = resolve_paths(args)
    try:
        body = run_pipeline_from_cli_config(cfg)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if cfg.get("_embedding_context"):
        body.setdefault("data_sources", {})["embeddings_aligned"] = "loaded_ok"
    else:
        body.setdefault("data_sources", {})["embeddings_aligned"] = "skipped_or_unavailable"
    out_path = Path(str(cfg["output_path"]))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
