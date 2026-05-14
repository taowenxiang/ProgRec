"""Short natural-language reasons and path fragments for reports / demos."""

from __future__ import annotations

from typing import Any


def generate_project_reason(
    student_interests: list[str],
    matched_interests: list[str],
    matched_skills: list[str],
    missing_skills: list[str],
    mentor_linked: bool,
) -> str:
    parts: list[str] = []
    if mentor_linked:
        parts.append("The project is connected to the recommended mentor in the academic graph.")
    if matched_interests:
        parts.append(
            f"It aligns with interests such as {', '.join(matched_interests[:4])}."
        )
    elif student_interests:
        parts.append("Topic overlap with the student's interests is limited but the project may still be a useful entry point.")
    if matched_skills:
        parts.append(f"The student already brings {', '.join(matched_skills[:4])}.")
    if missing_skills:
        parts.append(f"They may need support in {', '.join(missing_skills[:5])}.")
    if not parts:
        return "Project fit is based on general profile compatibility with the mentor's portfolio."
    return " ".join(parts)


def generate_teammate_reason(
    shared_interests: list[str],
    complementary_skills: list[str],
    graph_edge_types: list[str],
) -> str:
    parts: list[str] = []
    if shared_interests:
        parts.append(
            f"The teammate shares interests such as {', '.join(shared_interests[:4])}."
        )
    if complementary_skills:
        parts.append(
            f"They can complement missing skills: {', '.join(complementary_skills[:5])}."
        )
    if graph_edge_types:
        parts.append(
            f"The Skill 2 graph also shows: {', '.join(sorted(set(graph_edge_types)))}."
        )
    if not parts:
        return "Teammate score is driven mainly by skill overlap and availability."
    return " ".join(parts)


def build_reason_paths(
    target_student_id: str,
    mentor_id: str,
    project_id: str,
    matched_interests: list[str],
    missing_skills: list[str],
    teammate_recs: list[dict[str, Any]] | None,
) -> list[list[str]]:
    """Emit ``complemented_by`` only when a teammate lists that skill in ``complementary_skills``."""
    _ = mentor_id  # reserved for richer paths later
    paths: list[list[str]] = []
    for it in matched_interests[:3]:
        paths.append(
            [
                "target_student",
                "has_interest",
                it,
                "matched_project",
                project_id,
            ]
        )
    paths.append(["mentor", "project_leads", project_id])
    teammates = teammate_recs or []
    for sk in missing_skills[:12]:
        sk_l = str(sk).strip().lower()
        teammate_id: str | None = None
        for tm in teammates:
            comp = {str(x).strip().lower() for x in (tm.get("complementary_skills") or [])}
            if sk_l in comp:
                teammate_id = str(tm.get("student_id") or "").strip() or None
                break
        if teammate_id:
            paths.append(["project", "requires_skill", sk_l, "complemented_by", teammate_id])
        else:
            paths.append(["project", "requires_skill", sk_l, "gap_for", "target_student"])
    return paths[:20]
