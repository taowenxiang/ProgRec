from __future__ import annotations


def synthesize_reply(*, session, user_text: str, decision, result) -> str:
    if not result.ok:
        return f"I tried to run `{result.tool_name}`, but it failed: {result.error}"

    if result.tool_name == "recommend_full_pipeline":
        skill5 = dict(result.payload.get("skill5_result") or {})
        recs = dict(skill5.get("recommendations") or {})
        return (
            "I ran the recommendation pipeline and generated recommendations. "
            f"Mentors: {len(list(recs.get('mentors') or []))}, "
            f"Projects: {len(list(recs.get('projects') or []))}, "
            f"Teammates: {len(list(recs.get('teammates') or []))}."
        )

    if result.tool_name == "show_current_profile":
        profile = result.payload.get("student_profile") or {}
        return f"Current profile: {profile}"

    if result.tool_name == "inspect_artifacts":
        return (
            "I inspected the current artifacts. "
            f"Mode: {result.payload.get('mode')}, files: {result.payload.get('temporary_paths')}"
        )

    if result.tool_name == "debug_graph_mode":
        return (
            "I checked graph-mode prerequisites. "
            f"Graph exists: {result.payload.get('graph_exists')}. "
            f"Students path: {result.payload.get('students_path')}"
        )

    return f"I handled your request with `{result.tool_name}`."
