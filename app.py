"""Streamlit app for the Bible Reading Planner."""

from datetime import date, datetime, timedelta
import json
from urllib.parse import quote
from urllib.request import urlopen
import streamlit as st

from bible_data import NEW_TESTAMENT_BOOKS, OLD_TESTAMENT_BOOKS, TOTAL_BIBLE_CHAPTERS, get_all_chapters, get_book_chapters, get_book_names, get_chapter_count
from planner import WEEKDAY_NAMES, encouragement_message, generate_ai_reflection_prompt, generate_initial_plan, progress_status, recalculate_future_plan
from storage import (
    add_completed_chapters, authenticate_profile, create_or_join_group, create_profile,
    export_profile_data, import_profile_data,
    init_db, invite_progress_viewer, load_allowed_viewers, load_assignments,
    load_completed_chapters, load_group_progress, load_groups_for_profile, load_history,
    load_profile, load_reading_position, load_reading_positions, load_settings,
    load_shared_profiles_for_viewer, reset_all_data, save_assignments, save_history,
    save_reading_position, save_settings,
)
from utils import assignments_to_dataframe, format_chapter_list, history_to_dataframe

st.set_page_config(page_title="Bible Reading Planner", page_icon="📖", layout="centered")
init_db()

ONLINE_PUBLIC_DOMAIN_VERSIONS = {
    "KJV": "kjv",
    "ASV": "asv",
    "WEB": "web",
}
LICENSED_OR_NOT_INSTALLED_VERSIONS = [
    "NIV - English (requires license/API)",
    "Amplified - English (requires license/API)",
    "NKJV - English (requires license/API)",
    "Swahili Union Version (requires licensed text/API)",
    "Biblia Habari Njema - Swahili (requires licensed text/API)",
    "Neno Bibilia Takatifu - Swahili (requires licensed text/API)",
]


def set_screen(screen_name):
    st.session_state["screen"] = screen_name


def landing_page():
    st.title("Bible Reading Planner")
    st.write("Sign in to track your Bible reading progress and share it with invited viewers.")
    login_tab, signup_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            pin = st.text_input("PIN", type="password")
            submitted = st.form_submit_button("Log in", type="primary")
        if submitted:
            profile = authenticate_profile(username, pin)
            if profile:
                st.session_state["profile_id"] = profile["id"]
                st.session_state["screen"] = "Start" if load_settings(profile["id"]) else "Setup Plan"
                st.rerun()
            st.error("That username or PIN did not match.")

    with signup_tab:
        with st.form("signup_form"):
            name = st.text_input("Name")
            username = st.text_input("Choose a username")
            pin = st.text_input("Choose a PIN", type="password")
            submitted = st.form_submit_button("Create account")
        if submitted:
            if not name.strip() or not username.strip() or not pin.strip():
                st.warning("Please enter your name, username, and PIN.")
            else:
                try:
                    profile_id = create_profile(name, username, pin)
                    st.session_state["profile_id"] = profile_id
                    st.session_state["screen"] = "Setup Plan"
                    st.rerun()
                except Exception:
                    st.error("That username may already exist. Try another one.")
    st.info("Prototype auth is local. For production, use Supabase Auth, Clerk, Firebase Auth, or another proper auth service.")


def get_plan_chapters(settings):
    return settings.get("plan_chapters") or get_all_chapters(settings["start_book"], settings["start_chapter"])


def pct(done, total):
    return done / total * 100 if total else 0


def testament_counts(chapters, completed):
    completed_set = set(completed)
    old_total = sum(1 for chapter in chapters if chapter.rsplit(" ", 1)[0] in OLD_TESTAMENT_BOOKS)
    new_total = sum(1 for chapter in chapters if chapter.rsplit(" ", 1)[0] in NEW_TESTAMENT_BOOKS)
    old_done = sum(1 for chapter in chapters if chapter in completed_set and chapter.rsplit(" ", 1)[0] in OLD_TESTAMENT_BOOKS)
    new_done = sum(1 for chapter in chapters if chapter in completed_set and chapter.rsplit(" ", 1)[0] in NEW_TESTAMENT_BOOKS)
    return old_done, old_total, new_done, new_total


def preview_plan(settings):
    try:
        assignments, chapters = generate_initial_plan(settings)
    except ValueError as error:
        st.warning(str(error))
        return None, None

    reading_days = [day for day, day_chapters in assignments.items() if day_chapters]
    st.write("**Plan preview**")
    cols = st.columns(3)
    cols[0].metric("Chapters in this plan", len(chapters))
    cols[1].metric("Reading days", len(reading_days))
    cols[2].metric("Average per day", f"{(len(chapters) / len(reading_days)):.1f}" if reading_days else "0")

    if settings.get("plan_style") == "Mixed Old and New Testament":
        old_count = sum(1 for chapter in chapters if chapter.rsplit(" ", 1)[0] in OLD_TESTAMENT_BOOKS)
        new_count = sum(1 for chapter in chapters if chapter.rsplit(" ", 1)[0] in NEW_TESTAMENT_BOOKS)
        scope_text = (
            "It will wrap around and include the earlier chapters too."
            if settings.get("plan_scope") == "Read the whole Bible starting from my selected points"
            else "It only includes chapters from those selected points onward."
        )
        st.caption(
            f"This mixed plan starts Old Testament at {settings['old_start_book']} {settings['old_start_chapter']} "
            f"and New Testament at {settings['new_start_book']} {settings['new_start_chapter']}. "
            f"It includes {old_count} Old Testament chapters and {new_count} New Testament chapters. {scope_text}"
        )
    else:
        if settings.get("plan_scope") == "Read the whole Bible starting from my selected point":
            st.caption(
                f"This plan starts at {settings['start_book']} {settings['start_chapter']}, continues to Revelation, "
                "then wraps around to Genesis so the full Bible is included."
            )
        else:
            st.caption(f"This plan starts at {settings['start_book']} {settings['start_chapter']} and continues to Revelation only.")

    for day, day_chapters in list(assignments.items())[:5]:
        st.write(f"**{day}:** {', '.join(day_chapters) if day_chapters else 'No reading assigned'}")
    return assignments, chapters


def projected_finish_days(history, remaining):
    active_days = [row for row in history if int(row.get("chapters_read", 0)) > 0]
    if remaining <= 0:
        return 0
    if not active_days:
        return None
    total_read = sum(int(row.get("chapters_read", 0)) for row in active_days)
    daily_average = total_read / len(active_days)
    return int((remaining + daily_average - 1) // daily_average) if daily_average else None


def setup_plan(settings, profile):
    st.subheader("Setup Plan")
    if settings:
        st.info("You already have a plan. Existing users are sent straight to progress.")
        st.button("Go to progress", on_click=set_screen, args=("Update Progress",))
        return
    default_end = date(date.today().year, 12, 31)
    start_date = st.date_input("Start date", value=date.today())
    end_date = st.date_input("End date", value=default_end)
    read_every_day = st.checkbox("Read every day", value=True)
    weekday_labels = list(WEEKDAY_NAMES.keys())
    selected_labels = weekday_labels
    if not read_every_day:
        selected_labels = st.multiselect("Reading days", weekday_labels, default=weekday_labels[:5])

    plan_style = st.radio("Reading style", ["Canonical order", "Mixed Old and New Testament"])
    start_book = "Genesis"
    start_chapter = 1
    old_percent = 70
    old_start_book = "Genesis"
    old_start_chapter = 1
    new_start_book = "Matthew"
    new_start_chapter = 1
    plan_scope = "Read from selected start to the end"

    if plan_style == "Canonical order":
        start_option = st.radio("Where do you want to begin?", ["Genesis 1", "Choose a book and chapter"])
        if start_option == "Choose a book and chapter":
            st.info("Pick the exact place where your Bible reading plan should start.")
            start_book = st.selectbox("Starting book", get_book_names())
            start_chapter = st.number_input("Starting chapter", 1, get_chapter_count(start_book), 1)
            plan_scope = st.radio(
                "What should happen to chapters before this starting point?",
                [
                    "Read the whole Bible starting from my selected point",
                    "Read from selected start to the end",
                ],
            )
        else:
            plan_scope = "Read the whole Bible starting from my selected point"
    else:
        old_percent = st.slider("Old Testament percentage", 10, 90, 70, 5)
        st.info("Pick where each Testament should begin for your mixed reading plan.")
        old_start_book = st.selectbox("Old Testament starting book", OLD_TESTAMENT_BOOKS)
        old_start_chapter = st.number_input("Old Testament starting chapter", 1, get_chapter_count(old_start_book), 1)
        new_start_book = st.selectbox("New Testament starting book", NEW_TESTAMENT_BOOKS)
        new_start_chapter = st.number_input("New Testament starting chapter", 1, get_chapter_count(new_start_book), 1)
        plan_scope = st.radio(
            "What should happen to earlier chapters before those starting points?",
            [
                "Read the whole Bible starting from my selected points",
                "Read from selected start to the end",
            ],
        )

    preview_settings = {
        "start_date": start_date.isoformat(), "end_date": end_date.isoformat(),
        "selected_weekdays": [WEEKDAY_NAMES[label] for label in selected_labels],
        "start_book": start_book, "start_chapter": int(start_chapter),
        "plan_style": plan_style, "old_testament_percent": int(old_percent),
        "old_start_book": old_start_book, "old_start_chapter": int(old_start_chapter),
        "new_start_book": new_start_book, "new_start_chapter": int(new_start_chapter),
        "plan_scope": plan_scope,
    }
    preview_assignments = None
    preview_chapters = None
    if start_date <= end_date and selected_labels:
        preview_assignments, preview_chapters = preview_plan(preview_settings)

    submitted = st.button("Generate plan", type="primary")
    if submitted:
        if start_date > end_date:
            st.error("Start date must be before or equal to end date.")
            return
        if not selected_labels:
            st.error("Choose at least one reading day.")
            return
        settings_to_save = {
            "start_date": start_date.isoformat(), "end_date": end_date.isoformat(),
            "selected_weekdays": [WEEKDAY_NAMES[label] for label in selected_labels],
            "start_book": start_book, "start_chapter": int(start_chapter),
            "plan_style": plan_style, "old_testament_percent": int(old_percent),
            "old_start_book": old_start_book, "old_start_chapter": int(old_start_chapter),
            "new_start_book": new_start_book, "new_start_chapter": int(new_start_chapter),
            "plan_scope": plan_scope,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        if preview_assignments is not None and preview_chapters is not None:
            assignments, chapters = preview_assignments, preview_chapters
        else:
            assignments, chapters = generate_initial_plan(settings_to_save)
        settings_to_save["original_assignments"] = assignments
        settings_to_save["plan_chapters"] = chapters
        reset_all_data(profile["id"])
        save_settings(settings_to_save, profile["id"])
        save_assignments(assignments, profile["id"])
        st.session_state["screen"] = "Update Progress"
        st.rerun()


def status_for(settings, assignments, completed):
    today_key = date.today().isoformat()
    expected = sum(len(ch) for day, ch in settings.get("original_assignments", assignments).items() if day < today_key)
    plan_completed = len(set(completed).intersection(get_plan_chapters(settings)))
    return progress_status(expected, plan_completed)


def today_screen(settings, assignments, completed, profile_id):
    st.subheader("Today's Reading")
    if not settings:
        st.warning("Create a plan first.")
        st.button("Set up my plan", on_click=set_screen, args=("Setup Plan",))
        return
    assigned = assignments.get(date.today().isoformat(), [])
    history_today = {row["date"]: row for row in load_history(profile_id)}.get(date.today().isoformat())
    status = status_for(settings, assignments, completed)
    if history_today and int(history_today["chapters_read"]) == 0:
        st.error("You have not read anything today.")
    else:
        st.info(encouragement_message(status))
    chapters = get_plan_chapters(settings)
    plan_completed = len(set(completed).intersection(chapters))
    st.metric("Current plan complete", f"{plan_completed / len(chapters) * 100:.1f}%")
    st.metric("Plan chapters completed", plan_completed)
    st.write("**Assigned chapters**")
    st.markdown(format_chapter_list(assigned))
    st.caption(generate_ai_reflection_prompt(assigned, status))


def progress_screen(settings, assignments, completed, profile):
    st.subheader("Update Progress")
    if not settings:
        st.warning("New users should set up a plan first.")
        st.button("Set up my plan", on_click=set_screen, args=("Setup Plan",))
        return
    progress_date = st.date_input("Progress date", value=date.today())
    key = progress_date.isoformat()
    if progress_date != date.today():
        st.info("You are adding progress for a previous date.")
    completed_set = set(completed)
    assigned = assignments.get(key, [])
    assigned_unread = [chapter for chapter in assigned if chapter not in completed_set]
    if assigned and not assigned_unread:
        st.success("Congratulations for finishing your day's assigned chapters. You can still input any extras you've read.")
        selected_assigned = []
    elif assigned_unread:
        selected_assigned = st.multiselect("Assigned chapters read", assigned_unread)
    else:
        st.info("No assigned chapters are available for this date. You can still input extra chapters you read.")
        selected_assigned = []
    mode = st.radio(
        "Additional progress",
        ["I read beyond the assigned book/chapters list", "Enter only a number"],
    )
    extra_selected = []
    manual_count = 0
    if mode == "I read beyond the assigned book/chapters list":
        testament = st.radio("Which Testament did you read from?", ["Old Testament", "New Testament"])
        books = OLD_TESTAMENT_BOOKS if testament == "Old Testament" else NEW_TESTAMENT_BOOKS
        book = st.selectbox("Extra book read", books)
        choices = [
            chapter
            for chapter in get_book_chapters(book)
            if chapter not in completed_set and chapter not in assigned_unread
        ]
        extra_selected = st.multiselect("Extra chapters read", choices)
    else:
        manual_count = st.number_input("Additional chapters read but not selected", 0, 1189, 0)
    notes = st.text_area("Notes or reflections", placeholder="Optional")
    completed_today = selected_assigned + extra_selected
    plan_chapters = get_plan_chapters(settings)
    if manual_count:
        unread = [chapter for chapter in plan_chapters if chapter not in completed_set and chapter not in completed_today]
        completed_today.extend(unread[: int(manual_count)])
    if not completed_today:
        st.error("You have not selected or entered any chapters. Saving now records that nothing was read.")
    if st.button("Save progress and adjust my plan", type="primary"):
        add_completed_chapters(completed_today, profile["id"])
        save_history(key, assigned, completed_today, len(completed_today), notes, profile["id"])
        refreshed = load_completed_chapters(profile["id"])
        recalc_from = max(progress_date + timedelta(days=1), date.today() + timedelta(days=1))
        try:
            save_assignments(recalculate_future_plan(settings, plan_chapters, refreshed, recalc_from), profile["id"], replace_from_date=recalc_from.isoformat())
        except ValueError:
            pass
        st.session_state["screen"] = "Dashboard"
        st.rerun()


def start_screen(settings, assignments, completed, history, profile):
    st.subheader(f"Welcome back, {profile['name']}")
    if not settings:
        st.info("Let's create your reading plan first.")
        st.button("Set up my plan", type="primary", on_click=set_screen, args=("Setup Plan",))
        return

    today_key = date.today().isoformat()
    assigned = assignments.get(today_key, [])
    plan_chapters = get_plan_chapters(settings)
    plan_completed = len(set(completed).intersection(plan_chapters))
    remaining = max(len(plan_chapters) - plan_completed, 0)
    finish_days = projected_finish_days(history or [], remaining)

    st.write("What would you like to do now?")
    cols = st.columns(2)
    with cols[0]:
        st.markdown("### Read today's Bible")
        if assigned:
            st.write(f"{len(assigned)} chapter(s) assigned today.")
            st.caption(", ".join(assigned[:3]) + ("..." if len(assigned) > 3 else ""))
        else:
            st.write("Open your reader and continue through your plan.")
        if st.button("Read Bible", type="primary", use_container_width=True):
            st.session_state["screen"] = "Bible Reader"
            st.rerun()

    with cols[1]:
        st.markdown("### Update progress")
        st.write("Record what you read and let the plan adjust.")
        st.caption(f"{remaining} chapter(s) left in your current plan.")
        if st.button("Update Progress", use_container_width=True):
            st.session_state["screen"] = "Update Progress"
            st.rerun()

    st.divider()
    metric_cols = st.columns(3)
    metric_cols[0].metric("Current plan", f"{pct(plan_completed, len(plan_chapters)):.1f}%")
    metric_cols[1].metric("Completed", plan_completed)
    metric_cols[2].metric("Remaining", remaining)

    if finish_days == 0:
        st.success("You have completed this plan.")
    elif finish_days is not None:
        st.info(f"If you keep this pace, you will finish in about {finish_days} days.")


def split_chapter_label(chapter_label):
    book, chapter = chapter_label.rsplit(" ", 1)
    return book, int(chapter)


@st.cache_data(ttl=3600)
def fetch_public_domain_chapter(chapter_label, version):
    """Fetch one chapter from bible-api.com for supported public-domain versions."""
    translation = ONLINE_PUBLIC_DOMAIN_VERSIONS[version]
    url = f"https://bible-api.com/{quote(chapter_label)}?translation={translation}"
    with urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))
    if "verses" not in data:
        raise ValueError(data.get("error", "Bible text could not be loaded."))
    return [
        {"verse": int(item["verse"]), "text": item["text"].strip()}
        for item in data["verses"]
    ]


def version_select(label, key):
    options = list(ONLINE_PUBLIC_DOMAIN_VERSIONS) + LICENSED_OR_NOT_INSTALLED_VERSIONS
    return st.selectbox(label, options, key=key)


def render_chapter_reader(chapter_label, version, profile_id, key_prefix, compact=False):
    if version not in ONLINE_PUBLIC_DOMAIN_VERSIONS:
        st.warning(
            "This translation is not bundled because it requires a license or paid/API provider. "
            "For production, connect API.Bible, YouVersion for Churches if eligible, or another licensed Bible text provider."
        )
        return

    position = load_reading_position(profile_id, chapter_label)
    last_verse = int(position["verse"]) if position and position.get("version") == version else 0
    try:
        verses = fetch_public_domain_chapter(chapter_label, version)
    except Exception as error:
        st.error(f"Could not load {chapter_label} in {version}. Check internet access or try another version.")
        st.caption(str(error))
        return

    if not compact and last_verse:
        st.info(f"Last saved position: {chapter_label}:{last_verse} in {version}.")

    max_verse = max([item["verse"] for item in verses], default=1)
    selected_verse = st.slider(
        "I ended at verse",
        min_value=1,
        max_value=max_verse,
        value=min(max(last_verse or 1, 1), max_verse),
        key=f"{key_prefix}_verse_slider",
    )
    if st.button("Save reading position", key=f"{key_prefix}_save_position"):
        save_reading_position(profile_id, chapter_label, selected_verse, version, "Read on this site")
        st.success(f"Saved your place at {chapter_label}:{selected_verse}.")

    for item in verses:
        verse_number = item["verse"]
        marker = "✓ " if last_verse and verse_number <= last_verse else ""
        st.markdown(f"**{marker}{verse_number}.** {item['text']}")


def bible_reader(settings, assignments, profile):
    st.subheader("Bible Reader")
    st.caption("Choose whether to read inside the app or track your place while using your own Bible.")

    if not settings:
        st.warning("Create a reading plan first so the reader can follow your assignments.")
        st.button("Set up my plan", on_click=set_screen, args=("Setup Plan",))
        return

    today_chapters = assignments.get(date.today().isoformat(), [])
    plan_chapters = get_plan_chapters(settings)
    default_chapters = today_chapters or plan_chapters
    if not default_chapters:
        st.info("No chapters are available in this plan yet.")
        return

    reading_mode = st.radio("How do you want to read?", ["Read on this site", "Use my physical Bible"])
    chapter_label = st.selectbox("Chapter to read", default_chapters, index=0)

    saved_positions = load_reading_positions(profile["id"])
    if saved_positions:
        latest = saved_positions[0]
        st.caption(f"Most recent saved place: {latest['chapter']}:{latest['verse']} ({latest['version']})")

    if reading_mode == "Use my physical Bible":
        book, chapter_number = split_chapter_label(chapter_label)
        st.write(f"Open your Bible to **{book} {chapter_number}**.")
        verse = st.number_input("Verse where I stopped", min_value=1, max_value=200, value=1, step=1)
        version = st.text_input("Bible version I used", value="Physical Bible")
        if st.button("Save my physical Bible position", type="primary"):
            save_reading_position(profile["id"], chapter_label, int(verse), version, "Physical Bible")
            st.success(f"Saved your place at {chapter_label}:{int(verse)}.")
        return

    compare = st.checkbox("Split screen and compare two versions")
    if compare:
        left, right = st.columns(2)
        with left:
            left_version = version_select("Left version", "left_reader_version")
            st.write(f"**{chapter_label} - {left_version}**")
            render_chapter_reader(chapter_label, left_version, profile["id"], "left_reader", compact=True)
        with right:
            right_version = version_select("Right version", "right_reader_version")
            st.write(f"**{chapter_label} - {right_version}**")
            render_chapter_reader(chapter_label, right_version, profile["id"], "right_reader", compact=True)
    else:
        version = version_select("Bible version", "single_reader_version")
        st.write(f"**{chapter_label} - {version}**")
        render_chapter_reader(chapter_label, version, profile["id"], "single_reader")


def dashboard(settings, assignments, completed, history=None, title="Dashboard"):
    st.subheader(title)
    if not settings:
        st.warning("No plan has been created yet.")
        return
    plan_chapters = get_plan_chapters(settings)
    all_chapters = get_all_chapters()
    completed_set = set(completed)
    whole_completed = len(completed_set.intersection(all_chapters))
    whole_percent = pct(whole_completed, TOTAL_BIBLE_CHAPTERS)
    plan_completed = len(completed_set.intersection(plan_chapters))
    total = len(plan_chapters)
    plan_percent = pct(plan_completed, total)
    remaining = max(total - plan_completed, 0)
    old_done, old_total, new_done, new_total = testament_counts(all_chapters, completed)
    finish_days = projected_finish_days(history or [], remaining)

    st.progress(min(plan_percent / 100, 1.0))
    cols = st.columns(2)
    cols[0].metric("Current plan", f"{plan_percent:.1f}%", f"{plan_completed}/{total}")
    cols[1].metric("Whole Bible", f"{whole_percent:.1f}%", f"{whole_completed}/{TOTAL_BIBLE_CHAPTERS}")

    cols = st.columns(2)
    cols[0].metric("Old Testament", f"{pct(old_done, old_total):.1f}%", f"{old_done}/{old_total}")
    cols[1].metric("New Testament", f"{pct(new_done, new_total):.1f}%", f"{new_done}/{new_total}")

    cols = st.columns(2)
    cols[0].metric("Plan remaining", remaining)
    cols[1].metric("Status", status_for(settings, assignments, completed).title())

    if finish_days == 0:
        st.success("Projection: you have completed this plan.")
    elif finish_days is None:
        st.info("Projection: add a few reading updates and I will estimate your finish date.")
    else:
        st.info(f"Projection: if you keep this pace, you will finish in about {finish_days} days.")


def backup_tools(profile):
    st.subheader("Backup And Restore")
    backup = export_profile_data(profile["id"])
    st.download_button(
        "Export my user data",
        json.dumps(backup, indent=2),
        file_name=f"bible_planner_backup_{profile['username']}.json",
        mime="application/json",
    )
    uploaded = st.file_uploader("Restore user data from backup JSON", type=["json"])
    if uploaded is not None:
        try:
            backup_data = json.loads(uploaded.getvalue().decode("utf-8"))
            if st.button("Restore this backup"):
                import_profile_data(profile["id"], backup_data)
                st.success("Backup restored. Reloading your dashboard.")
                st.session_state["screen"] = "Dashboard"
                st.rerun()
        except json.JSONDecodeError:
            st.error("That file is not valid JSON.")


def leaderboard(profile):
    st.subheader("Leaderboard")
    rows = []

    for group in load_groups_for_profile(profile["id"]):
        for row in load_group_progress(group["id"]):
            row = dict(row)
            row["source"] = f"Group: {group['name']}"
            rows.append(row)

    for person in load_shared_profiles_for_viewer(profile["id"]):
        person_settings = load_settings(person["id"])
        person_completed = load_completed_chapters(person["id"])
        total = len(get_plan_chapters(person_settings)) if person_settings else 0
        rows.append(
            {
                "name": person["name"],
                "username": person["username"],
                "completed_chapters": len(person_completed),
                "total_chapters": total,
                "percent_complete": round(pct(len(person_completed), total), 1),
                "source": "Shared with you",
            }
        )

    if not rows:
        st.info("Join a group or ask someone to share their progress with you to see the leaderboard.")
        return

    unique = {}
    for row in rows:
        key = row.get("username") or row["name"]
        if key not in unique or row["percent_complete"] > unique[key]["percent_complete"]:
            unique[key] = row

    sorted_rows = sorted(unique.values(), key=lambda item: item["percent_complete"], reverse=True)
    st.dataframe(sorted_rows, use_container_width=True, hide_index=True)


def groups(profile):
    st.subheader("Groups And Shared Progress")
    with st.form("invite_form"):
        username = st.text_input("Invite someone by username")
        submitted = st.form_submit_button("Allow them to view my progress")
    if submitted:
        ok, message = invite_progress_viewer(profile["id"], username)
        st.success(message) if ok else st.warning(message)
    viewers = load_allowed_viewers(profile["id"])
    if viewers:
        st.write("People allowed to view your progress:")
        st.dataframe(viewers, use_container_width=True, hide_index=True)
    with st.form("group_form"):
        group_name = st.text_input("Group name")
        submitted = st.form_submit_button("Join group")
    if submitted and group_name.strip():
        create_or_join_group(profile["id"], group_name)
        st.rerun()
    my_groups = load_groups_for_profile(profile["id"])
    if my_groups:
        labels = [group["name"] for group in my_groups]
        group = my_groups[labels.index(st.selectbox("View group", labels))]
        st.dataframe(load_group_progress(group["id"]), use_container_width=True, hide_index=True)
    shared = load_shared_profiles_for_viewer(profile["id"])
    if shared:
        labels = [f"{person['name']} (@{person['username']})" for person in shared]
        owner = shared[labels.index(st.selectbox("Progress shared with you", labels))]
        dashboard(
            load_settings(owner["id"]),
            load_assignments(owner["id"]),
            load_completed_chapters(owner["id"]),
            load_history(owner["id"]),
            f"{owner['name']}'s Progress",
        )


def ai_guidance(settings, completed):
    st.subheader("AI And Hosting Guidance")
    if settings:
        total = len(get_plan_chapters(settings))
        st.info(f"Rule-based coach: You are {len(completed) / total * 100:.1f}% complete. Keep your rhythm simple and consistent.")
    st.write("A used laptop can run small local AI models with Ollama, especially with 16 GB RAM, but it may be slow.")
    st.write("For a proper website, use Supabase for auth/database and add AI later through OpenAI, Gemini, or a local Ollama server.")
    st.write("For very cheap phone use, deploy to Streamlit Community Cloud and add the link to your phone home screen.")


def history_screen(assignments, history):
    st.subheader("Reading History")
    history_df = history_to_dataframe(history)
    plan_df = assignments_to_dataframe(assignments)
    if history_df.empty:
        st.info("No reading history has been saved yet.")
    else:
        st.dataframe(history_df, use_container_width=True, hide_index=True)
    st.download_button("Export full reading plan to CSV", plan_df.to_csv(index=False), "reading_plan.csv", "text/csv", disabled=plan_df.empty)


def settings_screen(profile):
    st.subheader("Settings")
    st.write(f"Signed in as **{profile['name']}** (`@{profile['username']}`)")
    st.write(f"Total Bible chapters: **{TOTAL_BIBLE_CHAPTERS}**")
    backup_tools(profile)
    if st.button("Log out"):
        st.session_state.clear()
        st.rerun()


def main():
    profile = load_profile(st.session_state.get("profile_id"))
    if not profile:
        landing_page()
        return
    settings = load_settings(profile["id"])
    assignments = load_assignments(profile["id"])
    completed = load_completed_chapters(profile["id"])
    history = load_history(profile["id"])
    if "screen" not in st.session_state:
        st.session_state["screen"] = "Start" if settings else "Setup Plan"
    st.title("Bible Reading Planner")
    st.caption("A simple plan that adjusts as you read.")
    st.write(f"Signed in as **{profile['name']}** (`@{profile['username']}`)")
    options = ["Start", "Setup Plan", "Today's Reading", "Bible Reader", "Update Progress", "Dashboard", "Groups", "Leaderboard", "AI Guidance", "Reading History", "Settings"]
    selected = st.sidebar.radio("Navigation", options, index=options.index(st.session_state["screen"]) if st.session_state["screen"] in options else 0)
    st.session_state["screen"] = selected
    if selected == "Start":
        start_screen(settings, assignments, completed, history, profile)
    elif selected == "Setup Plan":
        setup_plan(settings, profile)
    elif selected == "Today's Reading":
        today_screen(settings, assignments, completed, profile["id"])
    elif selected == "Bible Reader":
        bible_reader(settings, assignments, profile)
    elif selected == "Update Progress":
        progress_screen(settings, assignments, completed, profile)
    elif selected == "Dashboard":
        dashboard(settings, assignments, completed, history)
        backup_tools(profile)
    elif selected == "Groups":
        groups(profile)
    elif selected == "Leaderboard":
        leaderboard(profile)
    elif selected == "AI Guidance":
        ai_guidance(settings, completed)
    elif selected == "Reading History":
        history_screen(assignments, history)
    elif selected == "Settings":
        settings_screen(profile)


if __name__ == "__main__":
    main()
