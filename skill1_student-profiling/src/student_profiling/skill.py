"""Main StudentProfilingSkill orchestrator."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from student_profiling.extractors.inference import (
    extract_experience_summary,
    infer_availability,
)
from student_profiling.extractors.narrative import (
    extract_interests_from_story,
    extract_skills_from_story,
)
from student_profiling.extractors.structured import (
    extract_grade,
    extract_major,
    generate_student_id,
)
from student_profiling.schemas import RawStudentRecord, StudentProfile, StudentProfileExtended
from student_profiling.scoring.confidence import build_confidence_dict, compute_term_confidence
from student_profiling.scoring.quality import compute_profile_quality
from student_profiling.taxonomy.mappings import (
    get_interests_from_hobbies,
    get_skills_from_major,
    get_terms_from_uq,
)
from student_profiling.postprocess import clean_terms_with_sources


class StudentProfilingSkill:
    """Extract structured student profiles from raw narrative data.

    Usage:
        skill = StudentProfilingSkill()
        # Tier 1 - public interface only
        profile = skill.profile(raw_record_dict, index=0)
        # Tier 2 - extended with confidence, sources, quality score
        profile = skill.profile_extended(raw_record_dict, index=0)
        # Batch
        profiles = skill.batch_profile(records)
    """

    def profile(self, record: dict, index: int = 0) -> dict:
        """Process a single raw record dict into a StudentProfile dict (Tier 1)."""
        raw = RawStudentRecord.model_validate(record)
        result, _ = self._extract(raw, index)
        return result.model_dump()

    def profile_extended(self, record: dict, index: int = 0) -> dict:
        """Process a single raw record dict into an extended profile dict (Tier 2).

        Includes confidence scores, source tracking, quality score, and metadata.
        """
        raw = RawStudentRecord.model_validate(record)
        base, extras = self._extract(raw, index)

        extended = StudentProfileExtended(
            **base.model_dump(),
            gpa=raw.GPA,
            confidence=extras["confidence"],
            sources=extras["sources"],
            metadata={
                "name": raw.Name,
                "age": raw.Age,
                "sex": raw.Sex,
                "country": raw.Country,
                "state": raw.State_Province,
                "unique_quality": raw.Unique_Quality,
                "hobbies": raw.Hobbies,
                "profile_quality_score": extras["quality_score"],
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
                "schema_version": "1.0.0",
            },
        )
        return extended.model_dump()

    def batch_profile(
        self,
        records: list[dict],
        start_index: int = 0,
        extended: bool = False,
    ) -> list[dict]:
        """Process a list of raw record dicts."""
        fn = self.profile_extended if extended else self.profile
        return [fn(rec, start_index + i) for i, rec in enumerate(records)]

    def _extract(self, raw: RawStudentRecord, index: int) -> tuple[StudentProfile, dict]:
        """Core extraction logic. Returns (StudentProfile, extras_dict)."""
        student_id = generate_student_id(raw.Name, index)
        grade = extract_grade(raw.Year)
        major = extract_major(raw.Major)

        # --- Skills aggregation with source tracking ---
        skills: list[str] = []
        skill_sources_per_term: list[list[str]] = []  # parallel list

        major_skills, major_srcs = get_skills_from_major(raw.Major)
        for s, src in zip(major_skills, major_srcs):
            skills.append(s)
            skill_sources_per_term.append([src])

        uq_skills, uq_skill_srcs, uq_interests, uq_interest_srcs = get_terms_from_uq(raw.Unique_Quality)
        for s, src in zip(uq_skills, uq_skill_srcs):
            if s not in skills:
                skills.append(s)
                skill_sources_per_term.append([src])
            else:
                # corroboration: add source to existing term
                idx = skills.index(s)
                skill_sources_per_term[idx].append(src)

        story_skills, story_skill_srcs = extract_skills_from_story(raw.Story)
        for s, src in zip(story_skills, story_skill_srcs):
            if s not in skills:
                skills.append(s)
                skill_sources_per_term.append([src])
            else:
                idx = skills.index(s)
                skill_sources_per_term[idx].append(src)

        # --- Interests aggregation with source tracking ---
        interests: list[str] = []
        interest_sources_per_term: list[list[str]] = []

        hobby_interests, hobby_srcs = get_interests_from_hobbies(raw.Hobbies)
        for i, src in zip(hobby_interests, hobby_srcs):
            interests.append(i)
            interest_sources_per_term.append([src])

        for i, src in zip(uq_interests, uq_interest_srcs):
            if i not in interests:
                interests.append(i)
                interest_sources_per_term.append([src])
            else:
                idx = interests.index(i)
                interest_sources_per_term[idx].append(src)

        story_interests, story_interest_srcs = extract_interests_from_story(raw.Story)
        for i, src in zip(story_interests, story_interest_srcs):
            if i not in interests:
                interests.append(i)
                interest_sources_per_term.append([src])
            else:
                idx = interests.index(i)
                interest_sources_per_term[idx].append(src)

        # Deduplicate (already deduped above, but normalize)
        skills, skill_sources_per_term = _dedup_with_sources(skills, skill_sources_per_term)
        interests, interest_sources_per_term = _dedup_with_sources(interests, interest_sources_per_term)

        skills, skill_sources_per_term = clean_terms_with_sources(
            skills,
            skill_sources_per_term,
            kind="skill",
        )
        interests, interest_sources_per_term = clean_terms_with_sources(
            interests,
            interest_sources_per_term,
            kind="interest",
        )

        if not skills:
            skills = [major.lower()]
            skill_sources_per_term = [["major_taxonomy"]]
        if not interests:
            interests = [h.lower() for h in raw.Hobbies]
            interest_sources_per_term = [["hobby_direct"]] * len(interests)

        # --- Availability ---
        availability, avail_confidence = infer_availability(raw.Year, raw.Story)

        # --- Experience summary ---
        experience_summary = extract_experience_summary(
            raw.Story, raw.Major, raw.Unique_Quality
        )

        # --- Confidence dicts ---
        skill_confidence = build_confidence_dict(skills, skill_sources_per_term)
        interest_confidence = build_confidence_dict(interests, interest_sources_per_term)

        # --- Quality score ---
        quality_score = compute_profile_quality(
            skills=skills,
            interests=interests,
            experience_summary=experience_summary,
            skill_sources=skill_sources_per_term,
            interest_sources=interest_sources_per_term,
            skill_confidences=skill_confidence,
            interest_confidences=interest_confidence,
        )

        profile = StudentProfile(
            student_id=student_id,
            grade=grade,
            major=major,
            skills=skills,
            interests=interests,
            experience_summary=experience_summary,
            availability=availability,
        )

        extras = {
            "confidence": {
                "skills": skill_confidence,
                "interests": interest_confidence,
                "availability": avail_confidence,
            },
            "sources": {
                "skills": {s: srcs for s, srcs in zip(skills, skill_sources_per_term)},
                "interests": {i: srcs for i, srcs in zip(interests, interest_sources_per_term)},
            },
            "quality_score": quality_score,
        }

        return profile, extras


def _dedup(items: list[str]) -> list[str]:
    """Remove duplicates while preserving insertion order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _dedup_with_sources(
    items: list[str],
    sources: list[list[str]],
) -> tuple[list[str], list[list[str]]]:
    """Remove duplicate terms, merging sources for duplicates."""
    seen: dict[str, int] = {}  # term -> index in result
    result_items: list[str] = []
    result_sources: list[list[str]] = []
    for item, srcs in zip(items, sources):
        key = item.lower().strip()
        if not key:
            continue
        if key in seen:
            # Merge sources for existing term
            existing_idx = seen[key]
            for s in srcs:
                if s not in result_sources[existing_idx]:
                    result_sources[existing_idx].append(s)
        else:
            seen[key] = len(result_items)
            result_items.append(item)
            result_sources.append(list(srcs))
    return result_items, result_sources


def _iter_jsonl(path: Path) -> Iterator[dict]:
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> None:
    """CLI entry point: python -m student_profiling.skill --input FILE --output DIR"""
    import argparse

    parser = argparse.ArgumentParser(description="Student Profiling Skill")
    parser.add_argument("--input", required=True, help="Path to input JSONL file")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--limit", type=int, default=None, help="Max records to process")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "student_profiles_normalized.jsonl"

    skill = StudentProfilingSkill()
    stats = {"total": 0, "skills_total": 0, "interests_total": 0, "errors": 0}

    with open(output_path, "w") as out_f:
        for i, record in enumerate(_iter_jsonl(input_path)):
            if args.limit and i >= args.limit:
                break
            try:
                profile = skill.profile(record, index=i)
                out_f.write(json.dumps(profile) + "\n")
                stats["total"] += 1
                stats["skills_total"] += len(profile["skills"])
                stats["interests_total"] += len(profile["interests"])
            except Exception as e:
                stats["errors"] += 1
                print(f"[WARN] Record {i} failed: {e}", file=sys.stderr)

    n = stats["total"]
    if n > 0:
        print(f"Processed {n} records -> {output_path}")
        print(f"  Avg skills:    {stats['skills_total']/n:.2f}")
        print(f"  Avg interests: {stats['interests_total']/n:.2f}")
        print(f"  Errors:        {stats['errors']}")
    else:
        print("No records processed.")


if __name__ == "__main__":
    main()
