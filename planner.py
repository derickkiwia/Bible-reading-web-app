"""Planning and recalculation logic for the Bible Reading Planner."""

from datetime import date, datetime, timedelta

from bible_data import get_all_chapters


WEEKDAY_NAMES = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def parse_date(value):
    """Convert a date string from storage into a Python date."""
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_reading_dates(start_date, end_date, selected_weekdays):
    """Return every date between start and end that is an allowed reading day."""
    start_date = parse_date(start_date)
    end_date = parse_date(end_date)
    selected_weekdays = set(selected_weekdays)

    if start_date > end_date:
        raise ValueError("Start date must be before or equal to end date.")
    if not selected_weekdays:
        raise ValueError("Choose at least one reading day.")

    reading_dates = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() in selected_weekdays:
            reading_dates.append(current_date)
        current_date += timedelta(days=1)

    return reading_dates


def distribute_chapters(chapters, reading_dates):
    """Evenly assign whole chapters across the available reading dates."""
    if chapters and not reading_dates:
        raise ValueError("There are no reading days available for the remaining chapters.")

    plan = {day.isoformat(): [] for day in reading_dates}
    if not chapters:
        return plan

    base_count = len(chapters) // len(reading_dates)
    extra_days = len(chapters) % len(reading_dates)
    chapter_index = 0

    for day_index, reading_day in enumerate(reading_dates):
        chapters_for_day = base_count + (1 if day_index < extra_days else 0)
        day_chapters = chapters[chapter_index : chapter_index + chapters_for_day]
        plan[reading_day.isoformat()] = day_chapters
        chapter_index += chapters_for_day

    return plan


def generate_initial_plan(settings):
    """Create a new reading plan from the selected start chapter to the end."""
    plan_chapters = get_all_chapters(settings["start_book"], settings["start_chapter"])
    reading_dates = get_reading_dates(
        settings["start_date"],
        settings["end_date"],
        settings["selected_weekdays"],
    )
    return distribute_chapters(plan_chapters, reading_dates), plan_chapters


def get_unread_chapters(plan_chapters, completed_chapters):
    """Return chapters that have not yet been completed, preserving Bible order."""
    completed = set(completed_chapters)
    return [chapter for chapter in plan_chapters if chapter not in completed]


def recalculate_future_plan(settings, plan_chapters, completed_chapters, from_date):
    """Rebuild assignments from from_date onward using only unread chapters.

    Past history is not edited here. The caller should save past/today records
    first, then replace future assignments with this recalculated plan.
    """
    unread_chapters = get_unread_chapters(plan_chapters, completed_chapters)
    future_dates = get_reading_dates(
        from_date,
        settings["end_date"],
        settings["selected_weekdays"],
    )
    return distribute_chapters(unread_chapters, future_dates)


def choose_completed_chapters(assigned_chapters, plan_chapters, completed_chapters, chapters_read):
    """Choose which chapters to mark complete after a progress update.

    We count assigned unread chapters first. If the user read more than assigned,
    we continue forward through the next unread chapters in Bible order.
    """
    completed = set(completed_chapters)
    assigned_unread = [chapter for chapter in assigned_chapters if chapter not in completed]
    all_unread = [chapter for chapter in plan_chapters if chapter not in completed]

    selected = []
    for chapter in assigned_unread:
        if len(selected) < chapters_read:
            selected.append(chapter)

    for chapter in all_unread:
        if len(selected) >= chapters_read:
            break
        if chapter not in selected:
            selected.append(chapter)

    return selected


def progress_status(expected_completed, actual_completed):
    """Return whether the reader is ahead, on track, or behind."""
    if actual_completed > expected_completed:
        return "ahead"
    if actual_completed < expected_completed:
        return "behind"
    return "on track"


def encouragement_message(status):
    """Return a friendly rule-based encouragement message."""
    if status == "ahead":
        return "Great progress. Your future daily load has reduced."
    if status == "behind":
        return "You are slightly behind, but the plan has been adjusted."
    return "You are on track. Keep going."


def generate_ai_reflection_prompt(reading_chapters, progress_status):
    """Placeholder for a future OpenAI or Gemini integration.

    Later, this function could call an AI API and return a generated reflection
    or devotional prompt. For now it returns a simple text prompt only.
    """
    chapters = ", ".join(reading_chapters) if reading_chapters else "today's reading"
    return f"Reflect on {chapters}. Progress status: {progress_status}."


def calculate_streaks(history_rows):
    """Calculate current streak, longest streak, and missed days from history."""
    if not history_rows:
        return 0, 0, 0

    by_day = {
        parse_date(row["date"]): int(row.get("chapters_read", 0))
        for row in history_rows
    }
    active_days = sorted(day for day, count in by_day.items() if count > 0)
    missed_days = sum(1 for count in by_day.values() if count == 0)

    if not active_days:
        return 0, 0, missed_days

    longest = 1
    current_run = 1
    for previous, current in zip(active_days, active_days[1:]):
        if current == previous + timedelta(days=1):
            current_run += 1
        else:
            longest = max(longest, current_run)
            current_run = 1
    longest = max(longest, current_run)

    today = date.today()
    current_streak = 0
    check_day = today
    if check_day not in by_day:
        check_day = today - timedelta(days=1)

    while by_day.get(check_day, 0) > 0:
        current_streak += 1
        check_day -= timedelta(days=1)

    return current_streak, longest, missed_days


def estimate_completion_date(total_completed, history_rows, remaining_chapters):
    """Estimate completion date using the reader's actual average pace."""
    if remaining_chapters <= 0:
        return date.today()

    active_rows = [row for row in history_rows if int(row.get("chapters_read", 0)) > 0]
    if not active_rows:
        return None

    total_read = sum(int(row.get("chapters_read", 0)) for row in active_rows)
    average_per_active_day = total_read / len(active_rows)
    if average_per_active_day <= 0:
        return None

    days_needed = int((remaining_chapters + average_per_active_day - 1) // average_per_active_day)
    return date.today() + timedelta(days=days_needed)
