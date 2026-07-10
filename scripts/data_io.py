"""데이터 IO + 위생 필터 공용 모듈 (measure_accuracy / validate_saju_signal 공용)

- fetch_from_admin_api / fetch_from_db: submissions + feedbacks 로드
- DUMMY_CUTOFF 이전 행은 더미/테스트 데이터 (2026-03-14 확정, Leo 확인)
- hour_is_known: 시주 신뢰 가능 여부 판정
- dedupe_persons: 멀티 퀴즈 반복 유저 → person 단위 집계 (공식 n은 person 수)
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DIMENSIONS

# 이 날짜 이전 행은 전부 테스트 더미 (학습/검증 제외) — pre-registered
DUMMY_CUTOFF = "2026-03-14"


def fetch_from_admin_api(base_url="https://flavor.arkedia.work", token=None,
                         since=DUMMY_CUTOFF):
    """서버 admin export API에서 submissions + feedbacks fetch"""
    import urllib.request

    if not token:
        token = os.environ.get("FLAVOR_ADMIN_TOKEN", "")
    if not token:
        raise RuntimeError("FLAVOR_ADMIN_TOKEN 환경변수 또는 --token 필요")

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "leoflavor-harness/1.0",
    }

    def _get(url):
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())

    q = f"&since={since}" if since else ""
    sub_data = _get(f"{base_url}/api/admin/export?table=submissions&limit=100000{q}")
    fb_data = _get(f"{base_url}/api/admin/export?table=feedbacks&limit=100000{q}")

    submissions = []
    for r in sub_data.get("data", []):
        submissions.append({
            "id": r["id"],
            "name": r.get("name", ""),
            "birth_date": r.get("birth_date", ""),
            "birth_time": r.get("birth_time", "12"),
            "gender": r.get("gender", ""),
            "elements": _loads(r.get("elements_json")),
            "raw_answers": _loads(r.get("raw_survey_json")),
            "survey": _loads(r.get("survey_json")),
            "profile": _loads(r.get("profile_json")),
            "results": _loads(r.get("results_json")),
            "saju": _loads(r.get("saju_json")),
            "profile_version": r.get("profile_version") or "",
            "created_at": r.get("created_at", ""),
        })

    return submissions, fb_data.get("data", [])


def fetch_from_db(db_path, since=DUMMY_CUTOFF):
    """로컬 SQLite DB에서 직접 로드"""
    import sqlite3

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    cols = ("id, name, birth_date, birth_time, gender, elements_json, "
            "raw_survey_json, survey_json, profile_json, results_json, "
            "profile_version, created_at")
    has_saju = _column_exists(c, "submissions", "saju_json")
    if has_saju:
        cols += ", saju_json"
    where = " WHERE created_at >= ?" if since else ""
    c.execute(f"SELECT {cols} FROM submissions{where} ORDER BY created_at ASC",
              (since,) if since else ())

    submissions = []
    for row in c.fetchall():
        submissions.append({
            "id": row[0], "name": row[1] or "",
            "birth_date": row[2], "birth_time": row[3], "gender": row[4],
            "elements": _loads(row[5]), "raw_answers": _loads(row[6]),
            "survey": _loads(row[7]), "profile": _loads(row[8]),
            "results": _loads(row[9]),
            "profile_version": row[10] or "", "created_at": row[11],
            "saju": _loads(row[12]) if has_saju else None,
        })

    c.execute(f"SELECT submission_id, domain, thumb, created_at FROM feedbacks{where} "
              "ORDER BY created_at ASC", (since,) if since else ())
    feedbacks = [{"submission_id": r[0], "domain": r[1], "thumb": r[2], "created_at": r[3]}
                 for r in c.fetchall()]
    conn.close()
    return submissions, feedbacks


def hour_is_known(sub: dict) -> bool:
    """시주 신뢰 가능 판정.

    - saju_json이 있으면 서버 계산 결과를 그대로 사용 (정본)
    - 없으면(구버전 행) 재구성: 사주 트랙 퀴즈 + birth_time이 숫자 + 더미 이전 아님
      비사주 트랙의 "12"는 하드코딩 기본값이라 신뢰 불가
    """
    saju = sub.get("saju")
    if saju and "hour_known" in saju:
        return bool(saju["hour_known"])

    if (sub.get("created_at") or "") < DUMMY_CUTOFF:
        return False  # 더미 시기: 전부 기본값 12
    bt = sub.get("birth_time")
    if bt in (None, "", "unknown"):
        return False
    is_saju_quiz = "_saju" in (sub.get("profile_version") or "")
    try:
        int(bt)
    except (ValueError, TypeError):
        return False
    return is_saju_quiz


def dedupe_persons(submissions: list) -> list:
    """(name, birth_date, gender) 키로 person 단위 집계.

    - survey = 소속 제출들의 9차원 평균 (노이즈 감소)
    - hour_known = 신뢰 가능한 제출이 하나라도 있고 birth_time이 서로 모순되지 않을 때
    - birth_time = 신뢰 가능한 제출 중 첫 값
    """
    persons = {}
    for sub in submissions:
        survey = sub.get("survey") or {}
        if not survey or not any(survey.values()):
            continue
        key = ((sub.get("name") or "").strip().lower(),
               sub.get("birth_date") or "", sub.get("gender") or "")
        p = persons.setdefault(key, {
            "key": key, "birth_date": sub.get("birth_date"),
            "surveys": [], "hours": [], "submissions": [],
        })
        p["surveys"].append(survey)
        p["submissions"].append(sub)
        if hour_is_known(sub):
            try:
                p["hours"].append(int(sub["birth_time"]))
            except (ValueError, TypeError):
                pass

    out = []
    for p in persons.values():
        n = len(p["surveys"])
        survey = {d: sum(s.get(d, 0.5) for s in p["surveys"]) / n for d in DIMENSIONS}
        hours = set(p["hours"])
        hour_known = len(hours) == 1  # 모순(여러 시간 주장) 시 미상으로 강등
        out.append({
            "key": p["key"],
            "birth_date": p["birth_date"],
            "birth_time": str(p["hours"][0]) if hour_known else None,
            "survey": survey,
            "n_submissions": n,
            "hour_known": hour_known,
            "hour_conflict": len(hours) > 1,
            "first_created_at": min(s["created_at"] for s in p["submissions"]),
            "submission_ids": [s["id"] for s in p["submissions"]],
        })
    out.sort(key=lambda p: p["first_created_at"])
    return out


def dataset_hash(submissions: list) -> str:
    """감사용 데이터셋 지문: sorted (id, created_at) sha256 앞 8자리"""
    keys = sorted((s["id"], s.get("created_at", "")) for s in submissions)
    return hashlib.sha256(json.dumps(keys).encode()).hexdigest()[:8]


def _loads(v):
    if not v:
        return {}
    try:
        return json.loads(v)
    except (ValueError, TypeError):
        return {}


def _column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())
