from __future__ import annotations

import uuid

import httpx
from pydantic import BaseModel, SecretStr

from progrec_service.config import settings
from progrec_service.db.models import RuntimeProfile
from progrec_service.db.repositories.runtime_profiles import RuntimeProfileRepository
from progrec_service.db.session import SessionLocal
from progrec_service.services.encryption import decrypt_secret, encrypt_secret


class RuntimeProfileCreate(BaseModel):
    label: str = "Saved runtime"
    base_url: str
    model: str
    api_key: SecretStr


class RuntimeProfileRead(BaseModel):
    id: str
    label: str
    base_url: str
    model: str
    api_key_last4: str


def fetch_available_models(*, base_url: str, api_key: str) -> list[str]:
    response = httpx.get(
        f"{base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10.0,
    )
    response.raise_for_status()
    payload = response.json()
    return [str(item["id"]) for item in payload.get("data", []) if "id" in item]


def probe_runtime_profile(payload: RuntimeProfileCreate) -> dict[str, object]:
    models = fetch_available_models(
        base_url=payload.base_url,
        api_key=payload.api_key.get_secret_value(),
    )
    return {
        "ok": payload.model in models,
        "provider": "openai-compatible",
        "model": payload.model,
        "available_model_count": len(models),
    }


def create_runtime_profile(payload: RuntimeProfileCreate) -> RuntimeProfileRead:
    profile = RuntimeProfile(
        id=f"rp_{uuid.uuid4().hex[:12]}",
        label=payload.label,
        base_url=payload.base_url,
        model=payload.model,
        api_key_ciphertext=encrypt_secret(payload.api_key.get_secret_value(), settings.encryption_key),
        api_key_last4=payload.api_key.get_secret_value()[-4:],
    )
    with SessionLocal() as session:
        repo = RuntimeProfileRepository(session)
        repo.add(profile)
        session.commit()
    return RuntimeProfileRead(
        id=profile.id,
        label=profile.label,
        base_url=profile.base_url,
        model=profile.model,
        api_key_last4=profile.api_key_last4,
    )


def get_runtime_profile(profile_id: str) -> RuntimeProfileRead | None:
    with SessionLocal() as session:
        repo = RuntimeProfileRepository(session)
        profile = repo.get(profile_id)
    if profile is None:
        return None
    return RuntimeProfileRead(
        id=profile.id,
        label=profile.label,
        base_url=profile.base_url,
        model=profile.model,
        api_key_last4=profile.api_key_last4,
    )


def resolve_persisted_api_key(profile_id: str) -> str:
    with SessionLocal() as session:
        repo = RuntimeProfileRepository(session)
        profile = repo.get(profile_id)
    if profile is None:
        raise ValueError(f"runtime profile {profile_id} not found")
    return decrypt_secret(profile.api_key_ciphertext, settings.encryption_key)
