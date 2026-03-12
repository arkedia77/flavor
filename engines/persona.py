"""사주 → 캐릭터/페르소나명 생성 (마케팅 훅 전용)

사주는 추천 엔진에 관여하지 않습니다.
유저에게 보여줄 캐릭터명과 스토리만 생성합니다.
"""


# 천간 10개 → 캐릭터 베이스
DAY_MASTER_PERSONA = {
    "갑": {"name": "큰 나무의 개척자", "emoji": "🌲", "element": "목",
           "vibe": "새로운 길을 만드는 사람"},
    "을": {"name": "덩굴의 적응가", "emoji": "🌿", "element": "목",
           "vibe": "어디서든 자리를 잡는 유연한 감각"},
    "병": {"name": "태양의 무대인", "emoji": "☀️", "element": "화",
           "vibe": "주목받을 때 빛나는 에너지"},
    "정": {"name": "촛불의 감성가", "emoji": "🕯️", "element": "화",
           "vibe": "은은하지만 깊은 감각의 소유자"},
    "무": {"name": "대지의 중심축", "emoji": "🏔️", "element": "토",
           "vibe": "흔들리지 않는 안정감"},
    "기": {"name": "정원의 큐레이터", "emoji": "🌾", "element": "토",
           "vibe": "사소한 것도 아름답게 가꾸는 손길"},
    "경": {"name": "강철의 완벽주의자", "emoji": "⚔️", "element": "금",
           "vibe": "타협 없는 기준, 날카로운 취향"},
    "신": {"name": "보석의 감식가", "emoji": "💎", "element": "금",
           "vibe": "정제된 아름다움을 알아보는 눈"},
    "임": {"name": "바다의 탐험가", "emoji": "🌊", "element": "수",
           "vibe": "끝없이 새로운 것을 향해 흐르는 호기심"},
    "계": {"name": "이슬의 관찰자", "emoji": "💧", "element": "수",
           "vibe": "조용히 스며들어 본질을 꿰뚫는 직관"},
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
