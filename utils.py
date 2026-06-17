"""Display helpers."""

import pandas as pd


def format_chapter_list(chapters):
    return "No chapters assigned." if not chapters else "\n".join(f"- {chapter}" for chapter in chapters)


def assignments_to_dataframe(assignments):
    return pd.DataFrame([{"date": day, "chapters": ", ".join(chapters), "chapter_count": len(chapters)} for day, chapters in sorted(assignments.items())])


def history_to_dataframe(history_rows):
    return pd.DataFrame([
        {
            "date": row["date"],
            "assigned_chapters": ", ".join(row["assigned_chapters"]),
            "completed_chapters": ", ".join(row["completed_chapters"]),
            "chapters_read": row["chapters_read"],
            "notes": row["notes"],
            "updated_at": row["updated_at"],
        }
        for row in history_rows
    ])
