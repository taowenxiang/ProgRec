"""Student Profiling Skill - Extract structured profiles from raw student data."""

from student_profiling.schemas import RawStudentRecord, StudentProfile
from student_profiling.skill import StudentProfilingSkill

__all__ = ["StudentProfilingSkill", "RawStudentRecord", "StudentProfile"]
__version__ = "1.0.0"
