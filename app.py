import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task
from showtime.bridge import fit_status, segments_to_rows, tasks_to_busy
from showtime.models import fmt_duration, fmt_time
from showtime.planner import make_plan
from showtime.retriever import find_title, load_catalog
from showtime.tmdb import get_key, lookup

st.set_page_config(page_title="ShowTime Planner", page_icon="🎬")
st.title("ShowTime Planner")
st.caption("Built on PawPal+. Plan pet care tasks, then find free time to watch something.")

catalog = load_catalog()
MODES = {"Single episode or movie": "single", "Binge a season": "season",
         "How long to finish the series": "series"}

state = st.session_state
state.setdefault("owner", Owner("Jordan"))
state.setdefault("busy", [("09:00", "12:00", "work"), ("13:00", "17:30", "work")])
state.setdefault("main_plan", None)
state.setdefault("rec", None)          # name of the clicked recommendation
state.setdefault("rec_checked", None)  # name whose fit check was requested
state.setdefault("pending", None)      # plan waiting for the user's confirmation
state.setdefault("flash", None)

tab_show, tab_pets = st.tabs(["Watch planner", "Pet care (PawPal+)"])

# The pet tab runs first so its tasks are already known when the watch tab builds its busy time.
with tab_pets:
    owner = state.owner
    st.subheader("Owner and pets")
    owner.name = st.text_input("Owner name", value=owner.name)
    c1, c2 = st.columns(2)
    pet_name = c1.text_input("Pet name", value="Mochi")
    species = c2.selectbox("Species", ["dog", "cat", "other"])
    if st.button("Add pet"):
        if pet_name.strip():
            owner.add_pet(Pet(pet_name.strip(), species))
        else:
            st.error("Pet name is empty")
    if owner.pets:
        st.table([{"name": p.name, "species": p.species} for p in owner.pets])
    else:
        st.info("No pets yet. Add one above.")

    st.subheader("Tasks")
    pets = owner.pets
    selected_pet_name = st.selectbox("Pet", [p.name for p in pets]) if pets else None
    t1, t2, t3, t4 = st.columns(4)
    task_title = t1.text_input("Task title", value="Morning walk")
    task_time = t2.text_input("Time (HH:MM)", value="08:00")
    duration = t3.number_input("Minutes", min_value=1, max_value=240, value=20)
    frequency = t4.selectbox("Frequency", ["once", "daily", "weekly"])
    if st.button("Add task", disabled=not pets):
        next(p for p in pets if p.name == selected_pet_name).add_task(
            Task(task_title, task_time, frequency, duration=int(duration)))

    scheduler = Scheduler(owner)
    pet_name_of = {id(t): p.name for p in pets for t in p.get_tasks()}
    st.subheader("Today's Schedule")
    if not pets:
        st.info("Add a pet first, then add tasks for it.")
    elif not scheduler.get_all_tasks():
        st.info("No tasks yet. Add one above.")
    else:
        open_tasks = scheduler.filter_tasks(completed=False)
        if open_tasks:
            idx = st.selectbox(
                "Mark a task complete", range(len(open_tasks)),
                format_func=lambda i: f"{open_tasks[i].time} {open_tasks[i].description} "
                                      f"({pet_name_of[id(open_tasks[i])]})")
            if st.button("Mark complete"):
                done = open_tasks[idx]
                nxt = scheduler.mark_task_complete(done)
                if nxt:
                    st.success(f"Completed '{done.description}'. Next {done.frequency} task created for {nxt.due_date}.")
                else:
                    st.success(f"Completed '{done.description}'.")
                pet_name_of = {id(t): p.name for p in pets for t in p.get_tasks()}
        conflicts = scheduler.detect_conflicts()
        for warning in conflicts:
            st.warning(warning)
        if not conflicts:
            st.success("No scheduling conflicts.")
        f1, f2 = st.columns(2)
        pet_filter = f1.selectbox("Show pet", ["All"] + [p.name for p in pets])
        status_filter = f2.selectbox("Show status", ["All", "To do", "Done"])
        shown = scheduler.filter_tasks(
            pet_name=None if pet_filter == "All" else pet_filter,
            completed={"All": None, "To do": False, "Done": True}[status_filter])
        shown_ids = {id(t) for t in shown}
        rows = [{"time": t.time, "task": t.description, "pet": pet_name_of[id(t)], "minutes": t.duration,
                 "frequency": t.frequency, "due": str(t.due_date), "status": "done" if t.completed else "to do"}
                for t in scheduler.sort_by_time() if id(t) in shown_ids]
        if rows:
            st.table(rows)
        else:
            st.info("No tasks match these filters.")

with tab_show:
    st.subheader("1. Busy time")
    with st.form("add_busy", clear_on_submit=True):
        b1, b2, b3 = st.columns(3)
        start = b1.text_input("Start (HH:MM)", "18:30")
        end = b2.text_input("End (HH:MM)", "19:30")
        label = b3.text_input("Label", "dinner")
        if st.form_submit_button("Add busy block"):
            state.busy.append((start, end, label))
    use_pet_tasks = st.checkbox("Count today's open pet tasks as busy time", value=True)
    pet_rows, skipped = (tasks_to_busy(state.owner) if use_pet_tasks else ([], []))
    for note in skipped:
        st.warning(note)
    effective_busy = state.busy + pet_rows
    if effective_busy:
        st.table([{"start": s, "end": e, "label": n} for s, e, n in effective_busy])
    if state.busy and st.button("Clear manual busy blocks and watch sessions"):
        state.busy = []
        st.rerun()
    if state.flash:
        st.success(state.flash)
        state.flash = None

    d1, d2 = st.columns(2)
    day_start = d1.text_input("Day starts", "08:00")
    day_end = d2.text_input("Day ends", "23:00")

    def show_plan_details(plan):
        for err in plan.errors:
            st.error(err)
        for warn in plan.warnings:
            st.warning(warn)
        if not plan.ok:
            return
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

    def ask_to_add(plan, key):
        """Button that starts the confirmation step for a plan with at least one free slot."""
        if fit_status(plan) == "none":
            st.info("Nothing fits today, so there is nothing to add.")
        elif st.button("Add to schedule", key=key):
            state.pending = plan
            st.rerun()

    st.subheader("2. What to watch")
    query = st.text_input("Movie or show title", "Breaking Bad")
    mode_label = st.radio("Mode", list(MODES), horizontal=True)
    mode = MODES[mode_label]
    season = st.number_input("Season", min_value=1, value=1, disabled=mode != "season")
    has_key = get_key() is not None
    use_live = st.checkbox("Also search TMDB (live)", value=has_key, disabled=not has_key,
                           help="Needs TMDB_API_KEY. Without it the bundled catalog is used.")
    if st.button("Plan it", type="primary"):
        state.main_plan = make_plan(query, mode, effective_busy, day_start, day_end, int(season),
                                    titles=catalog, live_lookup=lookup if use_live else None)
        state.rec = state.rec_checked = state.pending = None

    plan = state.main_plan
    if plan is not None:
        if plan.ok:
            st.subheader(f"{plan.title.name} ({plan.title.year})")
            st.caption(f"Source: {plan.source} | Director/creator: {plan.title.director or 'n/a'} | "
                       f"Cast: {', '.join(plan.title.cast) or 'n/a'}")
        show_plan_details(plan)
        if plan.ok:
            ask_to_add(plan, "add_main")
            if plan.related:
                st.subheader("You might also like")
                cols = st.columns(len(plan.related))
                for i, (col, (other, _, why)) in enumerate(zip(cols, plan.related)):
                    col.markdown(f"**{other.name}** ({other.year})")
                    col.caption(why)
                    if col.button("View details", key=f"rec_{i}"):
                        state.rec, state.rec_checked, state.pending = other.name, None, None
                        st.rerun()

    if state.rec:
        rec, _ = find_title(state.rec, catalog)
        st.divider()
        st.subheader(f"Recommendation: {rec.name} ({rec.year})")
        st.write(f"**Type:** {rec.kind} | **Runtime:** {rec.runtime} min"
                 + (f" per episode | **Seasons:** {len(rec.seasons)}" if rec.seasons else ""))
        st.write(f"**Director/creator:** {rec.director or 'n/a'}")
        st.write(f"**Cast:** {', '.join(rec.cast) or 'n/a'}")
        st.write(f"**Genres:** {', '.join(rec.genres) or 'n/a'}")
        rec_mode = MODES[st.radio("Mode for this title", list(MODES), horizontal=True, key="rec_mode")]
        rec_season = st.number_input("Season", min_value=1, value=1, key="rec_season",
                                     disabled=rec_mode != "season")
        if st.button("Check if it fits my schedule", key="rec_check"):
            state.rec_checked = rec.name
        if state.rec_checked == rec.name:
            rec_plan = make_plan(rec.name, rec_mode, effective_busy, day_start, day_end,
                                 int(rec_season), titles=catalog)
            show_plan_details(rec_plan)
            status = fit_status(rec_plan)
            if status == "fits":
                st.success("It fits in your free time today.")
            elif status == "partial":
                st.warning(f"Only part fits today ({fmt_duration(rec_plan.left)} left over).")
            if rec_plan.ok:
                ask_to_add(rec_plan, "add_rec")
        if st.button("Close details", key="rec_close"):
            state.rec = state.rec_checked = None
            st.rerun()

    if state.pending is not None:
        pend = state.pending
        st.divider()
        st.subheader("Confirm")
        spans = ", ".join(f"{fmt_time(s)}-{fmt_time(e)}" for s, e in pend.segments)
        st.write(f"Add **{pend.title.name}** to your schedule at {spans}?")
        if pend.left > 0:
            st.warning(f"Only part fits. {fmt_duration(pend.left)} will remain unscheduled.")
        y, n = st.columns(2)
        if y.button("Yes, add it", key="confirm_yes", type="primary"):
            state.busy += segments_to_rows(pend.segments, pend.title.name)
            state.flash = f"Added {pend.title.name} ({spans}). It now counts as busy time."
            state.pending = None
            st.rerun()
        if n.button("Cancel", key="confirm_no"):
            state.pending = None
            st.rerun()

st.divider()
st.caption("This product uses the TMDB API but is not endorsed or certified by TMDB.")
