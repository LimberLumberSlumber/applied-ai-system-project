"""Input validation and confidence scoring. Nothing here raises to the caller."""
import re

from .models import BusyBlock

_TIME = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_time(text: str) -> int:
    """Parse HH:MM into minutes since midnight. Raises ValueError if invalid."""
    match = _TIME.match((text or "").strip())
    if not match:
        raise ValueError(f"'{text}' is not a valid time, use HH:MM")
    hours, mins = int(match.group(1)), int(match.group(2))
    if hours > 23 or mins > 59:
        raise ValueError(f"'{text}' is out of range")
    return hours * 60 + mins


def validate_busy(rows: list) -> tuple:
    """rows: list of (start, end, label) strings. Returns (blocks, errors, warnings)."""
    blocks, errors, warnings = [], [], []
    for start, end, label in rows:
        try:
            s, e = parse_time(start), parse_time(end)
        except ValueError as err:
            errors.append(f"Busy block '{label}': {err}")
            continue
        if e <= s:
            errors.append(f"Busy block '{label}': end {end} must be after start {start}")
            continue
        blocks.append(BusyBlock(s, e, label or "busy"))
    ordered = sorted(blocks, key=lambda b: b.start)
    for a, b in zip(ordered, ordered[1:]):
        if b.start < a.end:
            warnings.append(f"Busy blocks overlap: '{a.label}' and '{b.label}' (merged)")
    return blocks, errors, warnings


def validate_day(start: str, end: str) -> tuple:
    """Returns (day_start, day_end, errors)."""
    try:
        s, e = parse_time(start), parse_time(end)
    except ValueError as err:
        return 0, 0, [f"Day window: {err}"]
    if e <= s:
        return s, e, ["Day window: end must be after start"]
    return s, e, []


def confidence(match_score: float, source: str, complete: bool, used_fallback: bool = False) -> float:
    """Score 0..1. Fuzzy match quality, data source, data completeness."""
    score = 0.6 * match_score
    score += 0.25 if source == "tmdb" else 0.2
    score += 0.15 if complete else 0.0
    if used_fallback:
        score -= 0.1
    return round(max(0.0, min(1.0, score)), 2)
