from __future__ import annotations

TASK_REQUIRED_SLOTS = {
    "recommend_existing_student": ["student_id", "mode"],
    "recommend_temporary_profile": ["research_topic", "program_type", "experience_level"],
    "inspect_recommendation": [],
    "explain_recommendation": [],
    "validate_resources": ["mode"],
    "answer_meta_question": [],
}

LOW_RISK_DEFAULTS = {
    "target_types": ["mentor"],
    "top_k": 5,
}
