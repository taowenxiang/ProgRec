#!/usr/bin/env python3
"""CLI: build heterogeneous graph JSON + print evaluation summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
_BUNDLE_ROOT = _SCRIPT.parents[1]
if str(_BUNDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(_BUNDLE_ROOT))

from skills.academic_graph_builder.runtime_paths import course_repo_root
from skills.academic_graph_builder import (
    build_graph_from_seeds,
    evaluate_payload,
    save_graph_json,
)
from skills.academic_graph_builder.mentor_profiles import save_mentor_standard_bundle
from skills.academic_graph_builder.skill1_embeddings import export_aligned_student_embeddings
from skills.academic_graph_builder.student_skill1 import save_student_standard_bundle

_COURSE_ROOT = course_repo_root(_BUNDLE_ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ProgRec academic graph from CSV seeds.")
    parser.add_argument(
        "--seeds",
        type=Path,
        default=_BUNDLE_ROOT / "data" / "seeds",
        help="Directory containing seed CSV files",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_BUNDLE_ROOT / "data" / "processed" / "academic_graph.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--eval-json",
        type=Path,
        default=None,
        help="Optional path to write evaluation metrics JSON",
    )
    parser.add_argument(
        "--mentor-out",
        type=Path,
        default=_BUNDLE_ROOT / "data" / "processed" / "mentor_profiles_standard.json",
        help="Standardized mentor profile bundle for downstream skills",
    )
    parser.add_argument(
        "--skill1-jsonl",
        type=Path,
        default=None,
        help="Skill 1 handoff: student_profiles_normalized.jsonl (overrides students.csv nodes). "
        f"Typical: {_COURSE_ROOT / 'skill1_handoff' / 'student_profiles_normalized.jsonl'}",
    )
    parser.add_argument(
        "--skill1-max-students",
        type=int,
        default=1800,
        help="Max students to load from Skill 1 JSONL (pairwise edges skipped above ~2800)",
    )
    parser.add_argument(
        "--skill1-no-major-filter",
        action="store_true",
        help="Load first N profiles without CS-related major filtering",
    )
    parser.add_argument(
        "--student-out",
        type=Path,
        default=_BUNDLE_ROOT / "data" / "processed" / "student_profiles_standard.json",
        help="Student bundle aligned with graph nodes (recommended when using --skill1-jsonl)",
    )
    parser.add_argument(
        "--skill1-embeddings",
        type=Path,
        default=_COURSE_ROOT / "skill1_handoff" / "embeddings.npy",
        help="Skill 1 embeddings.npy (full corpus, row-aligned with student_ids.json)",
    )
    parser.add_argument(
        "--skill1-student-ids-json",
        type=Path,
        default=_COURSE_ROOT / "skill1_handoff" / "student_ids.json",
        help="Skill 1 student_ids.json (same order as embeddings.npy rows)",
    )
    parser.add_argument(
        "--embedding-out",
        type=Path,
        default=_BUNDLE_ROOT / "data" / "processed" / "student_embeddings_aligned.npy",
        help="Subset embeddings aligned to exported student order",
    )
    parser.add_argument(
        "--embedding-ids-out",
        type=Path,
        default=_BUNDLE_ROOT / "data" / "processed" / "student_ids_aligned.json",
        help="student_id list matching rows of student_embeddings_aligned.npy",
    )
    parser.add_argument(
        "--skip-skill1-embedding-export",
        action="store_true",
        help="Do not slice/export embeddings even if files exist",
    )
    args = parser.parse_args()

    major_filter = None if args.skill1_no_major_filter else (
        "Computer",
        "Software",
        "Electrical",
        "Data Science",
        "Information",
        "Cyber",
        "Mathematics",
    )

    payload = build_graph_from_seeds(
        args.seeds,
        skill1_jsonl=args.skill1_jsonl,
        skill1_max_students=args.skill1_max_students,
        skill1_major_filter=major_filter,
    )
    save_graph_json(payload, args.out)
    save_mentor_standard_bundle(
        payload.nodes["mentor"],
        args.mentor_out,
        build_meta={
            "graph_out": str(args.out.resolve()),
            "seeds_dir": str(args.seeds.resolve()),
        },
    )
    student_meta: dict = {
        "graph_out": str(args.out.resolve()),
        "student_source": payload.build_meta.get("student_source"),
        "skill1_jsonl": payload.build_meta.get("skill1_jsonl"),
    }
    if args.skill1_jsonl is not None:
        emb_path = args.skill1_embeddings
        sid_path = args.skill1_student_ids_json
        if args.skip_skill1_embedding_export:
            student_meta["embedding_note"] = "Embedding export skipped (--skip-skill1-embedding-export)."
        elif emb_path.is_file() and sid_path.is_file():
            ordered = [s["student_id"] for s in payload.nodes["student"]]
            export_info = export_aligned_student_embeddings(
                embeddings_npy=emb_path,
                student_ids_json=sid_path,
                ordered_student_ids=ordered,
                npy_out=args.embedding_out,
                ids_json_out=args.embedding_ids_out,
            )
            student_meta["skill1_embeddings_export"] = export_info
            student_meta["embedding_note"] = (
                "Rows of student_embeddings_aligned.npy match students[] order in student_profiles_standard.json "
                "and student_ids_aligned.json (subset sliced from full Skill 1 embeddings)."
            )
        else:
            student_meta["embedding_alignment_warning"] = (
                "Could not export aligned embeddings. "
                f"Expected Skill 1 files under skill1_handoff/ (or pass --skill1-embeddings / --skill1-student-ids-json). "
                f"Missing: embeddings={not emb_path.is_file()}, student_ids_json={not sid_path.is_file()} "
                f"(looked at {emb_path} and {sid_path})."
            )
    save_student_standard_bundle(payload.nodes["student"], args.student_out, build_meta=student_meta)

    metrics = evaluate_payload(payload, args.seeds)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    if args.eval_json:
        args.eval_json.parent.mkdir(parents=True, exist_ok=True)
        with args.eval_json.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
