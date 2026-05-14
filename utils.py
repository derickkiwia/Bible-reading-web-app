"""Small helper functions used by the Streamlit app."""

from datetime import date, timedelta

import pandas as pd

from planner import get_reading_dates, progress_status


def format_chapter_list(chapters):
    """Format chapters for display in the app."""
    if not chapters:
        return "No chapters assigned."
    return "\n".join(f"- {chapter}" for chapter in chapters)


def assignments_to_dataframe(assignments):
    """Convert assignment data to a table for display or CSV export."""
    rows = []
    for day, chapters in sorted(assignments.items()):
        rows.append(
            {
                "date": day,
                "chapters": ", ".join(chapters),
                "chapter_count": len(chapters),
            }
        )
    return pd.DataFrame(rows)


def history_to_dataframe(history_rows):
    """Convert history data to a table for display or CSV export."""
    rows = []
    for row in history_rows:
        rows.append(
            {
                "date": row["date"],
                "assigned_chapters": ", ".join(row["assigned_chapters"]),
                "completed_chapters": ", ".join(row["completed_chapters"]),
                "chapters_read": row["chapters_read"],
                "notes": row["notes"],
                "updated_at": row["updated_at"],
            }
        )
    return pd.DataFrame(rows)


def expected_completed_by_today(assignments):
    """Count chapters assigned before today to estimate plan status."""
    today = date.today().isoformat()
    return sum(len(chapters) for day, chapters in assignments.items() if day < today)


def build_dashboard(settings, plan_chapters, completed_chapters, history_rows):
    """Calculate dashboard metrics in one easy-to-use dictionary."""
    total_chapters = len(plan_chapters)
    completed_count = len(completed_chapters)
    remaining_count = max(total_chapters - completed_count, 0)
    percent_complete = (completed_count / total_chapters * 100) if total_chapters else 100

    tomorrow = date.today() + timedelta(days=1)
    try:
        remaining_days = get_reading_dates(
            tomorrow,
            settings["end_date"],
            settings["selected_weekdays"],
        )
    except ValueError:
        remaining_days = []

    daily_average_needed = (
        remaining_count / len(remaining_days) if remaining_days and remaining_count else 0
    )
    expected_completed = expected_completed_by_today(settings.get("original_assignments", {}))
    status = progress_status(expected_completed, completed_count)

    return {
        "total_chapters": total_chapters,
        "completed_count": completed_count,
        "remaining_count": remaining_count,
        "percent_complete": percent_complete,
        "daily_average_needed": daily_average_needed,
        "status": status,
        "days_remaining_to_end": max((date.fromisoformat(settings["end_date"]) - date.today()).days, 0),
    }
