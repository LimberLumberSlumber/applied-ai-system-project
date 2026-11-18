"""Evaluation harness: runs predefined inputs offline (catalog only) and prints a pass/fail summary.

Usage: python eval.py
Each case states what should happen, and the harness checks the real planner output against it.
"""
import sys

from showtime.planner import make_plan
from showtime.retriever import load_catalog

BUSY = [("09:00", "12:00", "work"), ("13:00", "17:30", "work")]
CAT = load_catalog()

# name, kwargs for make_plan, check(plan) -> bool, expectation text
CASES = [
    ("exact movie", dict(query="Inception", mode="single", busy_rows=BUSY),
     lambda p: p.ok and p.needed == 148 and p.confidence >= 0.9, "ok, 148 min, conf >= 0.9"),
    ("typo title", dict(query="breaking bda", mode="single", busy_rows=BUSY),
     lambda p: p.ok and p.title.name == "Breaking Bad" and p.warnings, "fuzzy match plus warning"),
    ("season binge minutes", dict(query="Dark", mode="season", season=2, busy_rows=BUSY),
     lambda p: p.ok and p.needed == 8 * 55, "8 episodes x 55 min"),
    ("series total", dict(query="Sherlock", mode="series", busy_rows=BUSY),
     lambda p: p.ok and p.needed == 12 * 88, "12 episodes x 88 min"),
    ("related by director", dict(query="Arrival", mode="single", busy_rows=BUSY),
     lambda p: p.ok and p.related and p.related[0][0].name == "Blade Runner 2049",
     "top related is same director"),
    ("movie in season mode", dict(query="Parasite", mode="season", busy_rows=BUSY),
     lambda p: p.ok and any("movie" in w for w in p.warnings), "warns, treated as single"),
    ("impossible season", dict(query="Arcane", mode="season", season=5, busy_rows=BUSY),
     lambda p: not p.ok and p.errors, "blocked with error"),
    ("bad busy time", dict(query="Arcane", mode="single", busy_rows=[("9am", "10:00", "x")]),
     lambda p: not p.ok and p.errors, "blocked with error"),
    ("end before start", dict(query="Arcane", mode="single", busy_rows=[("12:00", "10:00", "x")]),
     lambda p: not p.ok and p.errors, "blocked with error"),
    ("unknown title", dict(query="Not A Real Show", mode="single", busy_rows=BUSY),
     lambda p: not p.ok and p.errors, "blocked with error"),
    ("empty title", dict(query="  ", mode="single", busy_rows=BUSY),
     lambda p: not p.ok and p.errors, "blocked with error"),
    ("fully busy day", dict(query="Whiplash", mode="single", busy_rows=[("08:00", "23:00", "all")]),
     lambda p: p.ok and not p.segments and p.left == 106, "ok, nothing scheduled"),
    ("live failure fallback", dict(query="Inception", mode="single", busy_rows=BUSY,
                                   live_lookup=lambda q: (_ for _ in ()).throw(TimeoutError())),
     lambda p: p.ok and p.source == "catalog" and p.warnings, "falls back to catalog"),
]


def main() -> int:
    passed, confs = 0, []
    print(f"{'case':<24}{'result':<8}{'conf':<7}expected")
    print("-" * 70)
    for name, kwargs, check, expect in CASES:
        plan = make_plan(titles=CAT, **kwargs)
        try:
            ok = bool(check(plan))
        except Exception as err:  # a crashing check counts as a failure
            ok = False
            print(f"  check crashed: {err!r}")
        passed += ok
        if plan.ok:
            confs.append(plan.confidence)
        print(f"{name:<24}{'PASS' if ok else 'FAIL':<8}{plan.confidence if plan.ok else '-':<7}{expect}")
    print("-" * 70)
    avg = sum(confs) / len(confs) if confs else 0
    print(f"{passed}/{len(CASES)} passed | average confidence on accepted plans: {avg:.2f}")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
