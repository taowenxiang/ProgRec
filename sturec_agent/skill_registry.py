"""Stable skill identifiers and metadata for documentation and tooling."""

from __future__ import annotations

from typing import Any


SKILL_REGISTRY: dict[str, dict[str, Any]] = {
    "/student-profiling": {
        "name": "Student Profiling Skill",
        "directory": "skill1_handoff",
        "entrypoint": "skill1_handoff/SKILL1_README.md (handoff + optional external package)",
        "function": "Normalize raw student narratives into structured profiles and optional embeddings.",
        "input_contract": "Raw student records or handoff: student_profiles_normalized.jsonl, embeddings.npy, student_ids.json",
        "output_contract": "JSONL profiles with student_id, grade, major, skills[], interests[], experience_summary, availability",
        "status": "artifact_handoff",
        "notes": "No in-repo batch CLI; Skill 2 consumes JSONL + NPY for graph builds.",
    },
    "/academic-graph": {
        "name": "Academic Graph Builder Skill",
        "directory": "skill2_handoff",
        "entrypoint": "skill2_handoff/regenerate_kit/scripts/build_graph.py",
        "function": "Fuse seeds and optional Skill 1 students into heterogeneous academic_graph.json plus standardized bundles.",
        "input_contract": "CSV seeds under regenerate_kit/data/seeds/; optional Skill 1 JSONL + embeddings + student_ids JSON",
        "output_contract": "academic_graph.json, mentor_profiles_standard.json, student_profiles_standard.json, optional aligned NPY/JSON",
        "status": "batch_cli",
        "notes": "Run generate_mentor_pool.py before build_graph if seeds are missing.",
    },
    "/mentor-discovery": {
        "name": "Mentor Discovery Skill",
        "directory": "skill3_mentor_discovery",
        "entrypoint": "skill3_mentor_discovery/run_skill3.py",
        "function": "Topic recall plus trust-aware graph reranking for mentor candidates.",
        "input_contract": "Standardized student dict; disk: outputs/ mentor + student bundles; graph from outputs or regenerate processed",
        "output_contract": "JSON object: student_id, graph_status, mentor_candidates[], optional graph_notice",
        "status": "runtime_cli_and_api",
        "notes": "CLI writes JSON to stdout; resource paths are fixed in loaders.py (no --skill2-students flag).",
    },
    "/project-teammate-discovery": {
        "name": "Project & Teammate Discovery Skill",
        "directory": "skill4_handoff",
        "entrypoint": "skill4_handoff/main.py",
        "function": "Expands mentor candidates into projects, skill gaps, and teammate recommendations with reason_paths.",
        "input_contract": "Skill 1 JSONL; Skill 2 graph + student + mentor paths (or auto-resolve); optional Skill 3 JSON; mock_projects fallback",
        "output_contract": "JSON: target_student_id, data_sources, mentor_project_teammate_recommendations[] with project_recommendations and teammate_recommendations",
        "status": "runtime_cli_and_api",
        "notes": "Agent dataset mode passes explicit paths from sturec_agent.config.ResourceConfig.",
    },
    "/social-ranking": {
        "name": "Social Ranking / Joint Ranker Skill",
        "directory": "skill5_student-recommendation-ranker",
        "entrypoint": "skill5_student-recommendation-ranker/scripts/joint_ranker.py",
        "function": "Joint multi-objective re-ranking of mentors, projects, and teammates with MMR and explanations.",
        "input_contract": "Paths to Skill 3 JSON, Skill 4 JSON; optional Skill 1 JSONL; --student-id, --top-k",
        "output_contract": "final_recommendation JSON: recommendations.{mentors,projects,teammates}, summary counts",
        "status": "runtime_cli",
        "notes": "sturec_agent invokes this script via subprocess; duplicate tree under skill5/ is non-canonical.",
    },
}


def get_skill(identifier: str) -> dict[str, Any]:
    """Return metadata dict for a stable skill identifier, or raise KeyError."""
    if identifier not in SKILL_REGISTRY:
        raise KeyError(f"Unknown skill identifier {identifier!r}. Known: {list(SKILL_REGISTRY.keys())}")
    return dict(SKILL_REGISTRY[identifier])


def list_skills() -> list[str]:
    """Return stable skill identifier strings in pipeline order."""
    return [
        "/student-profiling",
        "/academic-graph",
        "/mentor-discovery",
        "/project-teammate-discovery",
        "/social-ranking",
    ]
