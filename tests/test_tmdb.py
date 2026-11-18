"""TMDB tests use fake responses only. No network or key needed."""
import pytest

from showtime import tmdb
from showtime.planner import make_plan


def fake_getter(path, key, **params):
    if path == "/search/multi":
        if params["query"] == "nothing":
            return {"results": []}
        kind = "tv" if params["query"] == "the boys" else "movie"
        return {"results": [{"media_type": "person", "id": 0}, {"media_type": kind, "id": 7}]}
    if path == "/movie/7":
        return {"title": "Fake Movie", "runtime": 100, "genres": [{"name": "Drama"}],
                "release_date": "2020-05-01",
                "credits": {"crew": [{"job": "Director", "name": "Dee"}], "cast": [{"name": "A"}]}}
    if path == "/tv/7":
        return {"name": "The Boys", "episode_run_time": [], "genres": [{"name": "Action"}],
                "first_air_date": "2019-07-26", "created_by": [{"name": "Eric Kripke"}],
                "seasons": [{"season_number": 0, "episode_count": 3},
                            {"season_number": 1, "episode_count": 8}],
                "credits": {"cast": [{"name": "Karl Urban"}]}}
    if path == "/tv/7/season/1":
        return {"episodes": [{"runtime": 60}, {"runtime": 62}, {"runtime": None}]}
    raise AssertionError(path)


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.setenv("TMDB_API_KEY", "fake")


def test_no_key_returns_none(monkeypatch):
    monkeypatch.delenv("TMDB_API_KEY", raising=False)
    monkeypatch.setattr(tmdb, "ENV_PATH", tmdb.Path("does-not-exist.env"))
    assert tmdb.lookup("anything", getter=fake_getter) is None


def test_movie_lookup(with_key):
    t = tmdb.lookup("x", getter=fake_getter)
    assert (t.name, t.kind, t.runtime, t.director, t.year, t.source) == \
        ("Fake Movie", "movie", 100, "Dee", 2020, "tmdb")


def test_tv_lookup_skips_specials_and_uses_season_runtime(with_key):
    t = tmdb.lookup("the boys", getter=fake_getter)
    assert t.seasons == {1: 8} and t.runtime == 61 and t.director == "Eric Kripke"


def test_no_results(with_key):
    assert tmdb.lookup("nothing", getter=fake_getter) is None


def test_planner_uses_live_title_and_marks_source(with_key):
    p = make_plan("the boys", "season", [], live_lookup=lambda q: tmdb.lookup(q, getter=fake_getter))
    assert p.ok and p.source == "tmdb" and p.needed == 8 * 61


def test_planner_falls_back_when_live_returns_none(with_key):
    p = make_plan("Inception", "single", [], live_lookup=lambda q: None)
    assert p.ok and p.source == "catalog"


def test_catalog_wins_when_live_hit_is_a_worse_name_match():
    from showtime.models import Title
    wrong = Title(name="Dark Shadows", kind="show", runtime=22, seasons={1: 124}, source="tmdb")
    p = make_plan("Dark", "season", [], season=1, live_lookup=lambda q: wrong)
    assert p.ok and p.title.name == "Dark" and p.source == "catalog"
    assert any("weaker match" in w for w in p.warnings)
