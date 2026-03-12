"""DB CRUD 함수"""

import json
from db.connection import get_db_connection


def save_submission(result_id, name, birth_date, birth_time, gender,
                    elements, raw_answers, survey, profile, results, profile_version, created_at):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO submissions (id, name, birth_date, birth_time, gender,
                                 elements_json, raw_survey_json, survey_json,
                                 profile_json, results_json, profile_version, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result_id, name, birth_date, birth_time, gender,
        json.dumps(elements, ensure_ascii=False),
        json.dumps(raw_answers, ensure_ascii=False),
        json.dumps(survey, ensure_ascii=False),
        json.dumps(profile, ensure_ascii=False),
        json.dumps(results, ensure_ascii=False),
        profile_version,
        created_at
    ))
    conn.commit()
    conn.close()


def get_submission(result_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, birth_date, birth_time, gender, profile_json, results_json FROM submissions WHERE id=?",
              (result_id,))
    row = c.fetchone()
    conn.close()
    return row


def get_submission_count():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM submissions")
    total = c.fetchone()[0]
    conn.close()
    return total


def check_and_record_milestone(milestone):
    """마일스톤 도달 체크. 새로 도달하면 True 반환"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM milestones WHERE milestone=?", (milestone,))
    if c.fetchone():
        conn.close()
        return False
    from datetime import datetime
    c.execute("INSERT INTO milestones VALUES (?, ?)",
              (milestone, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return True


def save_feedback(submission_id, domain, thumb, created_at):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO feedbacks (submission_id, domain, thumb, created_at) VALUES (?,?,?,?)",
        (submission_id, domain, thumb, created_at)
    )
    conn.commit()
    conn.close()


def get_recent_submissions(limit=100):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, birth_date, gender, created_at FROM submissions ORDER BY created_at DESC LIMIT ?",
              (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_calibration_data():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, birth_date, birth_time, gender,
               elements_json, raw_survey_json, survey_json, profile_version, created_at
        FROM submissions ORDER BY created_at ASC
    """)
    rows = c.fetchall()
    c.execute("SELECT COUNT(*) FROM submissions")
    total = c.fetchone()[0]
    conn.close()
    return rows, total


def save_ux_vote(preferred, comment, done_set_json, source, created_at):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS ux_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preferred TEXT,
            comment TEXT,
            done_set TEXT,
            source TEXT,
            created_at TEXT
        )
    """)
    c.execute(
        "INSERT INTO ux_votes (preferred, comment, done_set, source, created_at) VALUES (?, ?, ?, ?, ?)",
        (preferred, comment, done_set_json, source, created_at)
    )
    conn.commit()
    conn.close()


def get_ux_vote_tally():
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT preferred, COUNT(*) FROM ux_votes GROUP BY preferred ORDER BY COUNT(*) DESC")
        tally = {row[0]: row[1] for row in c.fetchall()}
    except Exception:
        tally = {}
    conn.close()
    return tally


def get_ux_vote_comments(limit=20):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT preferred, comment, created_at FROM ux_votes WHERE comment != '' ORDER BY created_at DESC LIMIT ?",
                  (limit,))
        comments = [{"preferred": r[0], "comment": r[1], "at": r[2]} for r in c.fetchall()]
    except Exception:
        comments = []
    conn.close()
    return comments
