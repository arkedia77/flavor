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

# 프로필 버전 — 가중치/공식 변경 시 올릴 것 (캘리브레이션 재분석용)
PROFILE_VERSION = "1.2"

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
            elements_json TEXT,      -- 오행 원본 (캘리브레이션용)
            raw_survey_json TEXT,    -- q1~q27 개별 응답 원본 (캘리브레이션용)
            survey_json TEXT,        -- 9개 차원 계산값
            profile_json TEXT,       -- blend된 최종 프로필
            results_json TEXT,
            profile_version TEXT,    -- 버전 관리 (가중치 변경 추적용)
            created_at TEXT
        )
    """)
    # 기존 DB 마이그레이션 — 신규 컬럼이 없으면 추가
    for col, col_type in [
        ("raw_survey_json", "TEXT"),
        ("profile_version", "TEXT"),
    ]:
        try:
            c.execute(f"ALTER TABLE submissions ADD COLUMN {col} {col_type}")
        except Exception:
            pass  # 이미 존재하면 무시
    # 피드백 테이블: 도메인별 👍👎 저장
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id TEXT,
            domain TEXT,
            thumb INTEGER,   -- 1: 👍, -1: 👎
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
# 추천 경계값 상수 (데이터 축적 후 캘리브레이션으로 조정)
# ──────────────────────────────────────────────
HIGH  = 0.65   # 이 이상: 강한 경향
LOW   = 0.35   # 이 이하: 반대 경향
MHI   = 0.60   # 보조 상위 임계
MLO   = 0.40   # 보조 하위 임계


# ──────────────────────────────────────────────
# Layer 2 — raw 설문 → 9개 차원 계산 (백엔드 소스 오브 트루스)
# ──────────────────────────────────────────────

def raw_to_survey(raw: dict) -> dict:
    """q1~q27 원본 응답 → 9개 차원 계산

    [v1.2 변경사항]
    - 백엔드가 유일한 계산 주체 (프론트엔드 computeProfile()과 동일 로직)
    - adventurous 다변화: 여행 4개 → 음식/여행스타일/여행목적/결정방식으로 분산
    - budget 보강: q25 단일 → q25 + 숙소선택(q22) 결합
    - maximalist 보강: q12(충동구매) 약하게 추가
    """
    def qv(k):
        v = raw.get(k) or raw.get(str(k))
        return float(v) if v is not None else 0.5

    def avg(*vals):
        return sum(vals) / len(vals)

    def clamp(v):
        return min(1.0, max(0.0, v))

    social      = clamp(avg(qv('q1'), 1 - qv('q2'), qv('q3') * 0.6 + 0.2, qv('q17') * 0.4 + 0.2))
    # adventurous: 음식(q13)·여행스타일(q21)·여행목적(q23)·결정방식(q5) — 4가지 맥락으로 분산
    adventurous = clamp(avg(qv('q13'), qv('q21'), qv('q23'), qv('q5') * 0.8 + 0.1))
    aesthetic   = clamp(avg(qv('q14'), qv('q9') * 0.7 + 0.1, qv('q24'), qv('q10') * 0.5 + 0.2))
    # budget: 지출철학(q25) + 숙소수준(q22 역산) — q22 낮을수록 고급숙소 = 고예산
    budget      = clamp(avg(qv('q25'), (1 - qv('q22')) * 0.5 + 0.1))
    comfort     = clamp(avg(qv('q26'), qv('q27')))
    # maximalist: 공간/컬러/패션 + 충동구매(q12) 약하게
    maximalist  = clamp(avg(qv('q6'), qv('q7'), qv('q11') * 0.8, qv('q10') * 0.6, qv('q12') * 0.4))
    energetic   = clamp(avg(qv('q19'), qv('q20') * 0.6 + 0.1, qv('q4') * 0.5 + 0.2, qv('q3') * 0.4 + 0.2))
    urban       = clamp(qv('q8'))
    bitter      = clamp(avg(qv('q16'), qv('q15') * 0.7 + 0.1))

    return {
        'social':      round(social,      3),
        'adventurous': round(adventurous, 3),
        'aesthetic':   round(aesthetic,   3),
        'budget':      round(budget,      3),
        'comfort':     round(comfort,     3),
        'maximalist':  round(maximalist,  3),
        'energetic':   round(energetic,   3),
        'urban':       round(urban,       3),
        'bitter':      round(bitter,      3),
    }


# ──────────────────────────────────────────────
# Layer 1+2 통합 — 오행 보정 + 설문 블렌딩
# ──────────────────────────────────────────────

def elements_to_profile(elements: dict, gender: str, survey: dict) -> dict:
    """오행(내부 보정용) + 설문 → 취향 프로필

    [v1.1 수정]
    - 사주 보정값을 [0,1] 전 범위로 정규화 (기존: 최대 0.5 → 사주 기여 1/8에 불과)
    - aesthetic 공식: 금 위주로 재조정 (금*0.7 + 수*0.3)
    - 오행 합산 방식: wood+fire는 각 비율 합 → [0,1] 범위 보장
    """
    total = sum(elements.values()) or 1

    # 오행 비율 (각각 0~1, 합계=1)
    wood  = elements.get("목", 0) / total
    fire  = elements.get("화", 0) / total
    earth = elements.get("토", 0) / total
    metal = elements.get("금", 0) / total
    water = elements.get("수", 0) / total

    def blend(saju_val, survey_val, w=0.25):
        """사주 보정값 25%, 설문값 75% 블렌딩 — saju_val은 반드시 [0,1] 범위"""
        return round(min(1.0, max(0.0, saju_val * w + survey_val * (1 - w))), 3)

    # 오행 조합 → [0,1] 정규화된 사주 보정값
    # wood+fire의 합 ≤ 1.0 (오행 비율의 합=1이므로), min(1.0, ...)은 안전장치
    saju_social      = min(1.0, wood + fire)           # 목화: 외향, 활동적
    saju_aesthetic   = min(1.0, metal * 0.7 + water * 0.3)  # 금 위주, 수 보조
    saju_adventurous = min(1.0, fire + wood * 0.6)     # 화 위주, 목 보조
    saju_comfort     = min(1.0, earth + metal)         # 토금: 안정, 지속성
    saju_energetic   = min(1.0, fire + wood * 0.5)     # 화 위주
    saju_bitter      = min(1.0, water * 1.5)           # 수: 쓴맛/깊은 맛 선호

    return {
        "social":      blend(saju_social,      survey.get("social", 0.5)),
        "aesthetic":   blend(saju_aesthetic,   survey.get("aesthetic", 0.5)),
        "adventurous": blend(saju_adventurous, survey.get("adventurous", 0.5)),
        "comfort":     blend(saju_comfort,     survey.get("comfort", 0.5)),
        "budget":      round(survey.get("budget", 0.5), 3),
        "maximalist":  round(survey.get("maximalist", 0.5), 3),
        "energetic":   blend(saju_energetic,   survey.get("energetic", 0.5)),
        "urban":       round(survey.get("urban", 0.5), 3),
        "bitter":      blend(saju_bitter,      survey.get("bitter", 0.5)),
    }


# ──────────────────────────────────────────────
# 도메인별 추천 (규칙 기반)
# ──────────────────────────────────────────────

def recommend_coffee(profile: dict) -> dict:
    bitter  = profile.get("bitter", 0.5)
    budget  = profile.get("budget", 0.5)
    comfort = profile.get("comfort", 0.5)
    if bitter > 0.65:
        if budget > 0.6:
            return {"item": "스페셜티 싱글오리진 핸드드립", "reason": "진하고 복잡한 맛을 즐기는 미식가형",
                    "description": "원두 농장 이름까지 외우는 당신, 바리스타도 긴장합니다"}
        return {"item": "에스프레소·아이스 아메리카노", "reason": "강하고 깔끔한 커피를 선호하는 타입",
                "description": "내 몸의 60%는 아메리카노로 이루어져 있습니다"}
    elif bitter < 0.35:
        if comfort > 0.65:
            return {"item": "카페라떼·바닐라라떼", "reason": "부드럽고 달콤한, 언제나 변함없이 믿는 메뉴",
                    "description": "커피는 핑계, 진짜 목적은 우유 (이것도 틀린 말은 아님)"}
        return {"item": "달달한 라떼·플랫화이트", "reason": "부드럽고 달콤한 풍미를 즐기는 타입",
                "description": "디카페인도 '맛있는 커피'라 부르는 낙천적인 타입"}
    else:
        if budget > MHI:
            if comfort < LOW:
                return {"item": "스페셜티 콜드브루·블랙워터", "reason": "새로운 커피 경험을 찾는 감각적인 탐험가",
                        "description": "카페 메뉴판을 위에서 아래로 순서대로 정복 중인 사람"}
            return {"item": "오트밀크 라떼·콜드브루", "reason": "트렌디하고 감각적인 카페 경험을 선호",
                    "description": "인스타 올리기 전에 한 모금 마셔보는 진짜 감식가"}
        elif comfort > HIGH:
            return {"item": "따뜻한 아메리카노·단골 블렌드", "reason": "매일 같은 메뉴에서 안정감을 찾는 타입",
                    "description": "사장님이 보이면 이미 주문이 들어가 있는 그 메뉴"}
        return {"item": "아이스 라떼·아메리카노", "reason": "무난하지만 믿을 수 있는 클래식한 취향",
                "description": "고민 없이 고르는 게 이미 고수의 경지입니다"}


def recommend_perfume(profile: dict) -> dict:
    aesthetic   = profile.get("aesthetic", 0.5)
    maximalist  = profile.get("maximalist", 0.5)
    adventurous = profile.get("adventurous", 0.5)
    comfort     = profile.get("comfort", 0.5)
    if maximalist < LOW and aesthetic > 0.5:
        return {"item": "머스크·클린 미니멀 향", "reason": "정제되고 세련된 감각, 은은한 존재감을 선호",
                "description": "없는 듯 있는 향, 그게 제일 어렵고 제일 세련된 겁니다"}
    elif maximalist > HIGH:
        return {"item": "오리엔탈·우디 레이어드 향", "reason": "풍부하고 개성 강한 향으로 존재감을 표현",
                "description": "엘리베이터에서 한 번쯤 '무슨 향이에요?' 듣는 그 사람"}
    elif adventurous > MHI:
        return {"item": "니치 퍼퓸·아방가르드 향", "reason": "남들과 다른 독특한 향기에 끌리는 탐험가 취향",
                "description": "브랜드 이름 10번 쳐도 못 찾는 향, 그게 좋은 이유입니다"}
    elif comfort > HIGH:
        return {"item": "클래식 시그니처 향·익숙한 우디 향", "reason": "오래 써온 익숙한 향이 주는 안정감을 선호",
                "description": "10년째 같은 향수, 그게 이미 당신의 시그니처입니다"}
    else:
        return {"item": "시트러스·그린 플로럴", "reason": "청량하고 자연스러운 향으로 편안한 인상",
                "description": "봄날 공원 벤치 옆에 앉은 사람 같은 향, 기분 좋아지는 타입"}


def recommend_music(profile: dict) -> dict:
    energetic = profile.get("energetic", 0.5)
    social    = profile.get("social", 0.5)
    aesthetic = profile.get("aesthetic", 0.5)
    comfort   = profile.get("comfort", 0.5)
    if energetic > HIGH and social > MHI:
        return {"item": "업템포 팝·하우스·EDM", "reason": "활동적이고 사교적인 에너지에 맞는 비트",
                "description": "AirPods 끼는 순간 자동으로 걸음이 빨라지는 타입"}
    elif energetic > HIGH:
        return {"item": "힙합·트랩·록", "reason": "강한 에너지를 혼자서도 즐기는 집중형 취향",
                "description": "이어폰 빼라는 말 세 번째 듣고 있는 중 (못 들었음)"}
    elif aesthetic > MHI and energetic < 0.5:
        return {"item": "재즈·보사노바·어쿠스틱", "reason": "감각적이고 여유로운 무드를 즐기는 타입",
                "description": "카페 플레이리스트 운영하면 무조건 대박날 취향"}
    elif energetic < LOW:
        return {"item": "로파이 힙합·앰비언트", "reason": "조용하고 집중력 있는 배경음악 선호",
                "description": "비 오는 날 창문 보며 일하는 게 인생 최고 세팅"}
    elif comfort > HIGH:
        return {"item": "잔잔한 팝·어쿠스틱 발라드", "reason": "편안하고 익숙한 멜로디, 마음이 쉬어가는 음악",
                "description": "가사가 오늘 내 일기인 것 같을 때가 종종 있는 타입"}
    else:
        return {"item": "인디 팝·얼터너티브 R&B", "reason": "감성과 에너지 사이에서 균형 잡힌 취향",
                "description": "유튜브 알고리즘이 당신을 완벽하게 파악하고 있음"}


def recommend_restaurant(profile: dict) -> dict:
    adventurous = profile.get("adventurous", 0.5)
    aesthetic   = profile.get("aesthetic", 0.5)
    budget      = profile.get("budget", 0.5)
    comfort     = profile.get("comfort", 0.5)
    if adventurous > 0.65:
        return {"item": "에스닉·퓨전 레스토랑", "reason": "새로운 맛과 문화를 탐험하는 미식 모험가",
                "description": "메뉴판에 모르는 단어 많을수록 더 기대되는 타입"}
    elif aesthetic > 0.65 and budget > 0.55:
        return {"item": "분위기 좋은 파인다이닝·비스트로", "reason": "음식만큼 공간과 경험을 중요하게 여기는 타입",
                "description": "음식 사진보다 공간 사진이 더 많은 갤러리의 주인"}
    elif budget < 0.35:
        return {"item": "로컬 맛집·가성비 한식", "reason": "진짜 맛을 아는 가성비 맛집 전문가",
                "description": "줄 서서 먹는 건 무조건 이유가 있다고 믿는 사람"}
    elif comfort > 0.65:
        return {"item": "단골 한식집·동네 맛집", "reason": "익숙하고 편안한 곳에서 제대로 된 한 끼를 즐기는 타입",
                "description": "사장님이 반겨주는 그 집, 그 자리, 그 메뉴가 최고"}
    else:
        return {"item": "이탈리안·모던 한식", "reason": "익숙하면서도 수준 있는 식사를 즐기는 타입",
                "description": "분위기도 맛도, 딱 기대한 만큼 나오는 식당이 제일 좋은 타입"}


def recommend_exercise(profile: dict) -> dict:
    energetic = profile.get("energetic", 0.5)
    social    = profile.get("social", 0.5)
    urban     = profile.get("urban", 0.5)
    comfort   = profile.get("comfort", 0.5)
    if energetic > 0.7:
        return {"item": "크로스핏·HIIT·복싱", "reason": "강렬한 자극과 도전을 즐기는 고강도 운동 타입",
                "description": "운동 후 기절 직전이 오히려 쾌감인 사람, 맞죠?"}
    elif energetic > 0.5 and urban < 0.4:
        return {"item": "등산·트레일 러닝·사이클", "reason": "자연 속에서 활동적으로 움직이는 아웃도어 타입",
                "description": "정상 인증샷 없으면 다녀온 게 아니라는 신념의 소유자"}
    elif social > 0.6 and energetic > 0.4:
        return {"item": "필라테스·클라이밍·댄스", "reason": "함께하며 성장하는 커뮤니티 운동을 선호",
                "description": "선생님 이름도 외우고 단골 자리도 있는 찐 단골"}
    elif energetic < 0.35:
        return {"item": "요가·스트레칭·산책", "reason": "몸과 마음의 균형을 챙기는 마음챙김형 운동",
                "description": "오늘 운동? 계단 탔습니다 (이것도 운동이라고 진심으로 믿음)"}
    elif comfort > 0.65:
        return {"item": "홈트·수영·꾸준한 헬스", "reason": "익숙한 루틴으로 꾸준히 이어가는 안정형 운동",
                "description": "3년째 같은 루틴, 그 꾸준함이 사실 제일 무서운 거예요"}
    else:
        return {"item": "수영·헬스·러닝", "reason": "꾸준하고 안정적인 루틴 운동을 선호하는 타입",
                "description": "특별하진 않지만 꾸준함이 특별함을 만드는 타입"}


def recommend_travel(profile: dict) -> dict:
    adventurous = profile.get("adventurous", 0.5)
    aesthetic   = profile.get("aesthetic", 0.5)
    urban       = profile.get("urban", 0.5)
    budget      = profile.get("budget", 0.5)
    comfort     = profile.get("comfort", 0.5)
    if adventurous > 0.7:
        return {"item": "동남아 배낭여행·중남미 트레킹", "reason": "예측 불가능한 모험을 즐기는 진짜 탐험가",
                "description": "귀국 비행기 안에서 다음 여행지 검색하는 사람"}
    elif aesthetic > 0.65 and urban > 0.5:
        return {"item": "유럽 예술·건축 도시 투어", "reason": "아름다운 것을 찾아 떠나는 감성 여행자",
                "description": "미술관 입장 전부터 굿즈숍 뭐 살지 미리 찜해두는 타입"}
    elif urban < 0.35:
        return {"item": "제주·규슈·뉴질랜드 자연 여행", "reason": "도시를 벗어나 자연 속 힐링을 원하는 타입",
                "description": "숙소 창문 뷰가 여행의 절반이라고 생각하는 사람"}
    elif budget > 0.65:
        return {"item": "럭셔리 리조트·몰디브·발리", "reason": "완벽한 휴식과 프리미엄 경험을 추구하는 타입",
                "description": "체크인부터 체크아웃까지 풀서비스가 진짜 여행이라는 신봉자"}
    elif comfort > 0.65:
        return {"item": "일본·대만 꼼꼼 자유여행", "reason": "안전하고 친숙한 환경에서 여유 있게 즐기는 타입",
                "description": "엑셀 여행 계획표에 여유시간까지 잡아두는 완벽주의 여행자"}
    else:
        return {"item": "일본 소도시·대만·포르투갈", "reason": "편안하면서도 감성적인 감각 여행을 선호",
                "description": "구글 지도 즐겨찾기가 500개는 넘었을 것 같은 사람"}


def recommend_fashion(profile: dict) -> dict:
    maximalist  = profile.get("maximalist", 0.5)
    aesthetic   = profile.get("aesthetic", 0.5)
    budget      = profile.get("budget", 0.5)
    adventurous = profile.get("adventurous", 0.5)
    comfort     = profile.get("comfort", 0.5)
    if maximalist < 0.3:
        return {"item": "미니멀·모노톤 룩", "reason": "군더더기 없는 정제된 스타일로 세련미를 표현",
                "description": "옷이 10벌인데 어떻게 매일 달라 보이냐는 말 자주 듣는 타입"}
    elif maximalist > 0.7 and adventurous > 0.5:
        return {"item": "스트리트·빈티지 레이어드", "reason": "개성 강한 믹스매치로 눈에 띄는 스타일링",
                "description": "세컨핸드 샵 직원이 얼굴을 먼저 알아보는 단골"}
    elif aesthetic > MHI and budget > MHI:
        return {"item": "컨템포러리·디자이너 캐주얼", "reason": "감각적이고 수준 있는 아이템에 투자하는 타입",
                "description": "가격표 안 보는 척하면서 사실 다 보는 그런 타입 (우리 다 알고 있음)"}
    elif comfort > HIGH:
        return {"item": "편안한 캐주얼·슬랙스 무드", "reason": "편안함이 최우선, 오래 입어도 질리지 않는 기본",
                "description": "3초 코디인데 왜 이렇게 잘 입은 것처럼 보이냐, 비결이 뭐예요"}
    elif maximalist > 0.5:
        return {"item": "내추럴·보헤미안 스타일", "reason": "편안하면서도 감성적인 무드를 즐기는 타입",
                "description": "린넨 소재 들어가면 일단 손부터 가는 사람"}
    else:
        return {"item": "스마트 캐주얼·트렌디 베이직", "reason": "무난하지만 트렌드를 놓치지 않는 스타일",
                "description": "유행 따라가되 휩쓸리지 않는 균형 감각, 이게 제일 어려운 겁니다"}


def recommend_interior(profile: dict) -> dict:
    maximalist = profile.get("maximalist", 0.5)
    urban      = profile.get("urban", 0.5)
    aesthetic  = profile.get("aesthetic", 0.5)
    budget     = profile.get("budget", 0.5)
    comfort    = profile.get("comfort", 0.5)
    if maximalist < 0.3 and urban > 0.5:
        return {"item": "스칸디나비안·재패니즈 미니멀", "reason": "깔끔한 여백과 기능적 아름다움을 추구",
                "description": "물건 하나 살 때 하나 버리는 원칙, 실천하는 사람"}
    elif maximalist > HIGH and aesthetic > 0.5:
        return {"item": "맥시멀리스트·보헤미안 스타일", "reason": "다양한 오브제와 텍스처로 개성 넘치는 공간",
                "description": "어디서 구했냐는 질문을 제일 좋아하는 공간 큐레이터"}
    elif urban < LOW:
        return {"item": "우드톤·내추럴 소재 인테리어", "reason": "자연 소재로 따뜻하고 편안한 공간 구성",
                "description": "러그 하나 깔았을 뿐인데 공간이 완전히 달라지는 마법 아시죠?"}
    elif budget > HIGH and aesthetic > MHI:
        return {"item": "모던 럭셔리·하이엔드 인테리어", "reason": "퀄리티 있는 소재와 감각적인 조명을 중시",
                "description": "조명 교체에 100만 원 써도 후회 없는, 공간 투자 신봉자"}
    elif comfort > HIGH:
        return {"item": "코지 홈·패브릭 소재 따뜻한 공간", "reason": "홈카페 감성, 쉬고 싶어지는 아늑한 공간",
                "description": "손님이 '나 여기서 살고 싶다'는 말 자주 듣는 집 주인"}
    else:
        return {"item": "모던 빈티지·인더스트리얼 믹스", "reason": "트렌디하면서 개성 있는 공간을 선호",
                "description": "새것 같은 빈티지, 빈티지 같은 새것, 그 경계 어딘가"}


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
               elements_json, raw_survey_json, survey_json, profile_version, created_at
        FROM submissions ORDER BY created_at ASC
    """)
    rows = c.fetchall()
    c.execute("SELECT COUNT(*) FROM submissions")
    total = c.fetchone()[0]
    conn.close()

    return jsonify({
        "total": total,
        "profile_version": PROFILE_VERSION,
        "calibration_thresholds": CALIBRATION_THRESHOLDS,
        "next_threshold": next((m for m in [50, 200, 500] if m > total), None),
        "data": [{
            "id": r[0],
            "birth_date": r[1],
            "birth_time": r[2],
            "gender": r[3],
            "elements": json.loads(r[4]) if r[4] else {},
            "raw_answers": json.loads(r[5]) if r[5] else {},   # q1~q27 원본
            "survey": json.loads(r[6]) if r[6] else {},
            "profile_version": r[7],
            "created_at": r[8],
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

        # q1~q27 원본 개별 응답 저장 (캘리브레이션·재분석용)
        raw_answers = data.get("raw_answers", {})

        # 백엔드가 소스 오브 트루스: raw_answers → 9개 차원 계산
        if raw_answers:
            survey = raw_to_survey(raw_answers)
        else:
            # 하위 호환: 프론트엔드가 직접 계산값 전송한 구버전 요청
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
                                     elements_json, raw_survey_json, survey_json,
                                     profile_json, results_json, profile_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result_id, name, birth_date, birth_time, gender,
            json.dumps(saju["elements"], ensure_ascii=False),   # 오행 원본
            json.dumps(raw_answers, ensure_ascii=False),        # q1~q27 원본
            json.dumps(survey, ensure_ascii=False),             # 9개 차원 계산값
            json.dumps(profile, ensure_ascii=False),            # blend된 최종 프로필
            json.dumps(results, ensure_ascii=False),
            PROFILE_VERSION,
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


@app.route("/api/feedback", methods=["POST"])
def feedback():
    """도메인별 👍👎 피드백 저장"""
    try:
        data = request.get_json(force=True)
        submission_id = data.get("submission_id", "")
        domain        = data.get("domain", "")
        thumb         = int(data.get("thumb", 0))  # 1 or -1
        if not submission_id or not domain or thumb not in (1, -1):
            return jsonify({"status": "error", "message": "invalid params"}), 400
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO feedbacks (submission_id, domain, thumb, created_at) VALUES (?,?,?,?)",
            (submission_id, domain, thumb, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


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
