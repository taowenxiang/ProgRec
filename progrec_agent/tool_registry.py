from __future__ import annotations

TOOLS: dict[str, dict[str, object]] = {
    "recommend_full_pipeline": {
        "name": "recommend_full_pipeline",
        "purpose": "Run Skill 3, Skill 4, and Skill 5 for one student or drafted profile.",
        "intent_tags": ["recommend"],
        "risk_level": "safe",
        "requires_confirmation": False,
        "side_effects": [],
        "executor_name": "run_recommendation",
    },
    "show_current_profile": {
        "name": "show_current_profile",
        "purpose": "Return the active student profile from session state.",
        "intent_tags": ["inspect", "explain"],
        "risk_level": "safe",
        "requires_confirmation": False,
        "side_effects": [],
        "executor_name": "show_current_profile",
    },
    "inspect_artifacts": {
        "name": "inspect_artifacts",
        "purpose": "Inspect the latest skill artifacts and surface high-level metadata.",
        "intent_tags": ["inspect", "debug"],
        "risk_level": "safe",
        "requires_confirmation": False,
        "side_effects": [],
        "executor_name": "inspect_artifacts",
    },
    "debug_graph_mode": {
        "name": "debug_graph_mode",
        "purpose": "Check graph-mode prerequisites and alignment for a student_id.",
        "intent_tags": ["debug"],
        "risk_level": "safe",
        "requires_confirmation": False,
        "side_effects": [],
        "executor_name": "debug_graph_mode",
    },
    "rebuild_skill2_graph": {
        "name": "rebuild_skill2_graph",
        "purpose": "Regenerate Skill 2 processed graph artifacts.",
        "intent_tags": ["rebuild"],
        "risk_level": "confirm",
        "requires_confirmation": True,
        "side_effects": ["refreshes processed graph artifacts"],
        "executor_name": "rebuild_skill2_graph",
    },
    "rebuild_skill1_profiles": {
        "name": "rebuild_skill1_profiles",
        "purpose": "Refresh Skill 1 normalized profiles when an external generator is configured.",
        "intent_tags": ["rebuild"],
        "risk_level": "confirm",
        "requires_confirmation": True,
        "side_effects": ["refreshes normalized profile artifacts"],
        "executor_name": "rebuild_skill1_profiles",
    },
}


def get_tool(name: str) -> dict[str, object]:
    return dict(TOOLS[name])


def list_tools() -> list[dict[str, object]]:
    return [dict(TOOLS[name]) for name in TOOLS]
