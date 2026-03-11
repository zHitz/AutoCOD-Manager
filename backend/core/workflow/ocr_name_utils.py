"""
OCR Name Utilities

Sanitization and noise filtering for lord_name strings
that may contain OCR artifacts, alliance tags, or other noise.
"""

import re
import unicodedata


# Characters commonly introduced by OCR errors on game fonts
_OCR_GARBAGE_CHARS = set('"\'|\\`~^')

# Minimum length for a name token to be considered valid
_MIN_TOKEN_LEN = 2


def sanitize_lord_name(raw_name: str) -> str:
    """Clean OCR-noisy lord_name for reliable in-game search.

    Three-phase pipeline:
      1. Strip OCR artifacts (stray quotes, pipes, special chars)
      2. Extract probable name (last token heuristic — alliance tags precede name)
      3. Validate length and return

    Args:
        raw_name: Raw lord_name string, potentially noisy.

    Returns:
        Cleaned name string suitable for OCR substring search.
        Returns empty string if input is entirely garbage.

    Examples:
        >>> sanitize_lord_name('dragonball "Goten')
        'Goten'
        >>> sanitize_lord_name('"MyLord"')
        'MyLord'
        >>> sanitize_lord_name('Storm"Rider')
        'Rider'
        >>> sanitize_lord_name('GotenSS')
        'GotenSS'
        >>> sanitize_lord_name('')
        ''
    """
    if not raw_name or not isinstance(raw_name, str):
        return ""

    # Phase 1: Strip OCR artifact characters
    cleaned = _strip_ocr_artifacts(raw_name)

    if not cleaned:
        return ""

    # Phase 2: Extract probable name (last meaningful token)
    tokens = cleaned.split()

    if len(tokens) <= 1:
        # Single token — already the best guess
        return cleaned

    # Multi-token: alliance/guild tag is usually the FIRST token(s),
    # the actual character name is the LAST token.
    candidate = tokens[-1].strip()

    # Validate: if last token is too short, try combining last 2 tokens
    if len(candidate) < _MIN_TOKEN_LEN and len(tokens) >= 2:
        candidate = tokens[-2].strip()
        if len(candidate) < _MIN_TOKEN_LEN:
            # Both last tokens too short, return full cleaned string
            return cleaned

    return candidate


def _strip_ocr_artifacts(text: str) -> str:
    """Remove common OCR noise characters from text.

    Strips:
    - Known garbage characters (" ' | \\ ` ~ ^)
    - Non-printable / control characters
    - Leading/trailing whitespace
    """
    result = []
    for ch in text:
        if ch in _OCR_GARBAGE_CHARS:
            # Replace garbage with space (preserves word boundaries)
            result.append(" ")
        elif unicodedata.category(ch).startswith("C"):
            # Control characters → skip
            continue
        else:
            result.append(ch)

    # Collapse multiple spaces and strip
    cleaned = re.sub(r"\s+", " ", "".join(result)).strip()
    return cleaned
