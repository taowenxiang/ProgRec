from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeProfileRecord:
    id: str
    label: str
    base_url: str
    model: str
    api_key_encrypted: str
    api_key_last4: str
