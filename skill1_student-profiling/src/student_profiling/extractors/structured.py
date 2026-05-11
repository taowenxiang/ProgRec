"""Structured field extraction - direct mapping from raw fields."""

from __future__ import annotations

import re
import unicodedata


def generate_student_id(name: str, index: int) -> str:
    """Generate a URL-safe student ID from name + index."""
    # Remove titles/suffixes
    clean = re.sub(r'\b(PhD|MD|Jr\.|Sr\.|DDS|III|II|IV)\b', '', name).strip()
    # Normalize unicode, lowercase, replace spaces/special chars with hyphens
    slug = unicodedata.normalize('NFKD', clean).encode('ascii', 'ignore').decode()
    slug = re.sub(r'[^a-z0-9]+', '-', slug.lower()).strip('-')
    return f"{slug}-{index:05d}"


def extract_grade(year: str) -> str:
    """Direct mapping: Year -> grade."""
    return year


def extract_major(major: str) -> str:
    """Direct mapping: Major -> major (lowercase)."""
    return major
