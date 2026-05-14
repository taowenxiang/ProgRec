"""Narrative extraction - regex-based skills/interests from Story text."""

from __future__ import annotations

import re

# Patterns that signal explicit skills in narrative text
# All capture groups are bounded to stop at punctuation/conjunctions/prepositions
_STOP_BOUNDARY = r"(?=[,\.;!?\n]|\s+(?:and|or|but|which|that|who|when|where|as|since|because|although|though|while|after|before|until|so|yet|for|nor|led|has|had|was|is|are|have|helped|made|gave|brought|caught|took|got|put|set|let|kept|left|came|went|saw|knew|thought|felt|found|told|asked|seemed|became|showed|turned|looked|used|tried|started|ended|moved|lived|played|ran|walked|talked|read|stood|heard|met|grew|spent|cut|learned|working|part-time|at a|in a|on a)\b)"

_SKILL_PATTERNS = [
    # "skilled in X" / "expertise in X" — bounded
    r"(?:skilled? in|skilled? at|expertise in|expert in|talent for|talented in|knack for)\s+([a-z][a-z\-]{2,20}(?:\s+[a-z][a-z\-]{2,20}){0,2})" + _STOP_BOUNDARY,
    # "proficient in X" — bounded
    r"(?:proficient in|proficiency in|trained in|certified in)\s+([a-z][a-z\-]{2,20}(?:\s+[a-z][a-z\-]{2,20}){0,2})" + _STOP_BOUNDARY,
    # "won/received X award" — keep the award-anchored pattern (already bounded by award/prize)
    r"(?:won|awarded|received)\s+(?:a |an |the )?([a-z][a-z\-]{2,20}(?:\s+[a-z][a-z\-]{2,20}){0,2})\s+(?:award|prize|competition|championship)",
]

# Patterns that signal explicit interests in narrative text
# Each capture group is bounded to stop at punctuation/conjunctions
_INTEREST_PATTERNS = [
    # "passion for X" / "fascinated by X" — stop at comma/period/conjunction
    r"(?:passion for|passionate about|fascinated by|fascination with|love for)\s+([a-z][a-z\-]{2,20}(?:\s+[a-z][a-z\-]{2,20}){0,2})(?=[,\.;!?\n]|\s+(?:and|or|but|which|that|who|when|where|as|since|because|although|though|while|after|before|until|so|yet|for|nor|with|by|from|led|has|had|was|is|are|have|helped|made|gave|brought|caught|took|got|put|set|let|kept|left|came|went|saw|knew|thought|felt|found|told|asked|seemed|became|showed|turned|looked|used|tried|started|ended|moved|lived|played|ran|walked|talked|read|stood|heard|let|met|led|grew|spent|cut|set|learned)\b)",
    # "interest in X"
    r"(?:interest in|interested in|keen interest in|deep interest in)\s+([a-z][a-z\-]{2,20}(?:\s+[a-z][a-z\-]{2,20}){0,2})(?=[,\.;!?\n]|\s+(?:and|or|but|which|that|who|when|where|as|since|because|although|though|while|after|before|until|so|yet|for|nor|with|by|from|led|has|had|was|is|are|have|helped|made|gave|brought|caught|took|got|put|set|let|kept|left|came|went|saw|knew|thought|felt|found|told|asked|seemed|became|showed|turned|looked|used|tried|started|ended|moved|lived|played|ran|walked|talked|read|stood|heard|let|met|led|grew|spent|cut|set|learned)\b)",
    # "dedicated to X"
    r"(?:dedicated to|committed to|devoted to)\s+([a-z][a-z\-]{2,20}(?:\s+[a-z][a-z\-]{2,20}){0,2})(?=[,\.;!?\n]|\s+(?:and|or|but|which|that|who)\b)",
]

# Stop words to filter out extracted noise
_STOP_TERMS = {
    "the", "a", "an", "his", "her", "their", "its", "this", "that", "these",
    "those", "it", "he", "she", "they", "we", "you", "i", "me", "him", "us",
    "what", "which", "who", "how", "when", "where", "why", "all", "more",
    "most", "much", "many", "some", "any", "each", "every", "both", "few",
    "other", "another", "such", "same", "own", "just", "also", "even",
    "still", "already", "always", "never", "often", "usually", "sometimes",
    "very", "quite", "rather", "too", "so", "well", "back", "out", "up",
    "down", "over", "under", "again", "further", "then", "once", "here",
    "there", "new", "old", "good", "great", "best", "better", "big", "small",
    "long", "little", "own", "right", "high", "low", "next", "last", "young",
    "early", "hard", "free", "real", "true", "full", "sure", "clear", "open",
    "making", "doing", "being", "having", "getting", "going", "coming",
    "taking", "giving", "working", "looking", "using", "finding", "helping",
    "trying", "keeping", "putting", "showing", "turning", "moving", "living",
    "playing", "running", "thinking", "feeling", "becoming", "leaving",
    "following", "bringing", "beginning", "holding", "writing", "standing",
    "hearing", "letting", "meeting", "leading", "growing", "spending",
    "cutting", "setting", "learning", "walking", "talking", "reading",
    "starting", "ending", "changing", "making", "saying", "seeing",
    "something", "anything", "everything", "nothing", "someone", "anyone",
    "everyone", "no one", "nobody", "everybody", "anybody", "somebody",
    "college", "university", "school", "campus", "class", "course", "degree",
    "student", "professor", "teacher", "friend", "family", "parent", "year",
    "day", "time", "life", "world", "place", "way", "thing", "part", "point",
    "fact", "case", "side", "hand", "head", "face", "eye", "mind", "heart",
    "body", "room", "home", "house", "door", "floor", "wall", "window",
    "morning", "evening", "night", "week", "month", "hour", "moment",
    "future", "past", "present", "end", "start", "beginning", "middle",
    "top", "bottom", "front", "back", "left", "right", "inside", "outside",
    "himself", "herself", "themselves", "myself", "yourself", "itself",
    "others", "people", "person", "man", "woman", "boy", "girl", "child",
    "senior", "junior", "sophomore", "freshman", "graduate", "undergraduate",
}

# Max term length (words) to avoid extracting full sentences
_MAX_TERM_WORDS = 4

# Single-word terms that are too generic to be useful as interests/skills
_GENERIC_SINGLE_WORDS = {
    "nature", "wildlife", "science", "art", "music", "sports", "life",
    "work", "study", "research", "learning", "knowledge", "education",
    "technology", "business", "health", "culture", "society", "community",
    "environment", "history", "literature", "language", "mathematics",
    "engineering", "medicine", "law", "politics", "economics", "philosophy",
    "psychology", "sociology", "biology", "chemistry", "physics",
    "kites", "kite", "birds", "plants", "animals", "stars", "rocks",
    "food", "water", "fire", "earth", "air", "space", "time", "energy",
    "people", "world", "things", "ideas", "skills", "talents", "abilities",
    "several",
}

# Multi-word phrases that are too generic or clearly noise
_GENERIC_PHRASES = {
    "various styles", "various fields", "various areas", "various topics",
    "different styles", "different fields", "different areas",
    "many things", "many areas", "many fields",
    "new things", "new skills", "new ideas",
    "his own music", "her own music", "their own music",
    "his own", "her own", "their own",
    "nature with others",
}


def _clean_term(term: str) -> str | None:
    """Clean and validate an extracted term."""
    term = term.strip().rstrip(".,;:!?").strip()
    # Remove trailing prepositions/articles/conjunctions
    term = re.sub(r'\s+(a|an|the|and|or|of|in|on|at|to|for|with|by|from|her|his|their|its)$', '', term)
    term = term.strip()

    if not term or len(term) < 4:
        return None
    words = term.split()
    if len(words) > _MAX_TERM_WORDS:
        return None
    # Filter pure stop-word terms
    if all(w.lower() in _STOP_TERMS for w in words):
        return None
    # Filter terms that start with a stop word (usually noise)
    if words[0].lower() in _STOP_TERMS:
        return None
    # Filter single-word generic terms
    if len(words) == 1 and words[0].lower() in _GENERIC_SINGLE_WORDS:
        return None
    # Filter known generic multi-word phrases
    if term.lower() in _GENERIC_PHRASES:
        return None
    return term.lower()


def extract_skills_from_story(story: str) -> tuple[list[str], list[str]]:
    """Extract skill terms from narrative Story text.

    Returns (skills, sources) where sources are all 'story_explicit'.
    """
    text = story.lower()
    skills: list[str] = []
    sources: list[str] = []

    for pattern in _SKILL_PATTERNS:
        for match in re.finditer(pattern, text):
            term = _clean_term(match.group(1))
            if term and term not in skills:
                skills.append(term)
                sources.append("story_explicit")

    return skills, sources


def extract_interests_from_story(story: str) -> tuple[list[str], list[str]]:
    """Extract interest terms from narrative Story text.

    Returns (interests, sources) where sources are all 'story_explicit'.
    """
    text = story.lower()
    interests: list[str] = []
    sources: list[str] = []

    for pattern in _INTEREST_PATTERNS:
        for match in re.finditer(pattern, text):
            term = _clean_term(match.group(1))
            if term and term not in interests:
                interests.append(term)
                sources.append("story_explicit")

    return interests, sources
