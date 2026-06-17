"""Bible book and chapter data used by the planner."""

BIBLE_BOOKS = [
    ("Genesis", 50), ("Exodus", 40), ("Leviticus", 27), ("Numbers", 36),
    ("Deuteronomy", 34), ("Joshua", 24), ("Judges", 21), ("Ruth", 4),
    ("1 Samuel", 31), ("2 Samuel", 24), ("1 Kings", 22), ("2 Kings", 25),
    ("1 Chronicles", 29), ("2 Chronicles", 36), ("Ezra", 10), ("Nehemiah", 13),
    ("Esther", 10), ("Job", 42), ("Psalms", 150), ("Proverbs", 31),
    ("Ecclesiastes", 12), ("Song of Solomon", 8), ("Isaiah", 66),
    ("Jeremiah", 52), ("Lamentations", 5), ("Ezekiel", 48), ("Daniel", 12),
    ("Hosea", 14), ("Joel", 3), ("Amos", 9), ("Obadiah", 1), ("Jonah", 4),
    ("Micah", 7), ("Nahum", 3), ("Habakkuk", 3), ("Zephaniah", 3),
    ("Haggai", 2), ("Zechariah", 14), ("Malachi", 4), ("Matthew", 28),
    ("Mark", 16), ("Luke", 24), ("John", 21), ("Acts", 28), ("Romans", 16),
    ("1 Corinthians", 16), ("2 Corinthians", 13), ("Galatians", 6),
    ("Ephesians", 6), ("Philippians", 4), ("Colossians", 4),
    ("1 Thessalonians", 5), ("2 Thessalonians", 3), ("1 Timothy", 6),
    ("2 Timothy", 4), ("Titus", 3), ("Philemon", 1), ("Hebrews", 13),
    ("James", 5), ("1 Peter", 5), ("2 Peter", 3), ("1 John", 5),
    ("2 John", 1), ("3 John", 1), ("Jude", 1), ("Revelation", 22),
]

OLD_TESTAMENT_BOOKS = [book for book, _ in BIBLE_BOOKS[:39]]
NEW_TESTAMENT_BOOKS = [book for book, _ in BIBLE_BOOKS[39:]]


def get_book_names():
    return [book for book, _ in BIBLE_BOOKS]


def get_chapter_count(book_name):
    for book, count in BIBLE_BOOKS:
        if book == book_name:
            return count
    raise ValueError(f"Unknown Bible book: {book_name}")


def get_book_chapters(book_name):
    return [f"{book_name} {chapter}" for chapter in range(1, get_chapter_count(book_name) + 1)]


def get_chapters_for_books(book_names, start_book=None, start_chapter=1):
    chapters = []
    found = start_book is None
    for book, count in BIBLE_BOOKS:
        if book not in book_names:
            continue
        if book == start_book:
            found = True
        if not found:
            continue
        first = start_chapter if book == start_book else 1
        chapters.extend(f"{book} {chapter}" for chapter in range(first, count + 1))
    return chapters


def get_all_chapters(start_book="Genesis", start_chapter=1):
    chapters = []
    found = False
    for book, count in BIBLE_BOOKS:
        if book == start_book:
            found = True
        if not found:
            continue
        first = start_chapter if book == start_book else 1
        chapters.extend(f"{book} {chapter}" for chapter in range(first, count + 1))
    return chapters


TOTAL_BIBLE_CHAPTERS = len(get_all_chapters())
OLD_TESTAMENT_CHAPTERS = [chapter for chapter in get_all_chapters() if chapter.rsplit(" ", 1)[0] in OLD_TESTAMENT_BOOKS]
NEW_TESTAMENT_CHAPTERS = [chapter for chapter in get_all_chapters() if chapter.rsplit(" ", 1)[0] in NEW_TESTAMENT_BOOKS]
