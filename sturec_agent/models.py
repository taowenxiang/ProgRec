from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Mode = Literal["dataset_mode", "custom_profile_mode"]
JsonDict = dict[str, Any]


@dataclass
class PipelineArtifacts:
    skill3_result: JsonDict | None = None
    skill4_result: JsonDict | None = None
    skill5_result: JsonDict | None = None
    temporary_paths: list[Path] = field(default_factory=list)
