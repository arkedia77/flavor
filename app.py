"""
SAJU 취향 분석 서비스 - Flask 백엔드
flavor.arkedia.work
"""

import os
import json
import uuid
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", "/tmp/saju_submissions.db")

# ──────────────────────────────────────────────
# DB 초기화
# ──────────────────────────────────────────────

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
            profile_json TEXT,
            results_json TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ──────────────────────────────────────────────
# 사주 계산 (간단 버전)
# ──────────────────────────────────────────────

STEMS = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
BRANCHES = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

STEM_ELEMENT = {
    "갑": "목", "을": "목",
    "병": "화", "정": "화",
    "무": "토", "기": "토",
    "경": "금", "신": "금",
    "임": "수", "계": "수"
}

BRANCH_ELEMENT = {
    "자": "수", "축": "토", "인": "목", "묘": "목",
    "진": "토", "사": "화", "오": "화", "미": "토",
    "신": "금", "유": "금", "술": "토", "해": "수"
}


def calc_saju(year: int, month: int, day: int, hour: int = 0):
    """사주 4주 계산 → 오행 카운트 반환"""
    # 천간 계산
    y_stem = STEMS[(year - 4) % 10]
    m_stem = STEMS[((year - 4) % 5 * 2 + month + 1) % 10]
    d_num = (year * 365 + year // 4 - year // 100 + year // 400
             + [0,31,59,90,120,151,181,212,243,273,304,334][month-1] + day)
    d_stem = STEMS[(d_num + 9) % 10]
    h_stem = STEMS[(d_num * 2 + hour // 2) % 10]

    # 지지 계산
    y_branch = BRANCHES[(year - 4) % 12]
    m_branch = BRANCHES[(month + 1) % 12]
    d_branch = BRANCHES[(d_num + 11) % 12]
    h_branch = BRANCHES[(hour // 2 + 23) % 12]

    # 오행 카운트
    elements = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
    for stem in [y_stem, m_stem, d_stem, h_stem]:
        elements[STEM_ELEMENT[stem]] += 1
    for branch in [y_branch, m_branch, d_branch, h_branch]:
        elements[BRANCH_ELEMENT[branch]] += 1

    return {
        "pillars": {
            "year": f"{y_stem}{y_branch}",
            "month": f"{m_stem}{m_branch}",
            "day": f"{d_stem}{d_branch}",
            "hour": f"{h_stem}{h_branch}"
        },
        "elements": elements
    }


# ──────────────────────────────────────────────
# 10차원 프로필 → 취향 벡터 변환
# ──────────────────────────────────────────────

def elements_to_profile(elements: dict, gender: str, survey: dict) -> dict:
    """오행 + 설문 → 취향 프로필"""
    total = sum(elements.values()) or 1

    # 오행 비율
    wood  = elements.get("목", 0) / total
    fire  = elements.get("화", 0) / total
    earth = elements.get("토", 0) / total
    metal = elements.get("금", 0) / total
    water = elements.get("수", 0) / total

    # 설문 보정값 (0~1 범위)
    social      = survey.get("social", 0.5)        # 외향성
    aesthetic   = survey.get("aesthetic", 0.5)     # 심미성
    adventurous = survey.get("adventurous", 0.5)   # 모험성
    comfort     = survey.get("comfort", 0.5)       # 편안함
    budget      = survey.get("budget", 0.5)        # 예산 여유

    return {
        "wood":        round(wood, 3),
        "fire":        round(fire, 3),
        "earth":       round(earth, 3),
        "metal":       round(metal, 3),
        "water":       round(water, 3),
        "social":      round((wood + fire) * 0.5 + social * 0.3, 3),
        "aesthetic":   round((metal + water) * 0.5 + aesthetic * 0.3, 3),
        "adventurous": round((fire + wood) * 0.4 + adventurous * 0.4, 3),
        "comfort":     round((earth + metal) * 0.4 + comfort * 0.4, 3),
        "budget":      round(budget, 3),
    }


# ──────────────────────────────────────────────
# 도메인별 추천 (규칙 기반)
# ──────────────────────────────────────────────

def recommend_coffee(profile: dict) -> dict:
    water = profile["water"]
    fire  = profile["fire"]
    if water > 0.25:
        return {"item": "콜드브루 블랙", "reason": "수(水) 기운이 강해 깔끔하고 깊은 맛 선호"}
    elif fire > 0.25:
        return {"item": "에스프레소 마키아토", "reason": "화(火) 기운으로 강렬하고 진한 맛 선호"}
    else:
        return {"item": "오트밀크 라떼", "reason": "균형 잡힌 오행으로 부드럽고 안정적인 맛 선호"}


def recommend_perfume(profile: dict) -> dict:
    wood  = profile["wood"]
    metal = profile["metal"]
    if wood > 0.25:
        return {"item": "그린 플로럴 계열", "reason": "목(木) 기운으로 자연스럽고 생동감 있는 향 선호"}
    elif metal > 0.25:
        return {"item": "머스크·우디 계열", "reason": "금(金) 기운으로 세련되고 미니멀한 향 선호"}
    else:
        return {"item": "시트러스 아쿠아틱", "reason": "균형 잡힌 오행으로 청량하고 밝은 향 선호"}


def recommend_music(profile: dict) -> dict:
    social = profile["social"]
    calm   = 1 - social
    if social > 0.55:
        return {"item": "업템포 팝·일렉트로닉", "reason": "외향적 에너지가 높아 활기차고 리듬감 있는 음악 선호"}
    elif calm > 0.55:
        return {"item": "어쿠스틱·로파이 힙합", "reason": "내향적 에너지로 조용하고 집중력 있는 음악 선호"}
    else:
        return {"item": "인디 팝·재즈", "reason": "균형 잡힌 성향으로 다양한 장르를 즐김"}


def recommend_restaurant(profile: dict) -> dict:
    adventurous = profile["adventurous"]
    comfort     = profile["comfort"]
    if adventurous > 0.5:
        return {"item": "에스닉 퓨전 레스토랑", "reason": "모험적 성향으로 새로운 맛과 문화 경험 선호"}
    elif comfort > 0.5:
        return {"item": "한식 가정식 맛집", "reason": "안정 추구 성향으로 익숙하고 편안한 음식 선호"}
    else:
        return {"item": "이탈리안 비스트로", "reason": "균형 잡힌 취향으로 클래식하지만 새로운 경험"}


def recommend_exercise(profile: dict) -> dict:
    fire  = profile["fire"]
    earth = profile["earth"]
    if fire > 0.25:
        return {"item": "HIIT·크로스핏", "reason": "화(火) 기운으로 강렬하고 도전적인 운동 선호"}
    elif earth > 0.25:
        return {"item": "요가·필라테스", "reason": "토(土) 기운으로 안정적이고 마음챙김 운동 선호"}
    else:
        return {"item": "수영·사이클링", "reason": "균형 잡힌 오행으로 지속적이고 리듬감 있는 운동 선호"}


def recommend_travel(profile: dict) -> dict:
    adventurous = profile["adventurous"]
    aesthetic   = profile["aesthetic"]
    if adventurous > 0.5:
        return {"item": "동남아 배낭여행·트레킹", "reason": "모험 지수 높아 미지의 자연 탐험 선호"}
    elif aesthetic > 0.5:
        return {"item": "유럽 예술·문화 도시 투어", "reason": "심미성 높아 아름다운 건축과 예술 선호"}
    else:
        return {"item": "일본 소도시 온천 여행", "reason": "균형 잡힌 취향으로 편안하고 감성적인 여행 선호"}


def recommend_fashion(profile: dict) -> dict:
    metal = profile["metal"]
    wood  = profile["wood"]
    if metal > 0.25:
        return {"item": "미니멀 모노톤 스타일", "reason": "금(金) 기운으로 깔끔하고 정제된 패션 선호"}
    elif wood > 0.25:
        return {"item": "내추럴 보헤미안 스타일", "reason": "목(木) 기운으로 자연스럽고 자유로운 패션 선호"}
    else:
        return {"item": "캐주얼 스트리트 스타일", "reason": "균형 잡힌 취향으로 편하면서 감각적인 스타일"}


def recommend_interior(profile: dict) -> dict:
    earth = profile["earth"]
    water = profile["water"]
    if earth > 0.25:
        return {"item": "웜톤 내추럴 인테리어", "reason": "토(土) 기운으로 따뜻하고 안정적인 공간 선호"}
    elif water > 0.25:
        return {"item": "스칸디나비안 미니멀", "reason": "수(水) 기운으로 깔끔하고 여백 있는 공간 선호"}
    else:
        return {"item": "모던 빈티지 믹스", "reason": "균형 잡힌 취향으로 개성 있고 아늑한 공간 선호"}


def run_all_domains(profile: dict) -> dict:
    return {
        "커피": recommend_coffee(profile),
        "향수": recommend_perfume(profile),
        "음악": recommend_music(profile),
        "식당": recommend_restaurant(profile),
        "운동": recommend_exercise(profile),
        "여행": recommend_travel(profile),
        "패션": recommend_fashion(profile),
        "인테리어": recommend_interior(profile),
    }


# ──────────────────────────────────────────────
# API 라우트
# ──────────────────────────────────────────────

@app.route("/api/submit", methods=["POST"])
def submit():
    try:
        data = request.get_json(force=True)

        name       = data.get("name", "익명")
        birth_date = data.get("birth_date", "")  # "YYYY-MM-DD"
        birth_time = data.get("birth_time", "0") # 시 (0~23)
        gender     = data.get("gender", "unknown")

        # 설문 응답 파싱 (0~1 범위로 정규화)
        survey = {
            "social":      float(data.get("social", 0.5)),
            "aesthetic":   float(data.get("aesthetic", 0.5)),
            "adventurous": float(data.get("adventurous", 0.5)),
            "comfort":     float(data.get("comfort", 0.5)),
            "budget":      float(data.get("budget", 0.5)),
        }

        # 생년월일 파싱
        parts = birth_date.split("-")
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        hour = int(birth_time)

        # 사주 계산
        saju = calc_saju(year, month, day, hour)
        profile = elements_to_profile(saju["elements"], gender, survey)
        results = run_all_domains(profile)

        # DB 저장
        result_id = str(uuid.uuid4())[:8]
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO submissions (id, name, birth_date, birth_time, gender,
                                     profile_json, results_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result_id, name, birth_date, birth_time, gender,
            json.dumps(profile, ensure_ascii=False),
            json.dumps(results, ensure_ascii=False),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "ok",
            "id": result_id,
            "name": name,
            "saju": saju,
            "profile": profile,
            "results": results,
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/result/<result_id>")
def result_page(result_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM submissions WHERE id=?", (result_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return "결과를 찾을 수 없습니다.", 404

    _, name, birth_date, birth_time, gender, profile_json, results_json, created_at = row
    profile = json.loads(profile_json)
    results = json.loads(results_json)

    return jsonify({
        "id": result_id,
        "name": name,
        "birth_date": birth_date,
        "profile": profile,
        "results": results,
        "created_at": created_at
    })


@app.route("/api/results")
def api_results():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, birth_date, gender, created_at FROM submissions ORDER BY created_at DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        "id": r[0], "name": r[1], "birth_date": r[2],
        "gender": r[3], "created_at": r[4]
    } for r in rows])


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "flavor-saju"})


@app.route("/")
def index():
    return """<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>SAJU 취향 분석</title></head>
<body style="font-family:sans-serif;text-align:center;padding:50px">
  <h1>🌟 SAJU 취향 분석</h1>
  <p>사주로 알아보는 나만의 취향</p>
  <a href="/survey">설문 시작하기</a>
</body>
</html>"""


if __name__ == "__main__":
    app.run(debug=os.environ.get("DEBUG", "false").lower() == "true",
            host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
