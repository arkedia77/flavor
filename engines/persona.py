"""사주 → 캐릭터/페르소나명 생성 (마케팅 훅 전용)

사주는 추천 엔진에 관여하지 않습니다.
유저에게 보여줄 캐릭터명과 스토리만 생성합니다.
"""


# 천간 10개 → 캐릭터 베이스
# 어휘 분리 (2026-07-12, EVIDENCE_AUDIT 완화책 3): 9차원 설문 어휘
# (config/dimension_lexicon.json) 사용 금지 — 자기귀인 오염 차단.
# 위반은 tests/test_lexicon_separation.py가 잡는다. 사물/자연 이미지로만 서술할 것.
DAY_MASTER_PERSONA = {
    "갑": {"name": "큰 나무의 개척자", "emoji": "🌲", "element": "목",
           "vibe": "가장 먼저 땅을 뚫고 하늘로 뻗는 기세"},
    "을": {"name": "덩굴의 적응가", "emoji": "🌿", "element": "목",
           "vibe": "어디서든 제 자리를 찾아내는 유연함"},
    "병": {"name": "태양의 무대인", "emoji": "☀️", "element": "화",
           "vibe": "무대 한가운데서 가장 밝게 타오르는 존재감"},
    "정": {"name": "촛불의 이야기꾼", "emoji": "🕯️", "element": "화",
           "vibe": "어둠이 짙을수록 또렷해지는 은은한 불빛"},
    "무": {"name": "대지의 중심축", "emoji": "🏔️", "element": "토",
           "vibe": "산맥처럼 흔들림 없는 묵직한 중심"},
    "기": {"name": "정원의 일꾼", "emoji": "🌾", "element": "토",
           "vibe": "무엇을 심어도 자라나게 하는 손길"},
    "경": {"name": "강철의 대장장이", "emoji": "⚔️", "element": "금",
           "vibe": "불에 달구고 두드려 벼려낸 단단한 기준"},
    "신": {"name": "보석의 세공사", "emoji": "💎", "element": "금",
           "vibe": "원석 속에서 빛을 골라내는 눈"},
    "임": {"name": "바다의 항해사", "emoji": "🌊", "element": "수",
           "vibe": "수평선 너머를 향해 쉬지 않고 흐르는 물길"},
    "계": {"name": "이슬의 관찰자", "emoji": "💧", "element": "수",
           "vibe": "새벽 안개처럼 스며들어 속을 꿰뚫는 직관"},
}

# 천간 리스트 (년/일 천간 계산용)
STEMS = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]


def _calc_day_stem(year: int, month: int, day: int) -> str:
    """간단한 일간 천간 계산 (정통 만세력 기준 근사치)

    정확한 만세력은 JDN 기반이지만, 캐릭터 부여 목적으로는
    이 근사 공식으로 충분합니다.
    """
    # 율리우스일수(JDN) 기반 일간 계산
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return STEMS[jdn % 10]


def get_persona(year: int, month: int, day: int) -> dict:
    """생년월일 → 캐릭터 페르소나

    Returns:
        dict: name, emoji, element, vibe, day_stem
    """
    stem = _calc_day_stem(year, month, day)
    persona = DAY_MASTER_PERSONA[stem].copy()
    persona["day_stem"] = stem
    return persona
