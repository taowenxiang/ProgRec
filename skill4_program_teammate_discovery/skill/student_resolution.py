"""Merge Skill 1 + Skill 2 student sources and resolve target student_id."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skill.skill1_adapter import (
    list_available_student_ids,
    load_skill1_profiles,
    normalize_skill1_profile,
)
from skill.skill2_adapter import load_skill2_students, normalize_skill2_student


@dataclass
class ResolvedTargetStudent:
    """Result of resolving ``--target-student-id`` against available profiles."""

    effective_student_id: str
    profile: dict[str, Any]
    requested_student_id: str
    resolution: str  # "resolved_ok" | "target_student_id_not_found_fallback_to_first_student" | "empty_bundle_no_students"
    warnings: list[str] = field(default_factory=list)
    sample_student_ids: list[str] = field(default_factory=list)


def build_merged_student_index_and_pool(
    skill2_students_path: Path | None,
    skill1_jsonl_path: Path | None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], str]:
    """Skill 2 profiles override Skill 1 on same ``student_id``; pool prefers Skill 2 list."""
    merged: dict[str, dict[str, Any]] = {}
    pool: list[dict[str, Any]] = []
    source_label = ""

    if skill1_jsonl_path and skill1_jsonl_path.is_file():
        for p in load_skill1_profiles(skill1_jsonl_path):
            n = normalize_skill1_profile(p)
            sid = n.get("student_id")
            if sid:
                merged[sid] = n
        source_label = source_label or str(skill1_jsonl_path)

    if skill2_students_path and skill2_students_path.is_file():
        bundle = load_skill2_students(skill2_students_path)
        rows = bundle.get("students") if isinstance(bundle, dict) else None
        if isinstance(rows, list) and rows:
            pool = [normalize_skill2_student(s) for s in rows]
            for n in pool:
                sid = n.get("student_id")
                if sid:
                    merged[sid] = n
            source_label = str(skill2_students_path)

    if not pool and skill1_jsonl_path and skill1_jsonl_path.is_file():
        pool = [
            normalize_skill1_profile(p)
            for p in load_skill1_profiles(skill1_jsonl_path)
            if normalize_skill1_profile(p).get("student_id")
        ]

    return merged, pool, source_label


def format_student_id_error(message: str, sample: list[str]) -> str:
    """Append up to 10 sample ids for CLI / ValueError messages."""
    sid_line = f" First available student_id values (up to 10): {sample}." if sample else ""
    return message + sid_line


def resolve_target_student(
    *,
    requested_id: str,
    merged_index: dict[str, dict[str, Any]],
    candidate_pool: list[dict[str, Any]],
    strict: bool = False,
    print_samples_to_stderr: bool = True,
    skill3_output_blocks_fallback: bool = False,
    allow_target_fallback_with_skill3: bool = False,
) -> ResolvedTargetStudent:
    """Resolve ``requested_id``; fallback to first pool student with explicit warning.

    When ``skill3_output_blocks_fallback`` is True (user passed ``--skill3-output`` and the file
    exists), a missing ``requested_id`` must not silently fall back to the first student unless
    ``allow_target_fallback_with_skill3`` is True; otherwise raise ``ValueError``.
    """
    sample = list_available_student_ids(candidate_pool, 10)
    if not candidate_pool:
        msg = "No student profiles loaded (check --skill2-students / Skill 1 JSONL paths)."
        return ResolvedTargetStudent(
            effective_student_id="",
            profile={},
            requested_student_id=str(requested_id or "").strip(),
            resolution="empty_bundle_no_students",
            warnings=[msg],
            sample_student_ids=[],
        )

    rid = str(requested_id or "").strip()
    if rid and rid in merged_index:
        return ResolvedTargetStudent(
            effective_student_id=rid,
            profile=dict(merged_index[rid]),
            requested_student_id=rid,
            resolution="resolved_ok",
            warnings=[],
            sample_student_ids=sample,
        )

    first = candidate_pool[0]
    fid = str(first.get("student_id") or "").strip()
    if not fid:
        return ResolvedTargetStudent(
            effective_student_id="",
            profile={},
            requested_student_id=rid,
            resolution="empty_bundle_no_students",
            warnings=["Student pool has rows without student_id."],
            sample_student_ids=sample,
        )

    if rid:
        detail = (
            f"Requested target_student_id={rid!r} not found in merged Skill 2 + Skill 1 student sources."
        )
        if skill3_output_blocks_fallback and not allow_target_fallback_with_skill3:
            msg = format_student_id_error(
                detail
                + " With --skill3-output, falling back to another student would desync mentor recommendations; "
                "fix --target-student-id or pass --allow-target-fallback-with-skill3 to override.",
                sample,
            )
            if print_samples_to_stderr:
                print(msg, file=sys.stderr)
            raise ValueError(msg)
        warn = "target_student_id_not_found_fallback_to_first_student"
        detail_fb = (
            f"{detail} Using first available student {fid!r} instead."
        )
        if print_samples_to_stderr:
            print(detail_fb, file=sys.stderr)
            print(f"Sample student_id values (first {len(sample)}): {sample}", file=sys.stderr)
        if strict:
            raise ValueError(format_student_id_error(detail_fb, sample))
        fb_warnings = [warn, detail_fb]
        if skill3_output_blocks_fallback and allow_target_fallback_with_skill3:
            fb_warnings.append(
                "allow_target_fallback_with_skill3: fallback permitted while Skill 3 output is in use."
            )
        return ResolvedTargetStudent(
            effective_student_id=fid,
            profile=dict(merged_index.get(fid, first)),
            requested_student_id=rid,
            resolution=warn,
            warnings=fb_warnings,
            sample_student_ids=sample,
        )

    if skill3_output_blocks_fallback and not allow_target_fallback_with_skill3:
        msg = format_student_id_error(
            "No --target-student-id provided. With --skill3-output, Skill 4 requires an explicit target "
            "so mentor recommendations stay aligned; pass --target-student-id or --allow-target-fallback-with-skill3.",
            sample,
        )
        if print_samples_to_stderr:
            print(msg, file=sys.stderr)
        raise ValueError(msg)

    return ResolvedTargetStudent(
        effective_student_id=fid,
        profile=dict(merged_index.get(fid, first)),
        requested_student_id="",
        resolution="resolved_ok",
        warnings=["No --target-student-id provided; using first student in bundle."],
        sample_student_ids=sample,
    )
