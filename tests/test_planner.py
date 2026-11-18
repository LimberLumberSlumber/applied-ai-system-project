import pytest

from showtime.models import Title
from showtime.planner import make_plan, minutes_needed
from showtime.retriever import load_catalog

CAT = load_catalog()
BUSY = [("09:00", "12:00", "work"), ("13:00", "17:30", "work")]


def test_single_movie_fits():
    p = make_plan("Inception", "single", BUSY, titles=CAT)
    assert p.ok and p.needed == 148 and p.left == 0 and p.confidence > 0.8
    assert p.related


def test_season_minutes():
    p = make_plan("Breaking Bad", "season", BUSY, season=1, titles=CAT)
    assert p.needed == 7 * 47


def test_series_total_and_days():
    p = make_plan("The Office", "series", BUSY, titles=CAT)
    assert p.needed == (6 + 22 + 23 + 14 + 26 + 26 + 26 + 24 + 23) * 22
    assert p.days_needed >= 2 and p.left > 0


def test_movie_in_season_mode_warns():
    p = make_plan("Inception", "season", BUSY, titles=CAT)
    assert p.ok and any("movie" in w for w in p.warnings)


def test_guardrails_block_bad_input():
    assert not make_plan("Dark", "season", BUSY, season=9, titles=CAT).ok
    assert not make_plan("", "single", BUSY, titles=CAT).ok
    assert not make_plan("Arcane", "single", [("99:00", "10:00", "x")], titles=CAT).ok
    assert not make_plan("Arcane", "bogus", BUSY, titles=CAT).ok
    assert not make_plan("zzzzqqq", "single", BUSY, titles=CAT).ok


def test_fuzzy_match_lowers_confidence_and_warns():
    exact = make_plan("Breaking Bad", "single", BUSY, titles=CAT)
    fuzzy = make_plan("breaking bda", "single", BUSY, titles=CAT)
    assert fuzzy.ok and fuzzy.confidence < exact.confidence and fuzzy.warnings


def test_fully_busy_day():
    p = make_plan("Inception", "single", [("08:00", "23:00", "all")], titles=CAT)
    assert p.ok and p.segments == [] and p.left == 148


def test_live_failure_falls_back():
    def boom(query):
        raise TimeoutError("down")

    p = make_plan("Inception", "single", BUSY, titles=CAT, live_lookup=boom)
    assert p.ok and p.title.source == "catalog"
    assert any("Live lookup failed" in w for w in p.warnings)


def test_minutes_needed_no_runtime():
    with pytest.raises(ValueError):
        minutes_needed(Title(name="x", kind="movie", runtime=0), "single")
