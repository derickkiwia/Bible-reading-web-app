"""SQLite storage helpers for the Bible Reading Planner."""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("bible_planner.db")


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def hash_pin(pin):
    return hashlib.sha256(pin.encode("utf-8")).hexdigest() if pin else ""


def normalize_username(username):
    return username.strip().lower()


def init_db():
    with get_connection() as con:
        con.execute("CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, username TEXT UNIQUE, pin_hash TEXT, created_at TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS settings (profile_id INTEGER PRIMARY KEY, data TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS assignments (profile_id INTEGER NOT NULL, date TEXT NOT NULL, chapters TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (profile_id, date))")
        con.execute("CREATE TABLE IF NOT EXISTS completed_chapters (profile_id INTEGER NOT NULL, chapter TEXT NOT NULL, completed_at TEXT NOT NULL, PRIMARY KEY (profile_id, chapter))")
        con.execute("CREATE TABLE IF NOT EXISTS history (profile_id INTEGER NOT NULL, date TEXT NOT NULL, assigned_chapters TEXT NOT NULL, completed_chapters TEXT NOT NULL, chapters_read INTEGER NOT NULL, notes TEXT, updated_at TEXT NOT NULL, PRIMARY KEY (profile_id, date))")
        con.execute("CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS group_members (group_id INTEGER NOT NULL, profile_id INTEGER NOT NULL, joined_at TEXT NOT NULL, PRIMARY KEY (group_id, profile_id))")
        con.execute("CREATE TABLE IF NOT EXISTS progress_access (owner_profile_id INTEGER NOT NULL, viewer_profile_id INTEGER NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY (owner_profile_id, viewer_profile_id))")


def create_profile(name, username=None, pin=None):
    now = datetime.now().isoformat(timespec="seconds")
    username = normalize_username(username or name.replace(" ", ""))
    with get_connection() as con:
        con.execute("INSERT INTO profiles (name, username, pin_hash, created_at) VALUES (?, ?, ?, ?)", (name.strip(), username, hash_pin(pin), now))
        return con.execute("SELECT id FROM profiles WHERE username = ?", (username,)).fetchone()["id"]


def authenticate_profile(username, pin):
    with get_connection() as con:
        row = con.execute("SELECT * FROM profiles WHERE username = ?", (normalize_username(username),)).fetchone()
    if not row:
        return None
    profile = dict(row)
    if profile.get("pin_hash") and profile["pin_hash"] != hash_pin(pin):
        return None
    return profile


def load_profile(profile_id):
    if not profile_id:
        return None
    with get_connection() as con:
        row = con.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    return dict(row) if row else None


def load_profile_by_username(username):
    with get_connection() as con:
        row = con.execute("SELECT * FROM profiles WHERE username = ?", (normalize_username(username),)).fetchone()
    return dict(row) if row else None


def save_settings(settings, profile_id):
    with get_connection() as con:
        con.execute("INSERT INTO settings (profile_id, data) VALUES (?, ?) ON CONFLICT(profile_id) DO UPDATE SET data = excluded.data", (profile_id, json.dumps(settings)))


def load_settings(profile_id):
    with get_connection() as con:
        row = con.execute("SELECT data FROM settings WHERE profile_id = ?", (profile_id,)).fetchone()
    return json.loads(row["data"]) if row else None


def save_assignments(assignments, profile_id, replace_from_date=None):
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as con:
        if replace_from_date:
            con.execute("DELETE FROM assignments WHERE profile_id = ? AND date >= ?", (profile_id, replace_from_date))
        for day, chapters in assignments.items():
            con.execute("INSERT INTO assignments (profile_id, date, chapters, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT(profile_id, date) DO UPDATE SET chapters = excluded.chapters, updated_at = excluded.updated_at", (profile_id, day, json.dumps(chapters), now))


def load_assignments(profile_id):
    with get_connection() as con:
        rows = con.execute("SELECT date, chapters FROM assignments WHERE profile_id = ? ORDER BY date", (profile_id,)).fetchall()
    return {row["date"]: json.loads(row["chapters"]) for row in rows}


def add_completed_chapters(chapters, profile_id):
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as con:
        for chapter in chapters:
            con.execute("INSERT OR IGNORE INTO completed_chapters (profile_id, chapter, completed_at) VALUES (?, ?, ?)", (profile_id, chapter, now))


def load_completed_chapters(profile_id):
    with get_connection() as con:
        rows = con.execute("SELECT chapter FROM completed_chapters WHERE profile_id = ? ORDER BY completed_at, chapter", (profile_id,)).fetchall()
    return [row["chapter"] for row in rows]


def save_history(day, assigned_chapters, completed_chapters, chapters_read, notes, profile_id):
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as con:
        con.execute("INSERT INTO history (profile_id, date, assigned_chapters, completed_chapters, chapters_read, notes, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(profile_id, date) DO UPDATE SET assigned_chapters = excluded.assigned_chapters, completed_chapters = excluded.completed_chapters, chapters_read = excluded.chapters_read, notes = excluded.notes, updated_at = excluded.updated_at", (profile_id, day, json.dumps(assigned_chapters), json.dumps(completed_chapters), int(chapters_read), notes, now))


def load_history(profile_id):
    with get_connection() as con:
        rows = con.execute("SELECT * FROM history WHERE profile_id = ? ORDER BY date DESC", (profile_id,)).fetchall()
    return [{"date": r["date"], "assigned_chapters": json.loads(r["assigned_chapters"]), "completed_chapters": json.loads(r["completed_chapters"]), "chapters_read": r["chapters_read"], "notes": r["notes"] or "", "updated_at": r["updated_at"]} for r in rows]


def export_profile_data(profile_id):
    """Export one user's full local data as a JSON-serializable dictionary."""
    with get_connection() as con:
        profile = con.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        settings = con.execute("SELECT data FROM settings WHERE profile_id = ?", (profile_id,)).fetchone()
        assignments = con.execute("SELECT date, chapters, updated_at FROM assignments WHERE profile_id = ? ORDER BY date", (profile_id,)).fetchall()
        completed = con.execute("SELECT chapter, completed_at FROM completed_chapters WHERE profile_id = ? ORDER BY completed_at", (profile_id,)).fetchall()
        history = con.execute("SELECT * FROM history WHERE profile_id = ? ORDER BY date", (profile_id,)).fetchall()
    return {
        "version": 1,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "profile": dict(profile) if profile else None,
        "settings": json.loads(settings["data"]) if settings else None,
        "assignments": [
            {"date": row["date"], "chapters": json.loads(row["chapters"]), "updated_at": row["updated_at"]}
            for row in assignments
        ],
        "completed_chapters": [dict(row) for row in completed],
        "history": [
            {
                "date": row["date"],
                "assigned_chapters": json.loads(row["assigned_chapters"]),
                "completed_chapters": json.loads(row["completed_chapters"]),
                "chapters_read": row["chapters_read"],
                "notes": row["notes"] or "",
                "updated_at": row["updated_at"],
            }
            for row in history
        ],
    }


def import_profile_data(profile_id, backup):
    """Restore one user's plan/progress from an exported backup."""
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as con:
        con.execute("DELETE FROM settings WHERE profile_id = ?", (profile_id,))
        con.execute("DELETE FROM assignments WHERE profile_id = ?", (profile_id,))
        con.execute("DELETE FROM completed_chapters WHERE profile_id = ?", (profile_id,))
        con.execute("DELETE FROM history WHERE profile_id = ?", (profile_id,))

        if backup.get("settings"):
            con.execute(
                "INSERT INTO settings (profile_id, data) VALUES (?, ?)",
                (profile_id, json.dumps(backup["settings"])),
            )

        for row in backup.get("assignments", []):
            con.execute(
                "INSERT INTO assignments (profile_id, date, chapters, updated_at) VALUES (?, ?, ?, ?)",
                (profile_id, row["date"], json.dumps(row.get("chapters", [])), row.get("updated_at", now)),
            )

        for row in backup.get("completed_chapters", []):
            con.execute(
                "INSERT OR IGNORE INTO completed_chapters (profile_id, chapter, completed_at) VALUES (?, ?, ?)",
                (profile_id, row["chapter"], row.get("completed_at", now)),
            )

        for row in backup.get("history", []):
            con.execute(
                """
                INSERT INTO history (
                    profile_id, date, assigned_chapters, completed_chapters,
                    chapters_read, notes, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    row["date"],
                    json.dumps(row.get("assigned_chapters", [])),
                    json.dumps(row.get("completed_chapters", [])),
                    int(row.get("chapters_read", 0)),
                    row.get("notes", ""),
                    row.get("updated_at", now),
                ),
            )


def invite_progress_viewer(owner_profile_id, viewer_username):
    viewer = load_profile_by_username(viewer_username)
    if not viewer:
        return False, "No user exists with that username yet."
    if viewer["id"] == owner_profile_id:
        return False, "You already own your progress."
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as con:
        con.execute("INSERT OR IGNORE INTO progress_access (owner_profile_id, viewer_profile_id, created_at) VALUES (?, ?, ?)", (owner_profile_id, viewer["id"], now))
    return True, f"{viewer['name']} can now view your progress."


def load_allowed_viewers(owner_profile_id):
    with get_connection() as con:
        rows = con.execute("SELECT profiles.id, profiles.name, profiles.username FROM profiles JOIN progress_access ON progress_access.viewer_profile_id = profiles.id WHERE progress_access.owner_profile_id = ? ORDER BY profiles.name", (owner_profile_id,)).fetchall()
    return [dict(row) for row in rows]


def load_shared_profiles_for_viewer(viewer_profile_id):
    with get_connection() as con:
        rows = con.execute("SELECT profiles.id, profiles.name, profiles.username FROM profiles JOIN progress_access ON progress_access.owner_profile_id = profiles.id WHERE progress_access.viewer_profile_id = ? ORDER BY profiles.name", (viewer_profile_id,)).fetchall()
    return [dict(row) for row in rows]


def create_or_join_group(profile_id, group_name):
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as con:
        con.execute("INSERT OR IGNORE INTO groups (name, created_at) VALUES (?, ?)", (group_name.strip(), now))
        group = con.execute("SELECT id FROM groups WHERE name = ?", (group_name.strip(),)).fetchone()
        con.execute("INSERT OR IGNORE INTO group_members (group_id, profile_id, joined_at) VALUES (?, ?, ?)", (group["id"], profile_id, now))
        return group["id"]


def load_groups_for_profile(profile_id):
    with get_connection() as con:
        rows = con.execute("SELECT groups.id, groups.name FROM groups JOIN group_members ON group_members.group_id = groups.id WHERE group_members.profile_id = ? ORDER BY groups.name", (profile_id,)).fetchall()
    return [dict(row) for row in rows]


def load_group_progress(group_id):
    with get_connection() as con:
        rows = con.execute("SELECT profiles.id, profiles.name, profiles.username, settings.data FROM profiles JOIN group_members ON group_members.profile_id = profiles.id LEFT JOIN settings ON settings.profile_id = profiles.id WHERE group_members.group_id = ? ORDER BY profiles.name", (group_id,)).fetchall()
        output = []
        for row in rows:
            completed = con.execute("SELECT COUNT(*) AS count FROM completed_chapters WHERE profile_id = ?", (row["id"],)).fetchone()["count"]
            total = len(json.loads(row["data"]).get("plan_chapters", [])) if row["data"] else 0
            output.append({"name": row["name"], "username": row["username"], "completed_chapters": completed, "total_chapters": total, "percent_complete": round((completed / total * 100) if total else 0, 1)})
    return output


def reset_all_data(profile_id):
    with get_connection() as con:
        con.execute("DELETE FROM settings WHERE profile_id = ?", (profile_id,))
        con.execute("DELETE FROM assignments WHERE profile_id = ?", (profile_id,))
        con.execute("DELETE FROM completed_chapters WHERE profile_id = ?", (profile_id,))
        con.execute("DELETE FROM history WHERE profile_id = ?", (profile_id,))
