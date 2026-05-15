from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from progrec_service.services.runtime_profiles import (
    RuntimeProfileCreate,
    create_runtime_profile,
    get_runtime_profile,
    probe_runtime_profile,
)

router = APIRouter(prefix="/runtime-profiles", tags=["runtime-profiles"])


@router.post("/test")
def test_profile(payload: RuntimeProfileCreate) -> dict[str, object]:
    try:
        return probe_runtime_profile(payload)
    except httpx.HTTPStatusError as exc:
        upstream_status = exc.response.status_code
        raise HTTPException(
            status_code=400,
            detail=f"Runtime probe failed: provider returned HTTP {upstream_status}. Check the API key, base URL, and model.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Runtime probe failed: could not reach the configured provider.",
        ) from exc


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
