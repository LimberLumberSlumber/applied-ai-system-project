"""Streamlit smoke tests. Live TMDB search is left off so no network is needed."""
from streamlit.testing.v1 import AppTest


def _run_plan(title, mode_index=0):
    at = AppTest.from_file("../app.py", default_timeout=30).run()
    assert not at.exception
    at.text_input[3].set_value(title)  # title box (after start, end, label)
    at.radio[0].set_value(at.radio[0].options[mode_index])
    if at.checkbox:
        at.checkbox[0].set_value(False)
    next(b for b in at.button if b.label == "Plan it").click()
    return at.run()


def test_app_plans_a_known_title():
    at = _run_plan("Inception")
    assert not at.exception and not at.error
    assert any("Inception" in s.value for s in at.subheader)
    assert at.metric and float(at.metric[0].value) > 0.8


def test_app_shows_guardrail_error_for_unknown_title():
    at = _run_plan("zzzzqqq")
    assert not at.exception
    assert any("No title found" in e.value for e in at.error)
