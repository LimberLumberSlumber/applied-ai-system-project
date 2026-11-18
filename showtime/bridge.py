"""Glue between the original PawPal+ pet tasks and the ShowTime watch planner."""
from datetime import date

from .guardrails import parse_time
from .models import fmt_time


def tasks_to_busy(owner, day: date = None) -> tuple:
    """Turn the owner's open pet tasks due on `day` into busy rows (start, end, label).

    Returns (rows, skipped). Tasks with an invalid time are skipped and reported, never raised.
    """
    day = day or date.today()
    rows, skipped = [], []
    for pet in owner.pets:
        for task in pet.get_tasks():
            if task.completed or task.due_date != day:
                continue
            try:
                start = parse_time(task.time)
            except ValueError:
                skipped.append(f"Pet task '{task.description}' ({pet.name}) has invalid time '{task.time}'")
                continue
            end = min(start + max(1, task.duration), 23 * 60 + 59)
            if end <= start:
                skipped.append(f"Pet task '{task.description}' ({pet.name}) starts too late to block time")
                continue
            rows.append((fmt_time(start), fmt_time(end), f"Pet: {task.description} ({pet.name})"))
    return rows, skipped


def segments_to_rows(segments: list, title_name: str) -> list:
    """Turn planned (start, end) minute segments into busy rows labeled as a watch session."""
    return [(fmt_time(s), fmt_time(e), f"Watch: {title_name}") for s, e in segments]


def fit_status(plan) -> str:
    """'fits', 'partial', or 'none' for a finished plan."""
    if not plan.ok or not plan.segments:
        return "none"
    return "fits" if plan.left == 0 else "partial"
