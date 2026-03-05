"""
SAJU 취향 분석 서비스 - Flask 백엔드
flavor.arkedia.work
"""

import os
import json
import uuid
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect

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
            elements_json TEXT,   -- 오행 원본 (캘리브레이션용)
            survey_json TEXT,     -- 설문 응답 원본 (캘리브레이션용)
            profile_json TEXT,    -- blend된 최종 프로필
            results_json TEXT,
            created_at TEXT
        )
    """)
    # 알림 테이블: 임계점 도달 기록
    c.execute("""
        CREATE TABLE IF NOT EXISTS milestones (
            milestone INTEGER PRIMARY KEY,
            reached_at TEXT
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
    """오행(내부 보정용) + 설문 → 취향 프로필"""
    total = sum(elements.values()) or 1

    # 오행 비율 (내부 미세 보정에만 사용, 외부 노출 안 함)
    wood  = elements.get("목", 0) / total
    fire  = elements.get("화", 0) / total
    earth = elements.get("토", 0) / total
    metal = elements.get("금", 0) / total
    water = elements.get("수", 0) / total

    def blend(saju_val, survey_val, w=0.25):
        """사주 보정값 25%, 설문값 75% 블렌딩"""
        return round(min(1.0, max(0.0, saju_val * w + survey_val * (1 - w))), 3)

    return {
        "social":      blend((wood + fire) * 0.5, survey.get("social", 0.5)),
        "aesthetic":   blend((metal + water) * 0.5, survey.get("aesthetic", 0.5)),
        "adventurous": blend((fire + wood) * 0.4 + 0.1, survey.get("adventurous", 0.5)),
        "comfort":     blend((earth + metal) * 0.4 + 0.1, survey.get("comfort", 0.5)),
        "budget":      round(survey.get("budget", 0.5), 3),
        "maximalist":  round(survey.get("maximalist", 0.5), 3),
        "energetic":   blend((fire + wood) * 0.4, survey.get("energetic", 0.5)),
        "urban":       round(survey.get("urban", 0.5), 3),
        "bitter":      blend(water * 0.6, survey.get("bitter", 0.5)),
    }


# ──────────────────────────────────────────────
# 도메인별 추천 (규칙 기반)
# ──────────────────────────────────────────────

def recommend_coffee(profile: dict) -> dict:
    bitter = profile.get("bitter", 0.5)
    budget = profile.get("budget", 0.5)
    if bitter > 0.65:
        if budget > 0.6:
            return {"item": "스페셜티 싱글오리진 핸드드립", "reason": "진하고 복잡한 맛을 즐기는 미식가형"}
        return {"item": "에스프레소·아이스 아메리카노", "reason": "강하고 깔끔한 커피를 선호하는 타입"}
    elif bitter < 0.35:
        return {"item": "달달한 라떼·플랫화이트", "reason": "부드럽고 달콤한 풍미를 즐기는 타입"}
    else:
        if budget > 0.6:
            return {"item": "오트밀크 라떼·콜드브루", "reason": "트렌디하고 감각적인 카페 경험을 선호"}
        return {"item": "아이스 라떼·아메리카노", "reason": "무난하지만 믿을 수 있는 클래식한 취향"}


def recommend_perfume(profile: dict) -> dict:
    aesthetic  = profile.get("aesthetic", 0.5)
    maximalist = profile.get("maximalist", 0.5)
    adventurous = profile.get("adventurous", 0.5)
    if maximalist < 0.35 and aesthetic > 0.5:
        return {"item": "머스크·클린 미니멀 향", "reason": "정제되고 세련된 감각, 은은한 존재감을 선호"}
    elif maximalist > 0.65:
        return {"item": "오리엔탈·우디 레이어드 향", "reason": "풍부하고 개성 강한 향으로 존재감을 표현"}
    elif adventurous > 0.6:
        return {"item": "니치 퍼퓸·아방가르드 향", "reason": "남들과 다른 독특한 향기에 끌리는 탐험가 취향"}
    else:
        return {"item": "시트러스·그린 플로럴", "reason": "청량하고 자연스러운 향으로 편안한 인상"}


def recommend_music(profile: dict) -> dict:
    energetic = profile.get("energetic", 0.5)
    social    = profile.get("social", 0.5)
    aesthetic = profile.get("aesthetic", 0.5)
    if energetic > 0.65 and social > 0.6:
        return {"item": "업템포 팝·하우스·EDM", "reason": "활동적이고 사교적인 에너지에 맞는 비트"}
    elif energetic > 0.65:
        return {"item": "힙합·트랩·록", "reason": "강한 에너지를 혼자서도 즐기는 집중형 취향"}
    elif aesthetic > 0.6 and energetic < 0.5:
        return {"item": "재즈·보사노바·어쿠스틱", "reason": "감각적이고 여유로운 무드를 즐기는 타입"}
    elif energetic < 0.35:
        return {"item": "로파이 힙합·앰비언트", "reason": "조용하고 집중력 있는 배경음악 선호"}
    else:
        return {"item": "인디 팝·얼터너티브 R&B", "reason": "감성과 에너지 사이에서 균형 잡힌 취향"}


def recommend_restaurant(profile: dict) -> dict:
    adventurous = profile.get("adventurous", 0.5)
    aesthetic   = profile.get("aesthetic", 0.5)
    budget      = profile.get("budget", 0.5)
    if adventurous > 0.65:
        return {"item": "에스닉·퓨전 레스토랑", "reason": "새로운 맛과 문화를 탐험하는 미식 모험가"}
    elif aesthetic > 0.65 and budget > 0.55:
        return {"item": "분위기 좋은 파인다이닝·비스트로", "reason": "음식만큼 공간과 경험을 중요하게 여기는 타입"}
    elif budget < 0.35:
        return {"item": "로컬 맛집·가성비 한식", "reason": "진짜 맛을 아는 가성비 맛집 전문가"}
    else:
        return {"item": "이탈리안·모던 한식", "reason": "익숙하면서도 수준 있는 식사를 즐기는 타입"}


def recommend_exercise(profile: dict) -> dict:
    energetic = profile.get("energetic", 0.5)
    social    = profile.get("social", 0.5)
    urban     = profile.get("urban", 0.5)
    if energetic > 0.7:
        return {"item": "크로스핏·HIIT·복싱", "reason": "강렬한 자극과 도전을 즐기는 고강도 운동 타입"}
    elif energetic > 0.5 and urban < 0.4:
        return {"item": "등산·트레일 러닝·사이클", "reason": "자연 속에서 활동적으로 움직이는 아웃도어 타입"}
    elif social > 0.6 and energetic > 0.4:
        return {"item": "필라테스·클라이밍·댄스", "reason": "함께하며 성장하는 커뮤니티 운동을 선호"}
    elif energetic < 0.35:
        return {"item": "요가·스트레칭·산책", "reason": "몸과 마음의 균형을 챙기는 마음챙김형 운동"}
    else:
        return {"item": "수영·헬스·러닝", "reason": "꾸준하고 안정적인 루틴 운동을 선호하는 타입"}


def recommend_travel(profile: dict) -> dict:
    adventurous = profile.get("adventurous", 0.5)
    aesthetic   = profile.get("aesthetic", 0.5)
    urban       = profile.get("urban", 0.5)
    budget      = profile.get("budget", 0.5)
    if adventurous > 0.7:
        return {"item": "동남아 배낭여행·중남미 트레킹", "reason": "예측 불가능한 모험을 즐기는 진짜 탐험가"}
    elif aesthetic > 0.65 and urban > 0.5:
        return {"item": "유럽 예술·건축 도시 투어", "reason": "아름다운 것을 찾아 떠나는 감성 여행자"}
    elif urban < 0.35:
        return {"item": "제주·규슈·뉴질랜드 자연 여행", "reason": "도시를 벗어나 자연 속 힐링을 원하는 타입"}
    elif budget > 0.65:
        return {"item": "럭셔리 리조트·몰디브·발리", "reason": "완벽한 휴식과 프리미엄 경험을 추구하는 타입"}
    else:
        return {"item": "일본 소도시·대만·포르투갈", "reason": "편안하면서도 감성적인 감각 여행을 선호"}


def recommend_fashion(profile: dict) -> dict:
    maximalist = profile.get("maximalist", 0.5)
    aesthetic  = profile.get("aesthetic", 0.5)
    budget     = profile.get("budget", 0.5)
    adventurous = profile.get("adventurous", 0.5)
    if maximalist < 0.3:
        return {"item": "미니멀·모노톤 룩", "reason": "군더더기 없는 정제된 스타일로 세련미를 표현"}
    elif maximalist > 0.7 and adventurous > 0.5:
        return {"item": "스트리트·빈티지 레이어드", "reason": "개성 강한 믹스매치로 눈에 띄는 스타일링"}
    elif aesthetic > 0.6 and budget > 0.55:
        return {"item": "컨템포러리·디자이너 캐주얼", "reason": "감각적이고 수준 있는 아이템에 투자하는 타입"}
    elif maximalist > 0.5:
        return {"item": "내추럴·보헤미안 스타일", "reason": "편안하면서도 감성적인 무드를 즐기는 타입"}
    else:
        return {"item": "스마트 캐주얼·트렌디 베이직", "reason": "무난하지만 트렌드를 놓치지 않는 스타일"}


def recommend_interior(profile: dict) -> dict:
    maximalist = profile.get("maximalist", 0.5)
    urban      = profile.get("urban", 0.5)
    aesthetic  = profile.get("aesthetic", 0.5)
    budget     = profile.get("budget", 0.5)
    if maximalist < 0.3 and urban > 0.5:
        return {"item": "스칸디나비안·재패니즈 미니멀", "reason": "깔끔한 여백과 기능적 아름다움을 추구"}
    elif maximalist > 0.65 and aesthetic > 0.5:
        return {"item": "맥시멀리스트·보헤미안 스타일", "reason": "다양한 오브제와 텍스처로 개성 넘치는 공간"}
    elif urban < 0.35:
        return {"item": "우드톤·내추럴 소재 인테리어", "reason": "자연 소재로 따뜻하고 편안한 공간 구성"}
    elif budget > 0.65 and aesthetic > 0.55:
        return {"item": "모던 럭셔리·하이엔드 인테리어", "reason": "퀄리티 있는 소재와 감각적인 조명을 중시"}
    else:
        return {"item": "모던 빈티지·인더스트리얼 믹스", "reason": "트렌디하면서 개성 있는 공간을 선호"}


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
# 임계점 알림 (agent-comm push)
# ──────────────────────────────────────────────

AGENT_COMM = os.environ.get("AGENT_COMM_PATH", os.path.expanduser("~/agent-comm"))
CALIBRATION_THRESHOLDS = {
    50:  "방향성 확인 — 오행-차원 상관관계 양/음 검증 가능",
    200: "1차 파라미터 보정 — blend 가중치 및 계수 재보정 가능",
    500: "레이어 구조 재설계 — 회귀분석 기반 파라미터 도출 가능",
}

def _notify_milestone(milestone: int, total: int):
    """임계점 도달 시 flavor/tasks/에 JSON push"""
    try:
        import subprocess
        from datetime import datetime as dt

        tasks_dir = os.path.join(AGENT_COMM, "flavor", "tasks")
        if not os.path.isdir(tasks_dir):
            return

        ts = dt.now().strftime("%Y%m%d_%H%M%S")
        fname = f"{ts}_flavor_reklvm_calibration_milestone_{milestone}.json"
        payload = {
            "id": f"{ts}_flavor_reklvm_calibration_milestone_{milestone}",
            "from": "flavor",
            "to": "reklvm",
            "project": "flavor",
            "task": "calibration_alert",
            "status": "pending",
            "created_at": dt.now().isoformat(),
            "message": f"설문 {milestone}명 도달! 레이어1-4 캘리브레이션 분석 요청",
            "payload": {
                "total_submissions": total,
                "milestone": milestone,
                "note": CALIBRATION_THRESHOLDS.get(milestone, ""),
                "data_endpoint": "/api/calibration-data",
            }
        }
        fpath = os.path.join(tasks_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        subprocess.run(
            ["git", "-C", AGENT_COMM, "add", f"flavor/tasks/{fname}"],
            capture_output=True
        )
        subprocess.run(
            ["git", "-C", AGENT_COMM, "commit", "-m",
             f"alert: flavor→reklvm 설문 {milestone}명 도달, 캘리브레이션 요청"],
            capture_output=True
        )
        subprocess.run(
            ["git", "-C", AGENT_COMM, "push", "origin", "main"],
            capture_output=True
        )
    except Exception as e:
        app.logger.warning(f"milestone notify failed: {e}")


# ──────────────────────────────────────────────
# 캘리브레이션용 raw 데이터 엔드포인트
# ──────────────────────────────────────────────

@app.route("/api/calibration-data")
def calibration_data():
    """오행 원본 + 설문 원본 — 레이어1-4 파라미터 분석용"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, birth_date, birth_time, gender,
               elements_json, survey_json, created_at
        FROM submissions ORDER BY created_at ASC
    """)
    rows = c.fetchall()
    c.execute("SELECT COUNT(*) FROM submissions")
    total = c.fetchone()[0]
    conn.close()

    return jsonify({
        "total": total,
        "calibration_thresholds": CALIBRATION_THRESHOLDS,
        "next_threshold": next((m for m in [50, 200, 500] if m > total), None),
        "data": [{
            "id": r[0],
            "birth_date": r[1],
            "birth_time": r[2],
            "gender": r[3],
            "elements": json.loads(r[4]) if r[4] else {},
            "survey": json.loads(r[5]) if r[5] else {},
            "created_at": r[6],
        } for r in rows]
    })


# ──────────────────────────────────────────────
# API 라우트
# ──────────────────────────────────────────────

@app.route("/api/submit", methods=["POST"])
def submit():
    try:
        data = request.get_json(force=True)

        name       = data.get("name", "익명")
        birth_date = data.get("birth_date", "")  # "YYYY-MM-DD"
        birth_time = data.get("birth_time", "12") # 시 (0~23), 기본값 낮 12시
        gender     = data.get("gender", "unknown")

        # 설문 응답 파싱 (0~1 범위로 정규화)
        survey = {
            "social":      float(data.get("social", 0.5)),
            "aesthetic":   float(data.get("aesthetic", 0.5)),
            "adventurous": float(data.get("adventurous", 0.5)),
            "comfort":     float(data.get("comfort", 0.5)),
            "budget":      float(data.get("budget", 0.5)),
            "maximalist":  float(data.get("maximalist", 0.5)),
            "energetic":   float(data.get("energetic", 0.5)),
            "urban":       float(data.get("urban", 0.5)),
            "bitter":      float(data.get("bitter", 0.5)),
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
                                     elements_json, survey_json, profile_json, results_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result_id, name, birth_date, birth_time, gender,
            json.dumps(saju["elements"], ensure_ascii=False),  # 오행 원본
            json.dumps(survey, ensure_ascii=False),             # 설문 원본
            json.dumps(profile, ensure_ascii=False),
            json.dumps(results, ensure_ascii=False),
            datetime.now().isoformat()
        ))

        # 임계점 도달 체크 (50, 200, 500명)
        c.execute("SELECT COUNT(*) FROM submissions")
        total = c.fetchone()[0]
        milestone_hit = None
        for m in [50, 200, 500]:
            if total >= m:
                c.execute("SELECT 1 FROM milestones WHERE milestone=?", (m,))
                if not c.fetchone():
                    c.execute("INSERT INTO milestones VALUES (?, ?)",
                              (m, datetime.now().isoformat()))
                    milestone_hit = m

        conn.commit()
        conn.close()

        # 임계점 도달 시 agent-comm으로 알림 push
        if milestone_hit:
            _notify_milestone(milestone_hit, total)

        return jsonify({
            "status": "ok",
            "id": result_id,
            "name": name,
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


@app.route("/survey")
def survey():
    survey_path = os.path.join(os.path.dirname(__file__), "test_stages", "survey.html")
    with open(survey_path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/")
def index():
    return redirect("/survey", code=302)


if __name__ == "__main__":
    app.run(debug=os.environ.get("DEBUG", "false").lower() == "true",
            host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
