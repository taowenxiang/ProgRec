from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass
class Settings:
    recommended_model_base_url: str = os.getenv("RECOMMENDED_MODEL_BASE_URL", "https://api.openai.com/v1")
    recommended_model_name: str = os.getenv("RECOMMENDED_MODEL_NAME", "gpt-4.1-mini")


settings = Settings()
