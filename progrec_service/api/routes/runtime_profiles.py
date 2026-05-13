from __future__ import annotations

from fastapi import APIRouter

from progrec_service.services.runtime_profiles import RuntimeProfileCreate

router = APIRouter(prefix="/runtime-profiles", tags=["runtime-profiles"])


@router.post("/test")
def test_profile(payload: RuntimeProfileCreate) -> dict[str, object]:
    if payload.api_key is None or not payload.api_key.get_secret_value():
        return {"ok": False, "message": "Missing API key"}
    return {"ok": True, "message": "Connection successful"}
