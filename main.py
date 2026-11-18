"""CLI demo of ShowTime Planner. Offline catalog by default; add --live for TMDB when a key is set."""
import sys

from showtime.planner import format_plan, make_plan

BUSY = [("09:00", "12:00", "work"), ("13:00", "17:30", "work"), ("18:30", "19:30", "dinner")]

CASES = [
    ("Inception", "single", 1, BUSY, "Movie tonight"),
    ("breaking bda", "season", 1, BUSY, "Binge season 1 (typo in title)"),
    ("The Office", "series", 1, BUSY, "How long to finish the series"),
    ("Dark", "season", 9, BUSY, "Guardrail: impossible season"),
    ("Arcane", "single", 1, [("25:00", "26:00", "oops")], "Guardrail: bad busy time"),
    ("Not A Real Show", "single", 1, BUSY, "Guardrail: unknown title"),
]


def get_live():
    if "--live" not in sys.argv:
        return None
    from showtime.tmdb import lookup
    return lookup


def main() -> None:
    live = get_live()
    print("ShowTime Planner demo (busy: " + ", ".join(f"{s}-{e} {n}" for s, e, n in BUSY) + ")")
    for query, mode, season, busy, label in CASES:
        print("=" * 60)
        print(f"{label}: title='{query}' mode={mode} season={season}")
        print(format_plan(make_plan(query, mode, busy, season=season, live_lookup=live)))


if __name__ == "__main__":
    main()
