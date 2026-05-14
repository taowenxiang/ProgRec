from __future__ import annotations

from dataclasses import dataclass

from progrec_service.config import settings
from progrec_service.db.repositories.runtime_profiles import RuntimeProfileRepository
from progrec_service.db.session import SessionLocal
from progrec_service.services.encryption import decrypt_secret


@dataclass(frozen=True)
class RuntimeContext:
    base_url: str
    model: str
    api_key: str
    source: str


def resolve_runtime_context(
    *,
    ephemeral_runtime: dict[str, str] | None,
    runtime_profile_id: str | None,
) -> RuntimeContext:
    if ephemeral_runtime:
        return RuntimeContext(
            base_url=ephemeral_runtime["base_url"],
            model=ephemeral_runtime["model"],
            api_key=ephemeral_runtime["api_key"],
            source="ephemeral",
        )
    if runtime_profile_id is None:
        raise ValueError("runtime context requires either ephemeral runtime or runtime_profile_id")
    with SessionLocal() as session:
        repo = RuntimeProfileRepository(session)
        profile = repo.get(runtime_profile_id)
    if profile is None:
        raise ValueError(f"runtime profile {runtime_profile_id} not found")
    return RuntimeContext(
        base_url=profile.base_url,
        model=profile.model,
        api_key=decrypt_secret(profile.api_key_ciphertext, settings.encryption_key),
        source="persisted",
    )
