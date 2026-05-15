from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    redis_url: str
    encryption_key: str
    progrec_repo_root: Path
    progrec_artifact_root: Path
    runtime_env_file: Path
    recommended_model_base_url: str
    recommended_model_name: str


def load_settings() -> Settings:
    progrec_repo_root = Path(os.getenv("PROGREC_REPO_ROOT", ".")).resolve()
    runtime_env_default = progrec_repo_root / "env.txt"
    if not runtime_env_default.exists():
        runtime_env_default = progrec_repo_root.parent / "env.txt"
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        encryption_key=os.getenv("ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef"),
        progrec_repo_root=progrec_repo_root,
        progrec_artifact_root=Path(os.getenv("PROGREC_ARTIFACT_ROOT", "./artifacts")).resolve(),
        runtime_env_file=Path(
            os.getenv("PROGREC_RUNTIME_ENV_FILE", str(runtime_env_default))
        ).resolve(),
        recommended_model_base_url=os.getenv("RECOMMENDED_MODEL_BASE_URL", "https://api.openai.com/v1"),
        recommended_model_name=os.getenv("RECOMMENDED_MODEL_NAME", "gpt-4.1-mini"),
    )


settings = load_settings()
