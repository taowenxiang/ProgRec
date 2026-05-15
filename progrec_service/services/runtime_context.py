from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


def _allow_env_file_fallback(app_env: str) -> bool:
    return app_env.strip().lower() in {"development", "dev", "test", "testing", "local"}


def _runtime_context_from_env_file(env_path: Path) -> RuntimeContext | None:
    if not env_path.exists():
        return None
    lines = [line.strip() for line in env_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) < 3:
        raise ValueError(f"runtime env file {env_path} must contain api key, model, and base url on separate lines")
    api_key, model, base_url = lines[:3]
    return RuntimeContext(
        base_url=base_url,
        model=model,
        api_key=api_key,
        source="env_file",
    )


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
        if _allow_env_file_fallback(settings.app_env):
            env_context = _runtime_context_from_env_file(settings.runtime_env_file)
            if env_context is not None:
                return env_context
            raise ValueError(
                "runtime context requires either ephemeral runtime, runtime_profile_id, or a valid env.txt file"
            )
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
