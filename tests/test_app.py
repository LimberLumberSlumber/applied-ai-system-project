"""Streamlit flow tests (AppTest). Live TMDB search is turned off so no network is needed."""
from streamlit.testing.v1 import AppTest


def _new():
    at = AppTest.from_file("../app.py", default_timeout=30).run()
    assert not at.exception
    return at


def _by_label(elements, label):
    return next(e for e in elements if e.label == label)


def _plan(title, mode_index=0):
    at = _new()
    _by_label(at.text_input, "Movie or show title").set_value(title)
    _by_label(at.radio, "Mode").set_value(list(_by_label(at.radio, "Mode").options)[mode_index])
    _by_label(at.checkbox, "Also search TMDB (live)")  # present even when disabled
    if not _by_label(at.checkbox, "Also search TMDB (live)").disabled:
        _by_label(at.checkbox, "Also search TMDB (live)").set_value(False)
    _by_label(at.button, "Plan it").click()
    return at.run()


def _headers(at):
    return [s.value for s in at.subheader]


# ---- watch planner ----

def test_app_plans_a_known_title():
    at = _plan("Inception")
    assert not at.exception and not at.error
    assert any("Inception" in h for h in _headers(at))
    assert at.metric and float(at.metric[0].value) > 0.8
    assert "You might also like" in _headers(at)


def test_app_shows_guardrail_error_for_unknown_title():
    at = _plan("zzzzqqq")
    assert not at.exception
    assert any("No title found" in e.value for e in at.error)


def test_clicking_a_recommendation_shows_its_data():
    at = _plan("Inception")
    at.button(key="rec_0").click().run()
    assert not at.exception
    assert any(h.startswith("Recommendation:") for h in _headers(at))
    text = " ".join(m.value for m in at.markdown)
    assert "Director/creator" in text and "Cast" in text and "Genres" in text


def test_fit_check_then_confirm_adds_watch_session_to_busy_time():
    at = _plan("Inception")
    at.button(key="rec_0").click().run()
    before = len(at.session_state["busy"])
    at.button(key="rec_check").click().run()
    assert not at.exception
    assert any("fits" in s.value.lower() for s in at.success)
    at.button(key="add_rec").click().run()
    assert "Confirm" in _headers(at)          # confirmation step is shown first
    assert len(at.session_state["busy"]) == before  # nothing added yet
    at.button(key="confirm_yes").click().run()
    busy = at.session_state["busy"]
    assert len(busy) > before and all(row[2].startswith("Watch: ") for row in busy[before:])
    assert at.session_state["pending"] is None


def test_cancel_adds_nothing():
    at = _plan("Inception")
    at.button(key="rec_0").click().run()
    before = len(at.session_state["busy"])
    at.button(key="rec_check").click().run()
    at.button(key="add_rec").click().run()
    at.button(key="confirm_no").click().run()
    assert len(at.session_state["busy"]) == before and at.session_state["pending"] is None


def test_second_session_sees_the_first_as_busy_time():
    at = _plan("Inception")
    at.button(key="add_main").click().run()
    at.button(key="confirm_yes").click().run()
    assert any(r[2] == "Watch: Inception" for r in at.session_state["busy"])


def test_nothing_fits_message_when_day_is_full():
    at = _new()
    at.session_state["busy"] = [("08:00", "23:00", "all day")]
    _by_label(at.text_input, "Movie or show title").set_value("Inception")
    _by_label(at.button, "Plan it").click()
    at.run()
    assert not at.exception
    assert any("Nothing fits" in i.value for i in at.info)


# ---- original PawPal+ capabilities ----

def _add_pet_and_task(at, task_time="08:00", frequency="daily"):
    _by_label(at.button, "Add pet").click()
    at.run()
    _by_label(at.text_input, "Time (HH:MM)").set_value(task_time)
    _by_label(at.selectbox, "Frequency").set_value(frequency)
    _by_label(at.button, "Add task").click()
    return at.run()


def test_pet_tab_add_pet_and_task():
    at = _add_pet_and_task(_new())
    owner = at.session_state["owner"]
    assert [p.name for p in owner.pets] == ["Mochi"]
    assert owner.get_all_tasks()[0].description == "Morning walk"
    assert owner.get_all_tasks()[0].duration == 20


def test_pet_tab_mark_complete_creates_next_recurring_task():
    at = _add_pet_and_task(_new())
    _by_label(at.button, "Mark complete").click()
    at.run()
    tasks = at.session_state["owner"].get_all_tasks()
    assert len(tasks) == 2 and tasks[0].completed and not tasks[1].completed
    assert tasks[1].due_date > tasks[0].due_date
    assert any("Next daily task created" in s.value for s in at.success)


def test_pet_tab_conflict_warning_for_same_time_tasks():
    at = _add_pet_and_task(_new())
    _by_label(at.button, "Add task").click()
    at.run()
    assert any("2 tasks at 08:00" in w.value for w in at.warning)


def test_pet_task_blocks_watch_time():
    at = _add_pet_and_task(_new(), task_time="19:00")
    cells = [str(v) for t in at.table for row in t.value.to_dict("records") for v in row.values()]
    assert "Pet: Morning walk (Mochi)" in cells
