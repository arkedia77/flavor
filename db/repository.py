"""DB CRUD 함수"""

import json
from db.connection import get_db_connection


def save_submission(result_id, name, birth_date, birth_time, gender,
                    elements, raw_answers, survey, profile, results, profile_version, created_at,
                    saju=None, user_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO submissions (id, name, birth_date, birth_time, gender,
                                 elements_json, raw_survey_json, survey_json,
                                 profile_json, results_json, profile_version, created_at,
                                 saju_json, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result_id, name, birth_date, birth_time, gender,
        json.dumps(elements, ensure_ascii=False),
        json.dumps(raw_answers, ensure_ascii=False),
        json.dumps(survey, ensure_ascii=False),
        json.dumps(profile, ensure_ascii=False),
        json.dumps(results, ensure_ascii=False),
        profile_version,
        created_at,
        json.dumps(saju, ensure_ascii=False) if saju else None,
        user_id
    ))
    conn.commit()
    conn.close()


def upsert_user_by_kakao(kakao_id, nickname=None, email=None):
    """카카오 로그인 유저 upsert → user_id(TEXT) 반환.

    kakao_id로 기존 유저 조회, 없으면 신규 생성(uuid). nickname/email은 로그인마다 갱신.
    person 식별의 안정 키 = kakao_id (기기·localStorage 무관하게 동일 유저).
    """
    import uuid
    from datetime import datetime
    kakao_id = str(kakao_id)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE kakao_id=?", (kakao_id,))
    row = c.fetchone()
    if row:
        user_id = row[0]
        c.execute("UPDATE users SET nickname=?, email=? WHERE id=?",
                  (nickname, email, user_id))
    else:
        user_id = str(uuid.uuid4())
        c.execute("INSERT INTO users (id, kakao_id, nickname, email, created_at) VALUES (?,?,?,?,?)",
                  (user_id, kakao_id, nickname, email, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return user_id


def get_user(user_id):
    """user_id로 유저 조회 → dict 또는 None."""
    if not user_id:
        return None
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, kakao_id, nickname, email, created_at FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "kakao_id": row[1], "nickname": row[2],
            "email": row[3], "created_at": row[4]}


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


def get_feedback_data():
    """전체 피드백 + 연결된 submission 프로필 (추천 학습용).

    results_json을 조인해 각 피드백에 '그때 보여준 아이템'을 붙인다 —
    학습 재랭킹(recommend.learned_rerank)이 아이템 단위 신호를 쓰기 위함.
    (feedbacks 테이블은 도메인 단위라 아이템은 결과 스냅샷에서 재구성)
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT s.id, s.survey_json, s.profile_json, s.results_json, f.domain, f.thumb
        FROM feedbacks f
        JOIN submissions s ON f.submission_id = s.id
        ORDER BY f.created_at ASC
    """)
    rows = c.fetchall()
    conn.close()

    users = {}
    for sid, survey_json, profile_json, results_json, domain, thumb in rows:
        if sid not in users:
            results = json.loads(results_json) if results_json else {}
            users[sid] = {
                "id": sid,
                "profile": json.loads(profile_json) if profile_json else {},
                "results": results,
                "feedbacks": [],
            }
        shown = users[sid]["results"].get(domain) or {}
        users[sid]["feedbacks"].append({
            "domain": domain, "thumb": thumb, "item": shown.get("item"),
        })

    return list(users.values())


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
