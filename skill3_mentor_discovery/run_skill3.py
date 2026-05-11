from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from skill3_mentor_discovery.graph_features import prepare_graph_for_ranking
from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.evaluate import (
    evaluate_ablation_summary,
    evaluate_perturbation_summary,
)
from skill3_mentor_discovery.retrieval import rank_mentors_for_student
from progrec_agent.llm_client import LLMClient, LLMConfig


def _resolve_student(resources, student_id: str) -> dict[str, object]:
    for student in resources.students:
        if student.get("student_id") == student_id:
            return student
    sample = [str(s.get("student_id")) for s in resources.students[:10] if s.get("student_id")]
    raise ValueError(
        f"Unknown student_id: {student_id}. First available student_id values (up to 10): {sample}"
    )


def _data_sources(resources) -> dict[str, object]:
    paths = resources.paths
    return {
        "student_profiles": str(paths.student_profiles_path.resolve()),
        "mentor_profiles": str(paths.mentor_profiles_path.resolve()),
        "academic_graph": str(resources.graph_source_path.resolve())
        if resources.graph_source_path
        else None,
        "resource_mode": paths.resource_mode,
    }


def _build_reason_llm_from_env() -> LLMClient | None:
    api_key = (os.getenv("PROGREC_AGENT_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return None
    model = (os.getenv("PROGREC_AGENT_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
    endpoint = (
        os.getenv("PROGREC_AGENT_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "https://api.openai.com/v1/responses"
    ).strip()
    return LLMClient(LLMConfig(model=model, api_key=api_key, endpoint=endpoint))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Skill 3 mentor discovery.")
    parser.add_argument("--student-id", help="Student id from standardized student profiles.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of mentor candidates to return.")
    parser.add_argument("--json-indent", type=int, default=2, help="Indentation for JSON output.")
    parser.add_argument(
        "--skill2-graph",
        type=Path,
        default=None,
        help="Optional academic_graph.json; must exist if passed (no fallback to outputs/).",
    )
    parser.add_argument(
        "--skill2-students",
        type=Path,
        default=None,
        help="Optional student_profiles_standard.json (must exist if passed).",
    )
    parser.add_argument(
        "--skill2-mentors",
        type=Path,
        default=None,
        help="Optional mentor_profiles_standard.json (must exist if passed).",
    )
    parser.add_argument(
        "--evaluation-mode",
        choices=("none", "ablation", "perturbation"),
        default="none",
        help="Optional evaluation output mode.",
    )
    args = parser.parse_args()

    repo_root = _REPO_ROOT
    if args.evaluation_mode == "ablation":
        print(json.dumps(evaluate_ablation_summary(repo_root, top_k=args.top_k), indent=args.json_indent))
        return
    if args.evaluation_mode == "perturbation":
        print(
            json.dumps(
                evaluate_perturbation_summary(repo_root, top_k=args.top_k),
                indent=args.json_indent,
            )
        )
        return
    if not args.student_id:
        parser.error("--student-id is required unless --evaluation-mode is ablation or perturbation.")

    graph_status = "loaded"
    graph_notice = None
    try:
        resources = load_standardized_resources(
            repo_root,
            rebuild_graph_if_missing=True,
            skill2_graph=args.skill2_graph,
            skill2_students=args.skill2_students,
            skill2_mentors=args.skill2_mentors,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        resources = load_standardized_resources(
            repo_root,
            rebuild_graph_if_missing=False,
            skill2_graph=args.skill2_graph,
            skill2_students=args.skill2_students,
            skill2_mentors=args.skill2_mentors,
        )
        graph_status = "unavailable_fallback_to_topic_only"
        graph_notice = "Graph rebuild was unavailable, so Skill 3 used topic-only mentor ranking."

    try:
        student = _resolve_student(resources, args.student_id)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    if graph_status == "loaded":
        prepared_graph, graph_status, graph_notice = prepare_graph_for_ranking(
            resources.graph,
            student_id=str(student.get("student_id", "")) or None,
        )
        resources.graph = prepared_graph
    reason_llm = _build_reason_llm_from_env()
    mentor_candidates = rank_mentors_for_student(
        student,
        resources.mentors,
        graph=resources.graph,
        top_k=args.top_k,
        llm_client=reason_llm,
    )
    payload = {
        "student_id": args.student_id,
        "graph_status": graph_status,
        "mentor_candidates": [candidate.to_dict() for candidate in mentor_candidates],
        "data_sources": _data_sources(resources),
    }
    if graph_notice is not None:
        payload["graph_notice"] = graph_notice
    print(json.dumps(payload, indent=args.json_indent))


if __name__ == "__main__":
    main()
