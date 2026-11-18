"""Free-time finding. Adapts the conflict idea from PawPal+ Scheduler.detect_conflicts."""
from .models import BusyBlock


def merge_busy(busy: list) -> list:
    """Merge overlapping or touching busy blocks into sorted (start, end) pairs."""
    merged = []
    for block in sorted(busy, key=lambda b: b.start):
        if merged and block.start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], block.end))
        else:
            merged.append((block.start, block.end))
    return merged


def free_windows(busy: list, day_start: int, day_end: int) -> list:
    """Return sorted (start, end) gaps inside the day that are not busy."""
    windows, cursor = [], day_start
    for start, end in merge_busy(busy):
        start, end = max(start, day_start), min(end, day_end)
        if end <= start:
            continue
        if start > cursor:
            windows.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < day_end:
        windows.append((cursor, day_end))
    return windows


def place_session(windows: list, minutes: int, min_chunk: int = 20) -> tuple:
    """Fill windows in order. Returns (segments, minutes_left). Skips windows under min_chunk."""
    segments, left = [], minutes
    for start, end in windows:
        length = end - start
        if left <= 0:
            break
        if length < min_chunk and length < left:
            continue
        used = min(length, left)
        segments.append((start, start + used))
        left -= used
    return segments, left
