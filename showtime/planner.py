"""Orchestration: validate -> retrieve -> compute minutes -> fit free windows -> explain -> related."""
from dataclasses import dataclass, field
from math import ceil

from .guardrails import confidence, validate_busy, validate_day
from .models import fmt_duration, fmt_time
from .retriever import find_title, load_catalog, related
from .scheduler import free_windows, place_session

MODES = ("single", "season", "series")


@dataclass
class Plan:
    ok: bool = False
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    title: object = None
    mode: str = ""
    needed: int = 0
    free_total: int = 0
    segments: list = field(default_factory=list)
    left: int = 0
    days_needed: int = 0
    confidence: float = 0.0
    source: str = ""
    explanation: list = field(default_factory=list)
    related: list = field(default_factory=list)


def minutes_needed(title, mode: str, season: int = 1) -> tuple:
    """Return (minutes, description). Raises ValueError for impossible requests."""
    if title.runtime <= 0:
        raise ValueError(f"'{title.name}' has no usable runtime")
    if title.kind == "movie" or mode == "single":
        what = "the movie" if title.kind == "movie" else "one episode"
        return title.runtime, what
    if not title.seasons:
        raise ValueError(f"'{title.name}' has no season data")
    if mode == "season":
        if season not in title.seasons:
            raise ValueError(f"'{title.name}' has no season {season} (has {sorted(title.seasons)})")
        eps = title.seasons[season]
        return eps * title.runtime, f"season {season} ({eps} episodes)"
    eps = sum(title.seasons.values())
    return eps * title.runtime, f"the full series ({len(title.seasons)} seasons, {eps} episodes)"


def make_plan(query, mode, busy_rows, day_start="08:00", day_end="23:00",
              season=1, titles=None, live_lookup=None) -> Plan:
    """live_lookup: optional callable(query) -> Title or None (e.g. TMDB). Falls back to the catalog."""
    plan = Plan(mode=mode)
    titles = titles if titles is not None else load_catalog()

    if mode not in MODES:
        plan.errors.append(f"Unknown mode '{mode}', choose one of {MODES}")
    blocks, busy_errors, busy_warnings = validate_busy(busy_rows)
    d_start, d_end, day_errors = validate_day(day_start, day_end)
    plan.errors += busy_errors + day_errors
    plan.warnings += busy_warnings
    if not (query or "").strip():
        plan.errors.append("Title is empty")
    if plan.errors:
        return plan

    title, score, used_fallback = None, 0.0, False
    if live_lookup is not None:
        try:
            title = live_lookup(query)
        except Exception as err:  # a network or parsing failure must never crash the plan
            plan.warnings.append(f"Live lookup failed ({type(err).__name__}); using offline catalog")
            used_fallback = True
        if title is not None:
            score = 1.0
    if title is None:
        title, score = find_title(query, titles)
    if title is None:
        plan.errors.append(f"No title found for '{query}' (best match score {score})")
        return plan
    if score < 1.0:
        plan.warnings.append(f"Matched '{query}' to '{title.name}' (score {score}); please confirm")

    if title.kind == "movie" and mode != "single":
        plan.warnings.append(f"'{title.name}' is a movie, so mode '{mode}' was treated as 'single'")
    try:
        needed, what = minutes_needed(title, mode, season)
    except ValueError as err:
        plan.errors.append(str(err))
        return plan

    windows = free_windows(blocks, d_start, d_end)
    plan.free_total = sum(e - s for s, e in windows)
    plan.segments, plan.left = place_session(windows, needed)
    plan.title, plan.needed, plan.source = title, needed, title.source
    if mode == "series" or plan.left > 0:
        usable = sum(e - s for s, e in windows if e - s >= 20)
        plan.days_needed = ceil(needed / usable) if usable else 0
    complete = title.runtime > 0 and (title.kind == "movie" or bool(title.seasons))
    plan.confidence = confidence(score, title.source, complete, used_fallback)
    plan.related = related(title, titles)

    unit = "movie" if title.kind == "movie" else "episode"
    plan.explanation.append(f"Retrieved '{title.name}' ({title.year}, source: {title.source}); "
                            f"runtime {title.runtime}m per {unit}.")
    plan.explanation.append(f"Mode '{mode}' needs {fmt_duration(needed)} for {what}.")
    plan.explanation.append(f"Free time today: {fmt_duration(plan.free_total)} in {len(windows)} window(s).")
    if plan.left == 0:
        plan.explanation.append("Everything fits today.")
    elif plan.segments:
        plan.explanation.append(f"Only part fits today; {fmt_duration(plan.left)} left over "
                                f"(about {plan.days_needed} days at this free time).")
    else:
        plan.explanation.append("No free window is long enough today.")
    plan.ok = True
    return plan


def format_plan(plan: Plan) -> str:
    lines = []
    for err in plan.errors:
        lines.append(f"  ERROR: {err}")
    for warn in plan.warnings:
        lines.append(f"  Warning: {warn}")
    if plan.ok:
        lines += [f"  {line}" for line in plan.explanation]
        for s, e in plan.segments:
            lines.append(f"  Watch {fmt_time(s)}-{fmt_time(e)} ({fmt_duration(e - s)})")
        lines.append(f"  Confidence: {plan.confidence}")
        for other, _, why in plan.related:
            lines.append(f"  Also try: {other.name} ({why})")
    return "\n".join(lines)
