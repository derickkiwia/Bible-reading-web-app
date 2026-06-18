"""Simple tests for the Bible Reading Planner.

Run with:
    python test_planner.py
"""

from datetime import date

from bible_data import TOTAL_BIBLE_CHAPTERS, get_all_chapters
from planner import generate_initial_plan, recalculate_future_plan


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


def test_mixed_plan_covers_old_and_new_testaments_once():
    settings = {
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "selected_weekdays": [0, 1, 2, 3, 4, 5, 6],
        "plan_style": "Mixed Old and New Testament",
        "old_testament_percent": 70,
        "old_start_book": "Genesis",
        "old_start_chapter": 1,
        "new_start_book": "Matthew",
        "new_start_chapter": 1,
    }
    assignments, plan_chapters = generate_initial_plan(settings)
    assigned = flatten(assignments)

    assert len(plan_chapters) == 1189
    assert len(assigned) == 1189
    assert len(set(assigned)) == 1189


def test_whole_bible_can_start_mid_bible_and_wrap():
    settings = {
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "selected_weekdays": [0, 1, 2, 3, 4, 5, 6],
        "start_book": "John",
        "start_chapter": 3,
        "plan_scope": "Read the whole Bible starting from my selected point",
    }
    assignments, plan_chapters = generate_initial_plan(settings)
    assigned = flatten(assignments)

    assert len(plan_chapters) == 1189
    assert len(set(plan_chapters)) == 1189
    assert plan_chapters[0] == "John 3"
    assert plan_chapters[-1] == "John 2"
    assert assigned == plan_chapters


def test_mixed_whole_bible_can_start_mid_testaments_and_wrap():
    settings = {
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "selected_weekdays": [0, 1, 2, 3, 4, 5, 6],
        "plan_style": "Mixed Old and New Testament",
        "old_testament_percent": 70,
        "old_start_book": "Psalms",
        "old_start_chapter": 23,
        "new_start_book": "John",
        "new_start_chapter": 3,
        "plan_scope": "Read the whole Bible starting from my selected points",
    }
    assignments, plan_chapters = generate_initial_plan(settings)

    assert len(plan_chapters) == 1189
    assert len(set(plan_chapters)) == 1189
    assert plan_chapters[0] == "Psalms 23"
    assert "Genesis 1" in plan_chapters
    assert "Matthew 1" in plan_chapters
    assert len(flatten(assignments)) == 1189


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
    future = recalculate_future_plan(settings, plan_chapters, [], date(2026, 1, 2))
    assigned = flatten(future)

    assert "Genesis 1" in assigned
    assert len(assigned) == 1189


def test_future_assignments_update_after_progress():
    settings = {
        "start_date": "2026-01-01",
        "end_date": "2026-01-10",
        "selected_weekdays": [0, 1, 2, 3, 4, 5, 6],
        "start_book": "Genesis",
        "start_chapter": 1,
    }
    plan_chapters = get_all_chapters("Genesis", 1)
    completed = ["Genesis 1", "Genesis 2"]
    future = recalculate_future_plan(settings, plan_chapters, completed, date(2026, 1, 2))
    assigned = flatten(future)

    assert assigned[0] == "Genesis 3"
    assert "Genesis 1" not in assigned
    assert "Genesis 2" not in assigned


if __name__ == "__main__":
    test_total_chapters()
    test_plan_covers_all_chapters_once()
    test_mixed_plan_covers_old_and_new_testaments_once()
    test_whole_bible_can_start_mid_bible_and_wrap()
    test_mixed_whole_bible_can_start_mid_testaments_and_wrap()
    test_completed_chapters_are_not_reassigned()
    test_missed_chapters_are_redistributed()
    test_future_assignments_update_after_progress()
    print("All planner tests passed.")
