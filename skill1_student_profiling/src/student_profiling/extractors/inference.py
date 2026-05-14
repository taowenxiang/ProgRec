"""Inference logic - availability and experience_summary from structured signals."""

from __future__ import annotations

import re

# Signals that lower availability (graduating with plans, very busy)
_LOW_AVAILABILITY_SIGNALS = [
    r"job offer",
    r"accepted a (?:position|job|offer)",
    r"offered (?:a |an )?(?:position|job)",
    r"moving to\b",
    r"relocat",
    r"graduation (?:ceremony|day)",
    r"after graduation",
    r"post.graduation",
    r"final (?:semester|year|exams?)",
    r"last (?:semester|year)",
]

# Signals that suggest reduced availability
_MODERATE_DOWN_SIGNALS = [
    r"busy schedule",
    r"juggling",
    r"overwhelm",
    r"part.time job",
    r"working (?:part.time|at a)",
    r"balancing",
    r"struggling to",
]

# Signals that suggest active research/project engagement (raise availability)
_HIGH_AVAILABILITY_SIGNALS = [
    r"research (?:project|lab|assistant|opportunity)",
    r"looking for (?:research|internship|opportunity)",
    r"eager to (?:learn|explore|contribute|join)",
    r"seeking (?:research|internship|opportunity)",
    r"interested in (?:joining|participating|contributing)",
]

# Action verbs for experience sentence extraction
_ACTION_VERBS = [
    "worked", "created", "built", "designed", "developed", "organized",
    "led", "managed", "volunteered", "interned", "joined", "won", "published",
    "founded", "launched", "established", "coordinated", "directed",
    "produced", "performed", "competed", "achieved", "received", "awarded",
    "presented", "researched", "analyzed", "implemented", "contributed",
    "collaborated", "mentored", "taught", "trained", "demonstrated",
]

_ACTION_VERB_PATTERN = re.compile(
    r'\b(' + '|'.join(_ACTION_VERBS) + r')\b', re.IGNORECASE
)

# Sentences to skip (generic narrative filler)
_FILLER_PATTERNS = [
    r"^(he|she|they) (was|were|had|would|could|did)",
    r"^(thomas|timothy|nancy|donna|mary|john|jane)",  # common name starts
    r"^(born|raised|growing up)",
    r"^(as|when|while|although|despite|however|but|and|so)",
    r"^(it was|it is|there was|there were)",
    r"^(the|a|an) \w+ (was|were|had|is|are)",
]
_FILLER_RE = re.compile('|'.join(_FILLER_PATTERNS), re.IGNORECASE)


def infer_availability(year: str, story: str) -> tuple[str, float]:
    """Infer availability from Year and Story signals.

    Returns (availability, confidence).
    """
    text = story.lower()

    # Base availability by year
    base = {
        "Freshman": "high",
        "Sophomore": "high",
        "Junior": "moderate",
        "Senior": "moderate",
    }.get(year, "moderate")

    level = {"high": 2, "moderate": 1, "low": 0}[base]

    # Check low signals (graduating with plans)
    for pattern in _LOW_AVAILABILITY_SIGNALS:
        if re.search(pattern, text):
            level = min(level, 0)  # force low
            break

    # Check moderate-down signals
    for pattern in _MODERATE_DOWN_SIGNALS:
        if re.search(pattern, text):
            level = max(level - 1, 0)
            break

    # Check high signals (actively seeking)
    for pattern in _HIGH_AVAILABILITY_SIGNALS:
        if re.search(pattern, text):
            level = min(level + 1, 2)
            break

    result = {2: "high", 1: "moderate", 0: "low"}[level]
    # Confidence is lower for inferred values
    confidence = 0.85 if result == base else 0.65
    return result, confidence


def extract_experience_summary(
    story: str,
    major: str,
    unique_quality: str,
    max_chars: int = 300,
) -> str:
    """Extract a 1-3 sentence experience summary from Story.

    Falls back to a generated sentence from UQ + major if no action sentences found.
    """
    sentences = _split_sentences(story)
    action_sentences = []

    for sent in sentences:
        sent_stripped = sent.strip()
        if not sent_stripped:
            continue
        # Must contain an action verb
        if not _ACTION_VERB_PATTERN.search(sent_stripped):
            continue
        # Skip filler sentences
        if _FILLER_RE.match(sent_stripped):
            continue
        # Skip very short or very long sentences
        word_count = len(sent_stripped.split())
        if word_count < 6 or word_count > 50:
            continue
        action_sentences.append(sent_stripped)

    if not action_sentences:
        # Fallback: generate from UQ + major
        return f"Student with background in {major.lower()}. {unique_quality}."

    # Pick top 1-3 sentences, prioritize shorter/more informative ones
    selected = action_sentences[:3]
    summary = " ".join(selected)

    # Truncate to max_chars at sentence boundary
    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(".", 1)[0] + "."

    return summary


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    # Split on period/exclamation/question followed by space+capital or end
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return parts
