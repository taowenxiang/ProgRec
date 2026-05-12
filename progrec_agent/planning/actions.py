from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExecutionPlanV2:
    action: str
    arguments: dict[str, object] = field(default_factory=dict)
