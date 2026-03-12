"""DB 초기화 및 연결"""

import sqlite3
from config import DB_PATH


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY,
            name TEXT,
            birth_date TEXT,
            birth_time TEXT,
            gender TEXT,
            elements_json TEXT,
            raw_survey_json TEXT,
            survey_json TEXT,
            profile_json TEXT,
            results_json TEXT,
            profile_version TEXT,
            created_at TEXT
        )
    """)
    for col, col_type in [
        ("raw_survey_json", "TEXT"),
        ("profile_version", "TEXT"),
    ]:
        try:
            c.execute(f"ALTER TABLE submissions ADD COLUMN {col} {col_type}")
        except Exception:
            pass
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id TEXT,
            domain TEXT,
            thumb INTEGER,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS milestones (
            milestone INTEGER PRIMARY KEY,
            reached_at TEXT
        )
    """)
    conn.commit()
    conn.close()
