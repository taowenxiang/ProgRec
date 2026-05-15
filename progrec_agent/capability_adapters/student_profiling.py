from __future__ import annotations

from typing import Any

from progrec_agent.dialog.profile_context import profile_context_from_text
from progrec_agent.runtime.profile_standardizer import standardize_temporary_profile


def build_temporary_profile(*, profile_context, executor_context):
    normalized = _coerce_profile_context(profile_context)
    return {"profile": standardize_temporary_profile(normalized)}


def update_profile_context(*, profile_context, executor_context):
    return {"profile_context": _coerce_profile_context(profile_context)}


def _coerce_profile_context(raw_profile_context: Any) -> dict[str, object]:
    if isinstance(raw_profile_context, dict):
        profile_context = dict(raw_profile_context)
        raw_profile_text = str(profile_context.get("raw_profile_text") or "").strip()
        if raw_profile_text and "profile_details" not in profile_context:
            profile_context["profile_details"] = raw_profile_text
        return profile_context
    text = str(raw_profile_context or "").strip()
    if not text:
        raise ValueError("profile_context must not be empty.")
    return profile_context_from_text(text)
