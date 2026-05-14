"""Streamlit app for the Beginner-Friendly Bible Reading Planner."""

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from bible_data import BIBLE_BOOKS, TOTAL_BIBLE_CHAPTERS, get_all_chapters, get_book_names, get_chapter_count
from planner import (
    WEEKDAY_NAMES,
    calculate_streaks,
    choose_completed_chapters,
    encouragement_message,
    estimate_completion_date,
    generate_ai_reflection_prompt,
    generate_initial_plan,
    progress_status,
    recalculate_future_plan,
)
from storage import (
    add_completed_chapters,
    init_db,
    load_assignment,
    load_assignments,
    load_completed_chapters,
    load_history,
    load_settings,
    reset_all_data,
    save_assignments,
    save_history,
    save_settings,
)
from utils import assignments_to_dataframe, format_chapter_list, history_to_dataframe


st.set_page_config(
    page_title="Bible Reading Planner",
    page_icon="📖",
    layout="centered",
)

init_db()


def show_header():
    """Show a friendly app header."""
    st.title("Bible Reading Planner")
    st.caption("A simple plan that adjusts as you read.")


def get_plan_chapters(settings):
    """Load the chapter scope for the current saved plan."""
    return get_all_chapters(settings["start_book"], settings["start_chapter"])


def show_setup(settings):
    """Render the setup form for creating a new plan."""
    st.subheader("Setup Plan")

    with st.form("setup_form"):
        current_year = date.today().year
        default_end_date = date(current_year, 12, 31)

        start_date = st.date_input("Start date", value=date.today())
        end_date = st.date_input("End date", value=default_end_date)

        read_every_day = st.checkbox("Read every day", value=True)
        weekday_labels = list(WEEKDAY_NAMES.keys())
        selected_labels = weekday_labels
        if not read_every_day:
            selected_labels = st.multiselect(
                "Reading days",
                weekday_labels,
                default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            )

        start_option = st.radio(
            "Where do you want to begin?",
            ["Genesis 1", "Choose a book and chapter"],
            horizontal=False,
        )

        start_book = "Genesis"
        start_chapter = 1
        if start_option == "Choose a book and chapter":
            start_book = st.selectbox("Starting book", get_book_names())
            max_chapter = get_chapter_count(start_book)
            start_chapter = st.number_input(
                "Starting chapter",
                min_value=1,
                max_value=max_chapter,
                value=1,
                step=1,
            )

        submitted = st.form_submit_button("Generate plan")

    if submitted:
        selected_weekdays = [WEEKDAY_NAMES[label] for label in selected_labels]
        new_settings = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "selected_weekdays": selected_weekdays,
            "start_book": start_book,
            "start_chapter": int(start_chapter),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

        try:
            assignments, plan_chapters = generate_initial_plan(new_settings)
            new_settings["original_assignments"] = assignments
        except ValueError as error:
            st.error(str(error))
            return

        reset_all_data()
        save_settings(new_settings)
        save_assignments(assignments)
        st.success(f"Plan created with {len(plan_chapters)} chapters.")
        st.rerun()

    if settings:
        st.info("A plan already exists. Use Settings if you want to reset it and create a new one.")


def show_today(settings, assignments, completed_chapters):
    """Render today's assignment and progress summary."""
    st.subheader("Today's Reading")

    if not settings:
        st.warning("Create a plan first in Setup Plan.")
        return

    today = date.today()
    today_key = today.isoformat()
    plan_chapters = get_plan_chapters(settings)
    assigned_today = assignments.get(today_key, [])

    original_assignments = settings.get("original_assignments", assignments)
    expected_completed = sum(
        len(chapters)
        for day, chapters in original_assignments.items()
        if day < today_key
    )
    status = progress_status(expected_completed, len(completed_chapters))
    remaining = len(plan_chapters) - len(completed_chapters)
    percent = (len(completed_chapters) / len(plan_chapters) * 100) if plan_chapters else 100

    st.write(f"**Today:** {today.strftime('%A, %B %d, %Y')}")
    st.info(encouragement_message(status))

    metric_cols = st.columns(2)
    metric_cols[0].metric("Status", status.title())
    metric_cols[1].metric("Completed", len(completed_chapters))

    metric_cols = st.columns(2)
    metric_cols[0].metric("Remaining", remaining)
    metric_cols[1].metric("Complete", f"{percent:.1f}%")

    days_remaining = max((date.fromisoformat(settings["end_date"]) - today).days, 0)
    st.metric("Days remaining to plan end", days_remaining)

    if remaining <= 0:
        st.success("You have completed all chapters in this plan.")
        return

    if assigned_today:
        st.write("**Assigned chapters**")
        st.markdown(format_chapter_list(assigned_today))
    else:
        st.write("No chapters are assigned for today.")

    st.caption(generate_ai_reflection_prompt(assigned_today, status))


def update_progress(settings, assignments, completed_chapters):
    """Render controls for recording today's reading progress."""
    st.subheader("Update Progress")

    if not settings:
        st.warning("Create a plan first in Setup Plan.")
        return

    today_key = date.today().isoformat()
    assigned_today = assignments.get(today_key, [])
    plan_chapters = get_plan_chapters(settings)
    remaining = len(plan_chapters) - len(completed_chapters)

    if remaining <= 0:
        st.success("All chapters are complete. Nothing else to update.")
        return

    st.write("Choose the option that best matches what happened today.")
    update_mode = st.radio(
        "Progress update",
        ["I completed today's reading", "I read a different number of chapters"],
    )

    if update_mode == "I completed today's reading":
        default_read = len([chapter for chapter in assigned_today if chapter not in set(completed_chapters)])
        chapters_read = default_read
        st.write(f"Chapters to mark complete: **{chapters_read}**")
    else:
        chapters_read = st.number_input(
            "How many chapters did you read today?",
            min_value=0,
            max_value=remaining,
            value=0,
            step=1,
        )

    notes = st.text_area("Notes or reflections", placeholder="Optional")

    if st.button("Adjust my plan", type="primary"):
        chapters_to_complete = choose_completed_chapters(
            assigned_today,
            plan_chapters,
            completed_chapters,
            int(chapters_read),
        )
        add_completed_chapters(chapters_to_complete)
        save_history(today_key, assigned_today, chapters_to_complete, int(chapters_read), notes)

        refreshed_completed = load_completed_chapters()
        tomorrow = date.today() + timedelta(days=1)
        try:
            future_plan = recalculate_future_plan(
                settings,
                plan_chapters,
                refreshed_completed,
                tomorrow,
            )
            save_assignments(future_plan, replace_from_date=tomorrow.isoformat())
        except ValueError:
            pass

        st.success("Progress saved and your future plan has been adjusted.")
        st.rerun()


def show_dashboard(settings, assignments, completed_chapters, history):
    """Render progress metrics and reading pace information."""
    st.subheader("Dashboard")

    if not settings:
        st.warning("Create a plan first in Setup Plan.")
        return

    plan_chapters = get_plan_chapters(settings)
    total = len(plan_chapters)
    completed_count = len(completed_chapters)
    remaining = max(total - completed_count, 0)
    percent = (completed_count / total * 100) if total else 100

    future_reading_days = [
        day for day, chapters in assignments.items()
        if day >= date.today().isoformat() and chapters
    ]
    daily_average_needed = remaining / len(future_reading_days) if future_reading_days else 0
    current_streak, longest_streak, missed_days = calculate_streaks(history)
    estimated_date = estimate_completion_date(completed_count, history, remaining)

    original_assignments = settings.get("original_assignments", assignments)
    expected_completed = sum(
        len(chapters)
        for day, chapters in original_assignments.items()
        if day < date.today().isoformat()
    )
    status = progress_status(expected_completed, completed_count)

    st.progress(min(percent / 100, 1.0))
    cols = st.columns(2)
    cols[0].metric("Completed chapters", completed_count)
    cols[1].metric("Remaining chapters", remaining)
    cols = st.columns(2)
    cols[0].metric("Percent complete", f"{percent:.1f}%")
    cols[1].metric("Daily average needed", f"{daily_average_needed:.1f}")
    cols = st.columns(2)
    cols[0].metric("Current streak", current_streak)
    cols[1].metric("Longest streak", longest_streak)
    cols = st.columns(2)
    cols[0].metric("Days missed", missed_days)
    cols[1].metric("Status", status.title())

    if estimated_date:
        st.write(f"Estimated completion date: **{estimated_date.strftime('%B %d, %Y')}**")
    else:
        st.write("Estimated completion date: start recording progress to calculate this.")


def show_history(assignments, history):
    """Render reading history and CSV export buttons."""
    st.subheader("Reading History")

    history_df = history_to_dataframe(history)
    plan_df = assignments_to_dataframe(assignments)

    if history_df.empty:
        st.info("No reading history has been saved yet.")
    else:
        st.dataframe(history_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Export reading history to CSV",
            history_df.to_csv(index=False),
            file_name="reading_history.csv",
            mime="text/csv",
        )

    st.download_button(
        "Export full reading plan to CSV",
        plan_df.to_csv(index=False),
        file_name="reading_plan.csv",
        mime="text/csv",
        disabled=plan_df.empty,
    )


def show_settings(settings):
    """Render reset controls and basic app information."""
    st.subheader("Settings")
    st.write(f"Total chapters in the full Bible dataset: **{TOTAL_BIBLE_CHAPTERS}**")

    if settings:
        st.write("Current plan:")
        st.json(
            {
                "start_date": settings["start_date"],
                "end_date": settings["end_date"],
                "start_book": settings["start_book"],
                "start_chapter": settings["start_chapter"],
            }
        )

    confirm_reset = st.checkbox("Yes, I want to reset my plan and history")
    if st.button("Reset plan", disabled=not confirm_reset):
        reset_all_data()
        st.success("Your plan and history have been reset.")
        st.rerun()


def main():
    """Load data and render all app sections."""
    show_header()

    settings = load_settings()
    assignments = load_assignments()
    completed_chapters = load_completed_chapters()
    history = load_history()

    tabs = st.tabs(
        [
            "Setup Plan",
            "Today's Reading",
            "Update Progress",
            "Dashboard",
            "Reading History",
            "Settings",
        ]
    )

    with tabs[0]:
        show_setup(settings)
    with tabs[1]:
        show_today(settings, assignments, completed_chapters)
    with tabs[2]:
        update_progress(settings, assignments, completed_chapters)
    with tabs[3]:
        show_dashboard(settings, assignments, completed_chapters, history)
    with tabs[4]:
        show_history(assignments, history)
    with tabs[5]:
        show_settings(settings)


if __name__ == "__main__":
    main()
