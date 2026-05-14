"""Bible book and chapter data used by the planner.

The app uses the standard Protestant canon order from Genesis to Revelation.
Each chapter is represented as a simple string such as "Genesis 1".
"""

BIBLE_BOOKS = [
    ("Genesis", 50),
    ("Exodus", 40),
    ("Leviticus", 27),
    ("Numbers", 36),
    ("Deuteronomy", 34),
    ("Joshua", 24),
    ("Judges", 21),
    ("Ruth", 4),
    ("1 Samuel", 31),
    ("2 Samuel", 24),
    ("1 Kings", 22),
    ("2 Kings", 25),
    ("1 Chronicles", 29),
    ("2 Chronicles", 36),
    ("Ezra", 10),
    ("Nehemiah", 13),
    ("Esther", 10),
    ("Job", 42),
    ("Psalms", 150),
    ("Proverbs", 31),
    ("Ecclesiastes", 12),
    ("Song of Solomon", 8),
    ("Isaiah", 66),
    ("Jeremiah", 52),
    ("Lamentations", 5),
    ("Ezekiel", 48),
    ("Daniel", 12),
    ("Hosea", 14),
    ("Joel", 3),
    ("Amos", 9),
    ("Obadiah", 1),
    ("Jonah", 4),
    ("Micah", 7),
    ("Nahum", 3),
    ("Habakkuk", 3),
    ("Zephaniah", 3),
    ("Haggai", 2),
    ("Zechariah", 14),
    ("Malachi", 4),
    ("Matthew", 28),
    ("Mark", 16),
    ("Luke", 24),
    ("John", 21),
    ("Acts", 28),
    ("Romans", 16),
    ("1 Corinthians", 16),
    ("2 Corinthians", 13),
    ("Galatians", 6),
    ("Ephesians", 6),
    ("Philippians", 4),
    ("Colossians", 4),
    ("1 Thessalonians", 5),
    ("2 Thessalonians", 3),
    ("1 Timothy", 6),
    ("2 Timothy", 4),
    ("Titus", 3),
    ("Philemon", 1),
    ("Hebrews", 13),
    ("James", 5),
    ("1 Peter", 5),
    ("2 Peter", 3),
    ("1 John", 5),
    ("2 John", 1),
    ("3 John", 1),
    ("Jude", 1),
    ("Revelation", 22),
]


def get_book_names():
    """Return the list of Bible book names in canonical order."""
    return [book for book, _ in BIBLE_BOOKS]


def get_chapter_count(book_name):
    """Return how many chapters are in one Bible book."""
    for book, chapter_count in BIBLE_BOOKS:
        if book == book_name:
            return chapter_count
    raise ValueError(f"Unknown Bible book: {book_name}")


def get_all_chapters(start_book="Genesis", start_chapter=1):
    """Return ordered chapter labels from the selected starting point onward."""
    chapters = []
    found_start_book = False

    for book, chapter_count in BIBLE_BOOKS:
        if book == start_book:
            found_start_book = True

        if not found_start_book:
            continue

        first_chapter = start_chapter if book == start_book else 1
        if first_chapter < 1 or first_chapter > chapter_count:
            raise ValueError(f"{book} has chapters 1 through {chapter_count}.")

        for chapter_number in range(first_chapter, chapter_count + 1):
            chapters.append(f"{book} {chapter_number}")

    if not found_start_book:
        raise ValueError(f"Unknown Bible book: {start_book}")

    return chapters


TOTAL_BIBLE_CHAPTERS = len(get_all_chapters())
