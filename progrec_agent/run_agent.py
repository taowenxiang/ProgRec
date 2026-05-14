#!/usr/bin/env python3
"""Non-interactive ProgRec Agent — batch pipeline (Skills 3 → 4 → 5).

Uses :mod:`progrec_agent.config` for demo vs graph paths and :mod:`progrec_agent.schemas`
for preflight / post-run checks. Example::

    python3 progrec_agent/run_agent.py --mode graph --student-id jamie-taylor-00008 --output outputs/final.json
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root_for_import = Path(__file__).resolve().parents[1]
if str(_repo_root_for_import) not in sys.path:
    sys.path.insert(0, str(_repo_root_for_import))

import argparse
import json
import shutil
import subprocess
import tempfile
from typing import Any

from progrec_agent.config import ResourceConfig, resolve_repo_root, resolve_resource_config
from progrec_agent.schemas import (
    assert_same_student_id,
    validate_skill3_output,
    validate_skill4_output,
    validate_skill5_output,
    validate_student_profiles,
)


def _ensure_repo_on_path(repo_root: Path) -> None:
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run ProgRec pipeline (Skill 3 → 4 → 5) for one student_id.",
    )
    p.add_argument(
        "--student-id",
        default=None,
        help="Target student_id (must exist in the mode's student_profiles_standard.json). "
        "Omitted: use first student from that bundle when available.",
    )
    p.add_argument(
        "--mode",
        choices=("demo", "graph"),
        default="demo",
        help="demo: outputs bundles + mock academic graph. graph: regenerate processed bundle (strict; no demo fallback).",
    )
    p.add_argument(
        "--top-k",
        "--top-k-mentors",
        type=int,
        default=5,
        dest="top_k",
        help="Top-K mentors for Skill 3 and Skill 5 ranking cap.",
    )
    p.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Write final JSON here (Skill 5 shape unless --skip-skill5, then Skill 4 body).",
    )
    p.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Optional temp directory for skill3/4/5 JSON; default is a new tempfile directory.",
    )
    p.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help="If set, copy intermediate JSON files into this directory after the run.",
    )
    p.add_argument(
        "--keep-work-dir",
        action="store_true",
        help="When using a tempfile work dir, keep it after the run and print its path.",
    )
    p.add_argument(
        "--list-students",
        action="store_true",
        help="Print up to 20 student_id values from the mode's student bundle and exit.",
    )
    p.add_argument(
        "--skip-skill5",
        action="store_true",
        help="Stop after Skill 4; write Skill 4 JSON to --output (not joint_ranker shape).",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print extra preflight and validation details to stderr.",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Override repository root (default: ancestor of progrec_agent/ with skill1_student_profiling/).",
    )
    return p.parse_args(argv)


def _copy_if_requested(src: Path, dest_dir: Path, name: str) -> None:
    if src.is_file():
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_dir / name)


def _warn_skill3_resource_alignment(bundle: ResourceConfig, skill3_result: dict[str, Any]) -> None:
    """Warn if Skill 3 ``data_sources`` disagree with graph ``ResourceConfig`` paths."""
    ds = skill3_result.get("data_sources") or {}
    if ds.get("resource_mode") != "explicit":
        print(
            f"WARNING: Skill 3 expected resource_mode 'explicit' for graph mode; got {ds.get('resource_mode')!r}.",
            file=sys.stderr,
        )
    exp_s = str(bundle.skill2_students.resolve())
    exp_m = str(bundle.skill2_mentors.resolve())
    exp_g = str(bundle.skill2_graph.resolve()) if bundle.skill2_graph else ""
    if ds.get("student_profiles") != exp_s:
        print(
            f"WARNING: Skill 3 student_profiles ({ds.get('student_profiles')!r}) != bundle ({exp_s}).",
            file=sys.stderr,
        )
    if ds.get("mentor_profiles") != exp_m:
        print(
            f"WARNING: Skill 3 mentor_profiles ({ds.get('mentor_profiles')!r}) != bundle ({exp_m}).",
            file=sys.stderr,
        )
    if exp_g and ds.get("academic_graph") != exp_g:
        print(
            f"WARNING: Skill 3 academic_graph ({ds.get('academic_graph')!r}) != bundle ({exp_g}).",
            file=sys.stderr,
        )


def _preflight_print(bundle: ResourceConfig, student_id: str, verbose: bool) -> None:
    print(f"Mode: {bundle.mode}", file=sys.stderr)
    print(f"Student profiles: {bundle.skill2_students}", file=sys.stderr)
    print(f"Mentor profiles: {bundle.skill2_mentors}", file=sys.stderr)
    print(f"Graph path: {bundle.skill2_graph}", file=sys.stderr)
    print(f"Skill 1 profiles: {bundle.skill1_profiles}", file=sys.stderr)
    print(f"Selected student_id: {student_id}", file=sys.stderr)
    if verbose:
        print(f"default_student_id (bundle): {bundle.default_student_id}", file=sys.stderr)


def _resolve_student_id(bundle: ResourceConfig, student_id: str | None) -> str:
    sid = (student_id or "").strip()
    if sid:
        return sid
    if bundle.default_student_id:
        return bundle.default_student_id
    raise SystemExit(
        "No --student-id provided and could not infer default (student bundle missing or empty). "
        "Pass --student-id or use --list-students."
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = resolve_repo_root(args.repo_root)
    _ensure_repo_on_path(repo_root)

    from progrec_agent.orchestrator import ProgRecOrchestrator

    try:
        bundle = resolve_resource_config(args.mode, repo_root, validate_graph=True)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.list_students:
        info = validate_student_profiles(bundle.skill2_students)
        print(f"student_id count: {info['count']}")
        for sid in info["sample_ids"][:20]:
            print(sid)
        if info["count"] > 20:
            print(f"... ({info['count']} total, showing 20)", file=sys.stderr)
        return 0

    student_id = _resolve_student_id(bundle, args.student_id)
    _preflight_print(bundle, student_id, args.verbose)

    try:
        prof = validate_student_profiles(bundle.skill2_students)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if student_id not in prof.get("all_student_ids", []):
        sample = prof.get("sample_ids") or []
        print(
            f"student_id {student_id!r} not found in {bundle.skill2_students}. "
            f"First available ids (up to 10): {sample[:10]}",
            file=sys.stderr,
        )
        return 2

    cleanup = False
    if args.work_dir is not None:
        work = args.work_dir
        work.mkdir(parents=True, exist_ok=True)
    else:
        work = Path(tempfile.mkdtemp(prefix="progrec_run_"))
        cleanup = not args.keep_work_dir

    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=work)
    result: dict[str, Any] | None = None
    exit_code = 0
    try:
        try:
            result = orchestrator.recommend_for_student_id(
                student_id,
                top_k=args.top_k,
                bundle=bundle,
                skip_skill5=args.skip_skill5,
            )
        except StopIteration:
            print(
                f"Internal error: student_id {student_id!r} missing after preflight.",
                file=sys.stderr,
            )
            exit_code = 1
        except FileNotFoundError as exc:
            print(f"Missing input file: {exc}", file=sys.stderr)
            exit_code = 1
        except subprocess.CalledProcessError as exc:
            err = (exc.stderr or "").strip() or (exc.stdout or "").strip() or str(exc)
            print(f"Skill 5 subprocess failed: {err}", file=sys.stderr)
            exit_code = 1
        except ValueError as exc:
            if "Student ID mismatch before Skill 5" in str(exc):
                print(str(exc), file=sys.stderr)
            else:
                print(f"Resource / graph error: {exc}", file=sys.stderr)
            exit_code = 2

        if result is not None and exit_code == 0 and bundle is not None and bundle.mode == "graph":
            _warn_skill3_resource_alignment(bundle, result.get("skill3_result") or {})

        if result is not None and exit_code == 0:
            paths = [Path(str(p)) for p in (result.get("temporary_paths") or [])]
            skill3_path = paths[0] if paths else None
            skill4_path = paths[1] if len(paths) > 1 else None
            skill5_path = paths[2] if len(paths) > 2 else None
            try:
                assert_same_student_id(skill3_path, skill4_path, student_id)
                v3 = validate_skill3_output(skill3_path) if skill3_path and skill3_path.is_file() else {}
                v4 = validate_skill4_output(skill4_path) if skill4_path and skill4_path.is_file() else {}
                if args.verbose:
                    print(f"[validate] skill3: {v3}", file=sys.stderr)
                    print(f"[validate] skill4: {v4}", file=sys.stderr)
            except ValueError as exc:
                print(f"Alignment / validation error: {exc}", file=sys.stderr)
                exit_code = 2

        if result is not None and exit_code == 0:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if args.skip_skill5:
                body = result["skill4_result"]
                args.output.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"Final output written to: {args.output.resolve()} (Skill 4 only)", file=sys.stderr)
            else:
                final: dict[str, Any] = result["skill5_result"]  # type: ignore[assignment]
                args.output.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
                v5 = validate_skill5_output(args.output)
                print(f"Final output written to: {args.output.resolve()}", file=sys.stderr)
                print(f"Mentors ranked: {v5.get('ranked_mentors', 'n/a')}", file=sys.stderr)
                print(f"Projects ranked: {v5.get('ranked_projects', 'n/a')}", file=sys.stderr)
                print(f"Teammates ranked: {v5.get('ranked_teammates', 'n/a')}", file=sys.stderr)
                if (v5.get("total_project_candidates") or 0) == 0 and (v5.get("ranked_projects") or 0) == 0:
                    print(
                        "WARNING: No project candidates were ranked. Check Skill 4 project source, "
                        "graph path, and mentor–project coverage.",
                        file=sys.stderr,
                    )
            if args.artifacts_dir:
                print(f"Run artifacts saved to: {args.artifacts_dir.resolve()}", file=sys.stderr)

        if args.artifacts_dir and result is not None and exit_code == 0:
            tpaths = result.get("temporary_paths") or []
            names = ("skill3.json", "skill4.json", "skill5.json")
            for pth, name in zip(tpaths, names):
                _copy_if_requested(Path(str(pth)), args.artifacts_dir, name)
    finally:
        if cleanup:
            shutil.rmtree(work, ignore_errors=True)
        elif not args.work_dir and args.keep_work_dir:
            print(f"Work directory kept at: {work}", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
