"""Integration tests for the full StudentProfilingSkill pipeline."""

import json
import pytest
from student_profiling import StudentProfilingSkill
from student_profiling.schemas import StudentProfile


SAMPLE_RECORDS = [
    {
        "Name": "Thomas Ibarra",
        "Age": 24,
        "Sex": "Male",
        "Major": "Biochemistry",
        "Year": "Senior",
        "GPA": 2.83,
        "Hobbies": ["table tennis", "photography"],
        "Country": "USA",
        "State/Province": "Massachusetts",
        "Unique Quality": "Wildlife conservationist",
        "Story": (
            "Thomas Ibarra was a senior at the University of Massachusetts, majoring in Biochemistry. "
            "He had a passion for wildlife conservation and spent hours documenting endangered species. "
            "He created a photography portfolio that was featured in the university magazine. "
            "He was offered a job at a wildlife conservation organization in Africa after graduation."
        ),
    },
    {
        "Name": "Nancy Brown",
        "Age": 23,
        "Sex": "Female",
        "Major": "Archaeology",
        "Year": "Sophomore",
        "GPA": 3.44,
        "Hobbies": ["dancing", "bouldering"],
        "Country": "USA",
        "State/Province": "Iowa",
        "Unique Quality": "Graphic design guru",
        "Story": (
            "Nancy Brown was a sophomore at Iowa State University, majoring in Archaeology. "
            "She was fascinated by the history and culture of her hometown. "
            "She designed posters and brochures for the university archaeology exhibition. "
            "Her professor recommended her for an internship at a local museum."
        ),
    },
    {
        "Name": "Mary Gonzales",
        "Age": 24,
        "Sex": "Female",
        "Major": "Sociology",
        "Year": "Freshman",
        "GPA": 2.42,
        "Hobbies": ["puzzle solving", "bird watching"],
        "Country": "Canada",
        "State/Province": "Ontario",
        "Unique Quality": "A natural leader",
        "Story": (
            "Mary Gonzales was a freshman at Ontario University, majoring in Sociology. "
            "She had always been fascinated by human behavior and social dynamics. "
            "She organized study groups and student events on campus. "
            "She was eager to learn and seeking research opportunities in social science."
        ),
    },
]


@pytest.fixture
def skill():
    return StudentProfilingSkill()


class TestSingleProfile:
    def test_returns_valid_schema(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0], index=0)
        profile = StudentProfile(**result)
        assert profile.student_id
        assert profile.grade == "Senior"
        assert profile.major == "Biochemistry"

    def test_required_fields_present(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0], index=0)
        for field in ["student_id", "grade", "major", "skills", "interests",
                      "experience_summary", "availability"]:
            assert field in result, f"Missing field: {field}"
            assert result[field], f"Empty field: {field}"

    def test_skills_minimum_count(self, skill):
        for i, rec in enumerate(SAMPLE_RECORDS):
            result = skill.profile(rec, index=i)
            assert len(result["skills"]) >= 3, (
                f"Profile {i} has only {len(result['skills'])} skills"
            )

    def test_interests_minimum_count(self, skill):
        for i, rec in enumerate(SAMPLE_RECORDS):
            result = skill.profile(rec, index=i)
            assert len(result["interests"]) >= 2, (
                f"Profile {i} has only {len(result['interests'])} interests"
            )

    def test_skills_are_lowercase(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0], index=0)
        for s in result["skills"]:
            assert s == s.lower(), f"Skill not lowercase: {s}"

    def test_interests_are_lowercase(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0], index=0)
        for i in result["interests"]:
            assert i == i.lower(), f"Interest not lowercase: {i}"

    def test_availability_valid_enum(self, skill):
        for i, rec in enumerate(SAMPLE_RECORDS):
            result = skill.profile(rec, index=i)
            assert result["availability"] in ("high", "moderate", "low")

    def test_grade_matches_year(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0], index=0)
        assert result["grade"] == "Senior"

    def test_major_preserved(self, skill):
        result = skill.profile(SAMPLE_RECORDS[1], index=1)
        assert result["major"] == "Archaeology"

    def test_experience_summary_nonempty(self, skill):
        for i, rec in enumerate(SAMPLE_RECORDS):
            result = skill.profile(rec, index=i)
            assert len(result["experience_summary"]) > 10

    def test_experience_summary_max_length(self, skill):
        for i, rec in enumerate(SAMPLE_RECORDS):
            result = skill.profile(rec, index=i)
            assert len(result["experience_summary"]) <= 350


class TestAvailabilityInference:
    def test_senior_with_job_offer_is_low(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0], index=0)
        assert result["availability"] == "low"

    def test_freshman_seeking_research_is_high(self, skill):
        result = skill.profile(SAMPLE_RECORDS[2], index=2)
        assert result["availability"] == "high"


class TestTaxonomyMapping:
    def test_major_skills_included(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0], index=0)
        # Biochemistry should include at least one taxonomy skill
        biochem_skills = {"laboratory techniques", "molecular analysis",
                          "data analysis", "scientific writing"}
        assert any(s in biochem_skills for s in result["skills"])

    def test_hobbies_in_interests(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0], index=0)
        # photography hobby should produce photography interest
        assert "photography" in result["interests"]

    def test_uq_skill_type_adds_to_skills(self, skill):
        result = skill.profile(SAMPLE_RECORDS[1], index=1)
        # "Graphic design guru" is skill type -> should add graphic design
        assert "graphic design" in result["skills"]

    def test_uq_interest_type_adds_to_interests(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0], index=0)
        # "Wildlife conservationist" is interest type -> wildlife conservation
        assert "wildlife conservation" in result["interests"]

    def test_uq_personality_type_no_terms(self, skill):
        result = skill.profile(SAMPLE_RECORDS[2], index=2)
        # "A natural leader" is personality type -> no extra terms from UQ
        # skills should still come from major taxonomy
        assert len(result["skills"]) >= 3


class TestTermCleanup:
    def test_generic_skill_terms_are_removed_from_story_extraction(self):
        from student_profiling.extractors.narrative import extract_skills_from_story

        story = (
            "She was skilled in research and proficient in data analysis, "
            "and she was trained in laboratory techniques."
        )
        skills, _ = extract_skills_from_story(story)
        assert "research" not in skills
        assert "data analysis" in skills
        assert "laboratory techniques" in skills

    def test_uq_cleanup_removes_generic_terms_but_keeps_specific_ones(self, skill):
        result = skill.profile(
            {
                "Name": "Ava Stone",
                "Age": 21,
                "Sex": "Female",
                "Major": "Computer Science",
                "Year": "Junior",
                "GPA": 3.7,
                "Hobbies": ["photography", "table tennis"],
                "Country": "USA",
                "State/Province": "Ohio",
                "Unique Quality": "Tech wizard",
                "Story": "She was trained in laboratory techniques and created a design portfolio.",
            },
            index=99,
        )
        assert "laboratory techniques" in result["skills"]
        assert "software development" in result["skills"]
        assert "technology" not in result["skills"]

    def test_interest_cleanup_removes_generic_uq_interest_terms(self, skill):
        result = skill.profile(
            {
                "Name": "Lena Hart",
                "Age": 20,
                "Sex": "Female",
                "Major": "Physics",
                "Year": "Sophomore",
                "GPA": 3.6,
                "Hobbies": ["bird watching", "photography"],
                "Country": "USA",
                "State/Province": "Oregon",
                "Unique Quality": "Science enthusiast",
                "Story": "She was fascinated by astrophysics and spent weekends documenting birds.",
            },
            index=100,
        )
        assert "scientific inquiry" in result["interests"]
        assert "science" not in result["interests"]

    def test_narrative_cleanup_removes_award_quantifier_noise(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0] | {
            "Name": "Jessica Blankenship",
            "Major": "Music",
            "Year": "Freshman",
            "Unique Quality": "Creative writer",
            "Story": (
                "She had a passion for skateboarding, woodworking, and creative writing. "
                "Her writing won several awards and was published in a renowned literary magazine."
            ),
        }, index=101)
        assert "several" not in result["skills"]

    def test_narrative_cleanup_stops_interest_phrase_before_with_others(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0] | {
            "Name": "Jamie Taylor",
            "Major": "Computer Science",
            "Year": "Junior",
            "Unique Quality": "Nature guide",
            "Story": (
                "She had a talent for calligraphy and a love for nature with others. "
                "She also had a passion for poetry."
            ),
        }, index=102)
        assert "nature with others" not in result["interests"]


class TestBatchProfile:
    def test_batch_returns_correct_count(self, skill):
        results = skill.batch_profile(SAMPLE_RECORDS)
        assert len(results) == len(SAMPLE_RECORDS)

    def test_batch_indices_are_sequential(self, skill):
        results = skill.batch_profile(SAMPLE_RECORDS, start_index=100)
        assert results[0]["student_id"].endswith("00100")
        assert results[1]["student_id"].endswith("00101")

    def test_batch_no_duplicates(self, skill):
        results = skill.batch_profile(SAMPLE_RECORDS)
        ids = [r["student_id"] for r in results]
        assert len(ids) == len(set(ids))


class TestStudentIdGeneration:
    def test_id_is_url_safe(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0], index=0)
        sid = result["student_id"]
        import re
        assert re.match(r'^[a-z0-9\-]+$', sid), f"ID not URL-safe: {sid}"

    def test_id_contains_index(self, skill):
        result = skill.profile(SAMPLE_RECORDS[0], index=42)
        assert "00042" in result["student_id"]
