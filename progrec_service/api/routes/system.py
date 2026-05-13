from __future__ import annotations

from fastapi import APIRouter

from progrec_service.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "service": "progrec-api", "version": "1.0.0"}


@router.get("/models/recommended")
def recommended_model() -> dict[str, object]:
    return {
        "recommended": {
            "label": "Recommended",
            "base_url": settings.recommended_model_base_url,
            "model": settings.recommended_model_name,
        },
        "supported_notes": [
            "OpenAI-compatible endpoints supported",
            "User provides their own API key",
        ],
    }
