from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TypedDict

Mode = Literal["dataset_mode", "custom_profile_mode"]
JsonDict = dict[str, Any]


class ConversationTurn(TypedDict):
    role: str
    content: str


@dataclass
class PipelineArtifacts:
    skill3_result: JsonDict | None = None
    skill4_result: JsonDict | None = None
    skill5_result: JsonDict | None = None
    temporary_paths: list[Path] = field(default_factory=list)
