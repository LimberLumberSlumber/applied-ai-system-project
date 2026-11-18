import pytest

from showtime.guardrails import confidence, parse_time, validate_busy, validate_day
from showtime.models import BusyBlock
from showtime.scheduler import free_windows, merge_busy, place_session


def test_parse_time_ok():
    assert parse_time("08:30") == 510


@pytest.mark.parametrize("bad", ["", "8", "25:00", "10:75", "ab:cd", None])
def test_parse_time_bad(bad):
    with pytest.raises(ValueError):
        parse_time(bad)


def test_validate_busy_collects_errors_and_overlap_warning():
    blocks, errors, warnings = validate_busy(
        [("09:00", "11:00", "work"), ("10:00", "12:00", "gym"), ("15:00", "14:00", "bad")]
    )
    assert len(blocks) == 2 and len(errors) == 1 and len(warnings) == 1


def test_validate_day_rejects_reversed():
    assert validate_day("22:00", "08:00")[2]


def test_free_windows_basic():
    busy = [BusyBlock(540, 720), BusyBlock(780, 1020)]
    assert free_windows(busy, 480, 1380) == [(480, 540), (720, 780), (1020, 1380)]


def test_free_windows_overlapping_busy_merged():
    busy = [BusyBlock(540, 700), BusyBlock(600, 800)]
    assert merge_busy(busy) == [(540, 800)]
    assert free_windows(busy, 480, 900) == [(480, 540), (800, 900)]


def test_free_windows_no_busy_and_fully_busy():
    assert free_windows([], 480, 600) == [(480, 600)]
    assert free_windows([BusyBlock(400, 700)], 480, 600) == []


def test_place_session_fits_and_splits():
    segs, left = place_session([(0, 60), (100, 200)], 120)
    assert segs == [(0, 60), (100, 160)] and left == 0


def test_place_session_not_enough_time():
    segs, left = place_session([(0, 60)], 100)
    assert left == 40


def test_place_session_skips_tiny_windows():
    segs, left = place_session([(0, 10), (50, 150)], 60)
    assert segs == [(50, 110)] and left == 0


def test_confidence_bounds_and_ordering():
    assert confidence(1.0, "tmdb", True) > confidence(0.5, "catalog", False)
    assert 0 <= confidence(0, "catalog", False, True) <= 1
