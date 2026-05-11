from __future__ import annotations

from progrec_agent.render import render_mentor_profile


def synthesize_reply(*, session, user_text: str, decision, result) -> str:
    if decision is not None and decision.message_type == "meta_question":
        if decision.intent == "ask_last_action":
            if session.last_action_kind == "clarify_then_wait" and session.last_action_result_summary:
                return (
                    "In the last turn I did not run a recommendation skill. "
                    "I asked a clarification question: "
                    f"{session.last_action_result_summary}"
                )
            if session.last_tool_name:
                return f"In the last turn I used `{session.last_tool_name}`."
            if decision.meta_reply:
                return decision.meta_reply
            return "I have not run a repository tool in this session yet."

    if decision is not None and decision.message_type == "out_of_scope":
        return (
            "That question is outside ProgRec's recommendation scope. "
            "I can still help with mentor, project, teammate, or graph-debug questions."
        )

    if decision is not None and decision.message_type == "startup_help":
        return decision.meta_reply or "I can help with mentor, project, teammate, and graph-debug questions."

    if result is None:
        return decision.meta_reply if decision is not None and decision.meta_reply else "I need a bit more detail."

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

    if result.tool_name == "show_recommended_mentor_profile":
        return render_mentor_profile(
            dict(result.payload.get("mentor_recommendation") or {}),
            dict(result.payload.get("mentor_profile") or {}),
            rank=result.payload.get("rank"),
        )

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
