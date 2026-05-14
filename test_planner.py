"""Simple tests for the Bible Reading Planner.

Run with:
    python test_planner.py
"""

from datetime import date

from bible_data import TOTAL_BIBLE_CHAPTERS, get_all_chapters
from planner import (
    choose_completed_chapters,
    generate_initial_plan,
    get_unread_chapters,
    recalculate_future_plan,
)


def flatten(assignments):
    """Turn assignment dictionary values into one chapter list."""
    chapters = []
    for day in sorted(assignments):
        chapters.extend(assignments[day])
    return chapters


def test_total_chapters():
    assert TOTAL_BIBLE_CHAPTERS == 1189


def test_plan_covers_all_chapters_once():
    settings = {
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "selected_weekdays": [0, 1, 2, 3, 4, 5, 6],
        "start_book": "Genesis",
        "start_chapter": 1,
    }
    assignments, plan_chapters = generate_initial_plan(settings)
    assigned = flatten(assignments)

    assert len(plan_chapters) == 1189
    assert len(assigned) == 1189
    assert len(set(assigned)) == 1189
    assert assigned == plan_chapters


def test_completed_chapters_are_not_reassigned():
    settings = {
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
        "selected_weekdays": [0, 1, 2, 3, 4, 5, 6],
        "start_book": "Genesis",
        "start_chapter": 1,
    }
    plan_chapters = get_all_chapters("Genesis", 1)
    completed = ["Genesis 1", "Genesis 2", "Genesis 3"]
    future = recalculate_future_plan(settings, plan_chapters, completed, date(2026, 1, 2))
    assigned = flatten(future)

    assert "Genesis 1" not in assigned
    assert "Genesis 2" not in assigned
    assert "Genesis 3" not in assigned


def test_missed_chapters_are_redistributed():
    settings = {
        "start_date": "2026-01-01",
        "end_date": "2026-01-10",
        "selected_weekdays": [0, 1, 2, 3, 4, 5, 6],
        "start_book": "Genesis",
        "start_chapter": 1,
    }
    plan_chapters = get_all_chapters("Genesis", 1)
    completed = []
    future = recalculate_future_plan(settings, plan_chapters, completed, date(2026, 1, 2))
    assigned = flatten(future)

    assert "Genesis 1" in assigned
    assert len(assigned) == 1189


def test_extra_reading_moves_plan_forward():
    plan_chapters = get_all_chapters("Genesis", 1)
    assigned_today = ["Genesis 1", "Genesis 2", "Genesis 3", "Genesis 4"]
    completed = choose_completed_chapters(assigned_today, plan_chapters, [], 6)

    assert completed == [
        "Genesis 1",
        "Genesis 2",
        "Genesis 3",
        "Genesis 4",
        "Genesis 5",
        "Genesis 6",
    ]


def test_unread_chapters_after_partial_progress():
    plan_chapters = get_all_chapters("Genesis", 1)
    assigned_today = ["Genesis 1", "Genesis 2", "Genesis 3", "Genesis 4"]
    completed = choose_completed_chapters(assigned_today, plan_chapters, [], 2)
    unread = get_unread_chapters(plan_chapters, completed)

    assert completed == ["Genesis 1", "Genesis 2"]
    assert unread[0] == "Genesis 3"


if __name__ == "__main__":
    test_total_chapters()
    test_plan_covers_all_chapters_once()
    test_completed_chapters_are_not_reassigned()
    test_missed_chapters_are_redistributed()
    test_extra_reading_moves_plan_forward()
    test_unread_chapters_after_partial_progress()
    print("All planner tests passed.")
