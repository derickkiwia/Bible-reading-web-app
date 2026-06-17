"""Planning and recalculation logic."""

from datetime import date, datetime, timedelta
from bible_data import (
    NEW_TESTAMENT_BOOKS,
    NEW_TESTAMENT_CHAPTERS,
    OLD_TESTAMENT_BOOKS,
    OLD_TESTAMENT_CHAPTERS,
    get_all_chapters,
    get_chapters_for_books,
)

WEEKDAY_NAMES = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}


def parse_date(value):
    return value if isinstance(value, date) else datetime.strptime(value, "%Y-%m-%d").date()


def get_reading_dates(start_date, end_date, selected_weekdays):
    start_date = parse_date(start_date)
    end_date = parse_date(end_date)
    if start_date > end_date:
        raise ValueError("Start date must be before or equal to end date.")
    if not selected_weekdays:
        raise ValueError("Choose at least one reading day.")
    days = []
    current = start_date
    while current <= end_date:
        if current.weekday() in set(selected_weekdays):
            days.append(current)
        current += timedelta(days=1)
    return days


def distribute_chapters(chapters, reading_dates):
    if chapters and not reading_dates:
        raise ValueError("There are no reading days available for the remaining chapters.")
    plan = {day.isoformat(): [] for day in reading_dates}
    if not chapters:
        return plan
    base = len(chapters) // len(reading_dates)
    extra = len(chapters) % len(reading_dates)
    index = 0
    for day_index, day in enumerate(reading_dates):
        count = base + (1 if day_index < extra else 0)
        plan[day.isoformat()] = chapters[index:index + count]
        index += count
    return plan


def distribute_mixed_chapters(chapters, reading_dates, old_testament_percent):
    old_set = set(OLD_TESTAMENT_CHAPTERS)
    new_set = set(NEW_TESTAMENT_CHAPTERS)
    old = [chapter for chapter in chapters if chapter in old_set]
    new = [chapter for chapter in chapters if chapter in new_set]
    counts = [len(items) for items in distribute_chapters(chapters, reading_dates).values()]
    plan = {day.isoformat(): [] for day in reading_dates}
    ratio = old_testament_percent / 100
    for day, total in zip(reading_dates, counts):
        old_count = round(total * ratio)
        if total > 1 and old and new:
            old_count = min(max(old_count, 1), total - 1)
        today_old = old[:old_count]
        old = old[old_count:]
        today_new = new[: total - len(today_old)]
        new = new[total - len(today_old):]
        while len(today_old) + len(today_new) < total and old:
            today_old.append(old.pop(0))
        while len(today_old) + len(today_new) < total and new:
            today_new.append(new.pop(0))
        plan[day.isoformat()] = today_old + today_new
    return plan


def generate_initial_plan(settings):
    if settings.get("plan_style") == "Mixed Old and New Testament":
        chapters = get_chapters_for_books(
            OLD_TESTAMENT_BOOKS,
            settings.get("old_start_book", "Genesis"),
            int(settings.get("old_start_chapter", 1)),
        ) + get_chapters_for_books(
            NEW_TESTAMENT_BOOKS,
            settings.get("new_start_book", "Matthew"),
            int(settings.get("new_start_chapter", 1)),
        )
    else:
        chapters = get_all_chapters(settings["start_book"], settings["start_chapter"])
    dates = get_reading_dates(settings["start_date"], settings["end_date"], settings["selected_weekdays"])
    if settings.get("plan_style") == "Mixed Old and New Testament":
        return distribute_mixed_chapters(chapters, dates, int(settings.get("old_testament_percent", 70))), chapters
    return distribute_chapters(chapters, dates), chapters


def recalculate_future_plan(settings, plan_chapters, completed_chapters, from_date):
    unread = [chapter for chapter in plan_chapters if chapter not in set(completed_chapters)]
    dates = get_reading_dates(from_date, settings["end_date"], settings["selected_weekdays"])
    if settings.get("plan_style") == "Mixed Old and New Testament":
        return distribute_mixed_chapters(unread, dates, int(settings.get("old_testament_percent", 70)))
    return distribute_chapters(unread, dates)


def progress_status(expected_completed, actual_completed):
    if actual_completed > expected_completed:
        return "ahead"
    if actual_completed < expected_completed:
        return "behind"
    return "on track"


def encouragement_message(status):
    if status == "ahead":
        return "Great progress. Your future daily load has reduced."
    if status == "behind":
        return "You are slightly behind, but the plan has been adjusted."
    return "You are on track. Keep going."


def generate_ai_reflection_prompt(reading_chapters, progress_status):
    chapters = ", ".join(reading_chapters) if reading_chapters else "today's reading"
    return f"Reflect on {chapters}. Progress status: {progress_status}."


def calculate_streaks(history_rows):
    return 0, 0, sum(1 for row in history_rows if int(row.get("chapters_read", 0)) == 0)


def estimate_completion_date(total_completed, history_rows, remaining_chapters):
    return None
