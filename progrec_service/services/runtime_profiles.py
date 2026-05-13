from __future__ import annotations

from pydantic import BaseModel, SecretStr


class RuntimeProfileCreate(BaseModel):
    label: str = "Session runtime"
    base_url: str
    model: str
    api_key: SecretStr | None = None


class RuntimeProfileRead(BaseModel):
    id: str
    label: str
    base_url: str
    model: str
    api_key_last4: str
