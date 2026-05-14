"""SQLite storage helpers for the Bible Reading Planner."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path("bible_planner.db")


def get_connection():
    """Open a connection to the local SQLite database."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    """Create database tables if this is the first app run."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS assignments (
                date TEXT PRIMARY KEY,
                chapters TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS completed_chapters (
                chapter TEXT PRIMARY KEY,
                completed_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                date TEXT PRIMARY KEY,
                assigned_chapters TEXT NOT NULL,
                completed_chapters TEXT NOT NULL,
                chapters_read INTEGER NOT NULL,
                notes TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )


def save_settings(settings):
    """Save the current plan settings as JSON."""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO settings (id, data)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET data = excluded.data
            """,
            (json.dumps(settings),),
        )


def load_settings():
    """Load saved plan settings, or return None when no plan exists."""
    with get_connection() as connection:
        row = connection.execute("SELECT data FROM settings WHERE id = 1").fetchone()
    return json.loads(row["data"]) if row else None


def save_assignments(assignments, replace_from_date=None):
    """Save daily assignments.

    If replace_from_date is provided, assignments on or after that date are
    deleted first so the recalculated future plan replaces the old one.
    """
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as connection:
        if replace_from_date:
            connection.execute(
                "DELETE FROM assignments WHERE date >= ?",
                (replace_from_date,),
            )
        for day, chapters in assignments.items():
            connection.execute(
                """
                INSERT INTO assignments (date, chapters, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(date) DO UPDATE
                SET chapters = excluded.chapters,
                    updated_at = excluded.updated_at
                """,
                (day, json.dumps(chapters), now),
            )


def load_assignments():
    """Load all saved assignments as a dictionary."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT date, chapters FROM assignments ORDER BY date"
        ).fetchall()
    return {row["date"]: json.loads(row["chapters"]) for row in rows}


def load_assignment(day):
    """Load one day's assigned chapters."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT chapters FROM assignments WHERE date = ?",
            (day,),
        ).fetchone()
    return json.loads(row["chapters"]) if row else []


def add_completed_chapters(chapters):
    """Mark chapters as completed, ignoring chapters already saved."""
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as connection:
        for chapter in chapters:
            connection.execute(
                """
                INSERT OR IGNORE INTO completed_chapters (chapter, completed_at)
                VALUES (?, ?)
                """,
                (chapter, now),
            )


def load_completed_chapters():
    """Return the list of completed chapters."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT chapter FROM completed_chapters ORDER BY completed_at, chapter"
        ).fetchall()
    return [row["chapter"] for row in rows]


def save_history(day, assigned_chapters, completed_chapters, chapters_read, notes):
    """Save or update the reading history record for one day."""
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO history (
                date, assigned_chapters, completed_chapters,
                chapters_read, notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE
            SET assigned_chapters = excluded.assigned_chapters,
                completed_chapters = excluded.completed_chapters,
                chapters_read = excluded.chapters_read,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                day,
                json.dumps(assigned_chapters),
                json.dumps(completed_chapters),
                int(chapters_read),
                notes,
                now,
            ),
        )


def load_history():
    """Load reading history rows as dictionaries."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM history ORDER BY date DESC"
        ).fetchall()

    history = []
    for row in rows:
        history.append(
            {
                "date": row["date"],
                "assigned_chapters": json.loads(row["assigned_chapters"]),
                "completed_chapters": json.loads(row["completed_chapters"]),
                "chapters_read": row["chapters_read"],
                "notes": row["notes"] or "",
                "updated_at": row["updated_at"],
            }
        )
    return history


def reset_all_data():
    """Delete all saved planner data."""
    with get_connection() as connection:
        connection.execute("DELETE FROM settings")
        connection.execute("DELETE FROM assignments")
        connection.execute("DELETE FROM completed_chapters")
        connection.execute("DELETE FROM history")
