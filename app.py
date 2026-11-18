import streamlit as st

from showtime.models import fmt_duration, fmt_time
from showtime.planner import make_plan
from showtime.retriever import load_catalog
from showtime.tmdb import get_key, lookup

st.set_page_config(page_title="ShowTime Planner", page_icon="🎬")
st.title("ShowTime Planner")
st.caption("Built on PawPal+. Block out your day, pick something to watch, and see when it fits.")

if "busy" not in st.session_state:
    st.session_state.busy = [("09:00", "12:00", "work"), ("13:00", "17:30", "work")]

st.subheader("1. Busy blocks")
with st.form("add_busy", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    start = c1.text_input("Start (HH:MM)", "18:30")
    end = c2.text_input("End (HH:MM)", "19:30")
    label = c3.text_input("Label", "dinner")
    if st.form_submit_button("Add busy block"):
        st.session_state.busy.append((start, end, label))
if st.session_state.busy:
    st.table([{"start": s, "end": e, "label": n} for s, e, n in st.session_state.busy])
    if st.button("Clear busy blocks"):
        st.session_state.busy = []
        st.rerun()

st.subheader("2. What to watch")
catalog = load_catalog()
query = st.text_input("Movie or show title", "Breaking Bad")
mode_label = st.radio(
    "Mode",
    ["Single episode or movie", "Binge a season", "How long to finish the series"],
    horizontal=True,
)
mode = {"Single episode or movie": "single", "Binge a season": "season",
        "How long to finish the series": "series"}[mode_label]
season = st.number_input("Season", min_value=1, value=1, disabled=mode != "season")
d1, d2 = st.columns(2)
day_start = d1.text_input("Day starts", "08:00")
day_end = d2.text_input("Day ends", "23:00")
has_key = get_key() is not None
use_live = st.checkbox("Also search TMDB (live)", value=has_key, disabled=not has_key,
                       help="Needs TMDB_API_KEY. Without it the bundled catalog is used.")

if st.button("Plan it", type="primary"):
    plan = make_plan(query, mode, st.session_state.busy, day_start, day_end, int(season),
                     titles=catalog, live_lookup=lookup if use_live else None)
    for err in plan.errors:
        st.error(err)
    for warn in plan.warnings:
        st.warning(warn)
    if plan.ok:
        st.subheader(f"{plan.title.name} ({plan.title.year})")
        st.caption(f"Source: {plan.source} | Director/creator: {plan.title.director or 'n/a'} | "
                   f"Cast: {', '.join(plan.title.cast) or 'n/a'}")
        for line in plan.explanation:
            st.write(line)
        if plan.segments:
            st.table([{"from": fmt_time(s), "to": fmt_time(e), "length": fmt_duration(e - s)}
                      for s, e in plan.segments])
        else:
            st.info("No free window long enough today.")
        st.metric("Confidence", plan.confidence)
        if plan.confidence < 0.7:
            st.warning("Low confidence: please check the title and data before relying on this.")
        if plan.related:
            st.subheader("You might also like")
            cols = st.columns(len(plan.related))
            for col, (other, _, why) in zip(cols, plan.related):
                col.markdown(f"**{other.name}** ({other.year})")
                col.caption(why)

st.divider()
st.caption("This product uses the TMDB API but is not endorsed or certified by TMDB.")
