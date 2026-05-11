"""Pydantic schemas for input/output data models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RawStudentRecord(BaseModel):
    """Raw input record from student_profiles.jsonl."""

    Name: str
    Age: int = Field(ge=18, le=30)
    Sex: Literal["Male", "Female"]
    Major: str
    Year: Literal["Freshman", "Sophomore", "Junior", "Senior"]
    GPA: float = Field(ge=0.0, le=5.0)
    Hobbies: list[str]
    Country: Literal["USA", "Canada"]
    State_Province: str = Field(alias="State/Province")
    Unique_Quality: str = Field(alias="Unique Quality")
    Story: str

    model_config = {"populate_by_name": True}


class StudentProfile(BaseModel):
    """Normalized student profile output for downstream skills."""

    student_id: str
    grade: Literal["Freshman", "Sophomore", "Junior", "Senior"]
    major: str
    skills: list[str] = Field(min_length=1)
    interests: list[str] = Field(min_length=1)
    experience_summary: str
    availability: Literal["high", "moderate", "low"]

    @field_validator("skills", "interests")
    @classmethod
    def lowercase_terms(cls, v: list[str]) -> list[str]:
        return [term.lower().strip() for term in v if term.strip()]


class StudentProfileExtended(StudentProfile):
    """Extended profile with Tier 2 fields (confidence, sources, embedding)."""

    gpa: float | None = None
    embedding: list[float] | None = None
    confidence: dict[str, dict[str, float] | float] | None = None
    sources: dict[str, dict[str, list[str]]] | None = None
    metadata: dict | None = None
