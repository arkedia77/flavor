"""DB 초기화 및 연결"""

import sqlite3
from config import DB_PATH


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    # ★WAL 전환 (2026-09-21, LEO 승인 · admin 찬성). 기본 `delete`는 쓰기가 DB 전체를
    # 잠가 «읽기»까지 busy_timeout 뒤 실패한다 — 동시 제출이 몰리는 유통 개시 때 터지는 축.
    # WAL은 읽기가 쓰기와 겹쳐도 통과한다. journal_mode는 **DB 파일에 영속**하므로 여기서 1회.
    # ⛔백업과의 상호작용(admin 지적): 백업이 파일 `cp`였다면 WAL 전환 순간부터 `-wal`·`-shm`을
    #   빠뜨려 «조용히» 깨졌을 것이다(에러 없이 「과거 시점」 DB가 나온다). 현 백업은 sqlite3
    #   `Connection.backup()`이라 안전 — 2026-09-21 admin이 백업본을 «열어서» 교차검증 통과.
    # ⚠★**이 마지막 문장은 이 repo 밖 자산에 달려 있다** — 백업 스크립트는
    #   `leoserver:~/.local/bin/flavor_db_backup.sh`(admin 소관)다. 그쪽이 `cp` 방식으로 바뀌면
    #   ***이 주석은 코드 한 줄 안 바뀌고도 거짓이 된다.*** ⇒ 인용 전 현물 확인.
    #   (같은 형태가 반대 방향으로 실제 발생했다: 이 WAL 전환이 admin 스크립트의 주석
    #    「journal_mode=delete라 더 위험」을 낡게 만들었고 admin이 자진 적발·교체했다.
    #    ⛔WAL에서 `cp`는 delete 때보다 **더** 위험하다 — 거꾸로 읽히던 문면이었다.)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass  # 전환 실패해도 기존 모드로 계속 — 기동을 막지 않는다
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
        ("saju_json", "TEXT"),
        ("user_id", "TEXT"),          # 카카오 로그인 시 서버 user 연결 (익명이면 NULL)
        ("source_json", "TEXT"),      # 유입 출처 utm 5종+랜딩경로 (직접 유입·기존 행은 NULL)
    ]:
        try:
            c.execute(f"ALTER TABLE submissions ADD COLUMN {col} {col_type}")
        except Exception:
            pass
    # 카카오 로그인 유저 (익명 흐름은 이 테이블을 안 씀 — 로그인 시에만 upsert)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            kakao_id TEXT UNIQUE,
            nickname TEXT,
            email TEXT,
            created_at TEXT
        )
    """)
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
