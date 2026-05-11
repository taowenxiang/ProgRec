"""Sentence-transformer embedding encoder for student profiles.

Model: all-MiniLM-L6-v2 (384-dim, ~22MB, fast on CPU/MPS)
Input text format: "{major}. Skills: {skills}. Interests: {interests}. {experience_summary}"
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


def build_profile_text(
    major: str,
    skills: list[str],
    interests: list[str],
    experience_summary: str,
) -> str:
    """Build the text string to embed for a student profile."""
    skills_str = ", ".join(skills[:8])
    interests_str = ", ".join(interests[:8])
    return (
        f"{major}. "
        f"Skills: {skills_str}. "
        f"Interests: {interests_str}. "
        f"{experience_summary}"
    )


class ProfileEncoder:
    """Lazy-loaded sentence-transformer encoder.

    Usage:
        encoder = ProfileEncoder()
        embedding = encoder.encode_one(text)
        embeddings = encoder.encode_batch(texts, batch_size=256)
    """

    MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self) -> None:
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise ImportError(
                    "sentence-transformers is required for embeddings. "
                    "Install with: pip install 'student-profiling-skill[embeddings]'"
                ) from e
            self._model = SentenceTransformer(self.MODEL_NAME)
        return self._model

    def encode_one(self, text: str) -> list[float]:
        """Encode a single text string. Returns a 384-dim list of floats."""
        model = self._load()
        vec = model.encode(text, convert_to_numpy=True)
        return vec.tolist()

    def encode_batch(
        self,
        texts: list[str],
        batch_size: int = 256,
        show_progress: bool = True,
    ) -> "np.ndarray":
        """Encode a list of texts. Returns numpy array of shape (n, 384)."""
        model = self._load()
        return model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )
