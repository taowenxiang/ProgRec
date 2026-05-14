from __future__ import annotations

from fastapi import APIRouter

from progrec_service.services.runtime_profiles import (
    RuntimeProfileCreate,
    create_runtime_profile,
    get_runtime_profile,
    probe_runtime_profile,
)

router = APIRouter(prefix="/runtime-profiles", tags=["runtime-profiles"])


@router.post("/test")
def test_profile(payload: RuntimeProfileCreate) -> dict[str, object]:
    return probe_runtime_profile(payload)


@router.post("", status_code=201)
def create_profile(payload: RuntimeProfileCreate) -> dict[str, object]:
    profile = create_runtime_profile(payload)
    return {
        "profile_id": profile.id,
        "label": profile.label,
        "base_url": profile.base_url,
        "model": profile.model,
        "api_key_last4": profile.api_key_last4,
    }


@router.get("/{profile_id}")
def get_profile(profile_id: str) -> dict[str, object]:
    profile = get_runtime_profile(profile_id)
    if profile is None:
        return {"profile_id": profile_id, "found": False}
    return {
        "profile_id": profile.id,
        "label": profile.label,
        "base_url": profile.base_url,
        "model": profile.model,
        "api_key_last4": profile.api_key_last4,
    }
