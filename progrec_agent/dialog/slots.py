from __future__ import annotations

TASK_REQUIRED_SLOTS = {
    "recommend_existing_student": ["student_id", "mode"],
    "recommend_temporary_profile": ["research_topic", "program_type", "experience_level"],
    "inspect_recommendation": [],
    "validate_resources": ["mode"],
}

LOW_RISK_DEFAULTS = {
    "target_types": ["mentor"],
    "top_k": 5,
}
