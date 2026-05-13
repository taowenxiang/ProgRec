from __future__ import annotations

from dataclasses import dataclass, field

from progrec_service.db.models import RuntimeProfileRecord


@dataclass
class InMemoryDatabase:
    runtime_profiles: dict[str, RuntimeProfileRecord] = field(default_factory=dict)


db = InMemoryDatabase()
