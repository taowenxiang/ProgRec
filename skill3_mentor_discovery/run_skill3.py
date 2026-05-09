from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from skill3_mentor_discovery.graph_features import prepare_graph_for_ranking
from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.retrieval import rank_mentors_for_student


def _resolve_student(resources, student_id: str) -> dict[str, object]:
    for student in resources.students:
        if student.get("student_id") == student_id:
            return student
    raise ValueError(f"Unknown student_id: {student_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Skill 3 mentor discovery.")
    parser.add_argument("--student-id", required=True, help="Student id from standardized student profiles.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of mentor candidates to return.")
    parser.add_argument("--json-indent", type=int, default=2, help="Indentation for JSON output.")
    args = parser.parse_args()

    repo_root = _REPO_ROOT
    graph_status = "loaded"
    graph_notice = None
    try:
        resources = load_standardized_resources(repo_root, rebuild_graph_if_missing=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        resources = load_standardized_resources(repo_root, rebuild_graph_if_missing=False)
        graph_status = "unavailable_fallback_to_topic_only"
        graph_notice = "Graph rebuild was unavailable, so Skill 3 used topic-only mentor ranking."
    else:
        prepared_graph, graph_status, graph_notice = prepare_graph_for_ranking(resources.graph)
        resources.graph = prepared_graph

    student = _resolve_student(resources, args.student_id)
    mentor_candidates = rank_mentors_for_student(
        student,
        resources.mentors,
        graph=resources.graph,
        top_k=args.top_k,
    )
    payload = {
        "student_id": args.student_id,
        "graph_status": graph_status,
        "mentor_candidates": [candidate.to_dict() for candidate in mentor_candidates],
    }
    if graph_notice is not None:
        payload["graph_notice"] = graph_notice
    print(json.dumps(payload, indent=args.json_indent))


if __name__ == "__main__":
    main()
