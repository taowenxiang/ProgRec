from __future__ import annotations


def render_summary(result: dict[str, object]) -> str:
    skill5 = result["skill5_result"]
    recs = skill5["recommendations"]
    lines = [
        f"Mode: {result['mode']}",
        f"Student: {result['student_profile']['student_id']}",
        "Top Mentors:",
    ]
    for mentor in recs["mentors"][:3]:
        lines.append(f"  {mentor['rank']}. {mentor['mentor_id']} ({mentor['final_score']:.3f})")
    lines.append("Top Projects:")
    for project in recs["projects"][:3]:
        lines.append(f"  {project['rank']}. {project['project_id']} ({project['final_score']:.3f})")
    lines.append("Top Teammates:")
    for teammate in recs["teammates"][:3]:
        lines.append(f"  {teammate['rank']}. {teammate['student_id']} ({teammate['final_score']:.3f})")
    return "\n".join(lines)


def render_mentor_detail(mentor: dict[str, object], skill4_bundle: dict[str, object]) -> str:
    projects = skill4_bundle.get("project_recommendations") or []
    teammates = skill4_bundle.get("teammate_recommendations") or []
    lines = [
        f"Mentor: {mentor.get('mentor_name') or mentor.get('mentor_id')}",
        f"ID: {mentor.get('mentor_id')}",
        f"Final score: {mentor.get('final_score')}",
        f"Explanation: {mentor.get('explanation', '')}",
        "Projects:",
    ]
    for project in projects[:3]:
        lines.append(f"  - {project.get('project_id')}: {project.get('title', '')}")
    lines.append("Teammates:")
    for teammate in teammates[:3]:
        lines.append(f"  - {teammate.get('student_id')}: {teammate.get('reason', '')}")
    return "\n".join(lines)


def render_mentor_profile(
    mentor_recommendation: dict[str, object],
    mentor_profile: dict[str, object],
    *,
    rank: int | None = None,
) -> str:
    name = (
        mentor_profile.get("name")
        or mentor_recommendation.get("mentor_name")
        or mentor_recommendation.get("mentor_id")
        or mentor_profile.get("mentor_id")
    )
    lines = [
        f"Mentor profile: {name}",
        f"ID: {mentor_profile.get('mentor_id') or mentor_recommendation.get('mentor_id')}",
    ]
    if rank is not None:
        lines.append(f"Recommended rank: {rank}")
    if mentor_recommendation.get("final_score") is not None:
        lines.append(f"Final score: {mentor_recommendation.get('final_score')}")
    if mentor_profile.get("department"):
        lines.append(f"Department: {mentor_profile.get('department')}")
    if mentor_profile.get("research_areas"):
        lines.append("Research areas: " + ", ".join(str(item) for item in mentor_profile.get("research_areas") or []))
    if mentor_profile.get("keywords"):
        lines.append("Keywords: " + ", ".join(str(item) for item in mentor_profile.get("keywords") or []))
    if mentor_profile.get("advising_style"):
        lines.append(f"Advising style: {mentor_profile.get('advising_style')}")
    if mentor_profile.get("weekly_time_expectation"):
        lines.append(f"Weekly time: {mentor_profile.get('weekly_time_expectation')}")
    if mentor_recommendation.get("explanation"):
        lines.append(f"Why recommended: {mentor_recommendation.get('explanation')}")
    if mentor_profile.get("profile_text"):
        lines.append(f"Profile: {mentor_profile.get('profile_text')}")
    return "\n".join(lines)


def render_agent_summary(result: dict[str, object], decision_trace: list[str], goal: str) -> str:
    summary = render_summary(result)
    lines = [f"Goal: {goal}", summary, "Decision Trace:"]
    if decision_trace:
        lines.extend(f"  - {line}" for line in decision_trace[:5])
    else:
        lines.append("  - No trace available.")
    return "\n".join(lines)
