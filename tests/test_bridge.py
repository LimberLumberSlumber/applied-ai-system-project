from datetime import date, timedelta

from pawpal_system import Owner, Pet, Scheduler, Task
from showtime.bridge import fit_status, segments_to_rows, tasks_to_busy
from showtime.planner import make_plan


def _owner(*tasks):
    owner = Owner("J")
    pet = Pet("Mochi", "dog")
    for t in tasks:
        pet.add_task(t)
    owner.add_pet(pet)
    return owner


def test_open_task_today_becomes_busy_row_using_duration():
    rows, skipped = tasks_to_busy(_owner(Task("Walk", "08:00", "once", duration=45)))
    assert rows == [("08:00", "08:45", "Pet: Walk (Mochi)")] and skipped == []


def test_completed_future_and_invalid_tasks_are_not_blocking():
    done = Task("Done", "09:00", "once")
    done.mark_complete()
    future = Task("Later", "10:00", "once", due_date=date.today() + timedelta(days=1))
    bad = Task("Bad", "9am", "once")
    rows, skipped = tasks_to_busy(_owner(done, future, bad))
    assert rows == [] and len(skipped) == 1 and "invalid time" in skipped[0]


def test_task_near_midnight_is_clamped():
    rows, _ = tasks_to_busy(_owner(Task("Late", "23:50", "once", duration=60)))
    assert rows == [("23:50", "23:59", "Pet: Late (Mochi)")]


def test_empty_owner_has_no_rows():
    assert tasks_to_busy(Owner("x")) == ([], [])


def test_recurring_task_keeps_duration():
    owner = _owner(Task("Walk", "08:00", "daily", duration=25))
    nxt = Scheduler(owner).mark_task_complete(owner.get_all_tasks()[0])
    assert nxt.duration == 25


def test_pet_task_changes_the_watch_plan():
    owner = _owner(Task("Vet", "08:00", "once", duration=120))
    rows, _ = tasks_to_busy(owner)
    free = make_plan("Inception", "single", [], day_start="08:00", day_end="12:00")
    blocked = make_plan("Inception", "single", rows, day_start="08:00", day_end="12:00")
    assert free.free_total == 240 and blocked.free_total == 120
    assert blocked.left > 0 and free.left == 0


def test_segments_to_rows_and_fit_status():
    assert segments_to_rows([(480, 540)], "Dark") == [("08:00", "09:00", "Watch: Dark")]
    assert fit_status(make_plan("Inception", "single", [])) == "fits"
    assert fit_status(make_plan("The Office", "series", [])) == "partial"
    assert fit_status(make_plan("Inception", "single", [("08:00", "23:00", "x")])) == "none"
    assert fit_status(make_plan("zzzz", "single", [])) == "none"
