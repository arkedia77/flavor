"""십신(十神) 엔진 — 일간 기준 사주 팔자 관계 분석

6글자 기반 (시주 제외): 년간/년지/월간/월지/일간/일지
일간(Day Master)과 나머지 5글자의 오행 관계 → 십신 분포 산출
십신 분포 → 9차원 취향 보정 벡터 생성 (향후 blend 재도입 시 활용)
"""

# ── 천간 ──
STEMS = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
STEM_ELEMENT = {
    "갑": "목", "을": "목",
    "병": "화", "정": "화",
    "무": "토", "기": "토",
    "경": "금", "신": "금",
    "임": "수", "계": "수",
}
STEM_POLARITY = {
    "갑": "양", "을": "음", "병": "양", "정": "음", "무": "양",
    "기": "음", "경": "양", "신": "음", "임": "양", "계": "음",
}

# ── 지지 ──
BRANCHES = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
BRANCH_ELEMENT = {
    "자": "수", "축": "토", "인": "목", "묘": "목",
    "진": "토", "사": "화", "오": "화", "미": "토",
    "신": "금", "유": "금", "술": "토", "해": "수",
}
BRANCH_POLARITY = {
    "자": "양", "축": "음", "인": "양", "묘": "음",
    "진": "양", "사": "음", "오": "양", "미": "음",
    "신": "양", "유": "음", "술": "양", "해": "음",
}

# ── 오행 생극 관계 ──
PRODUCES = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}  # 생
OVERCOMES = {"목": "토", "토": "수", "수": "화", "화": "금", "금": "목"}  # 극

# ── 십신 10종 ──
SIPSIN_NAMES = [
    "비견", "겁재",   # 같은 오행
    "식신", "상관",   # 내가 생하는 오행
    "편재", "정재",   # 내가 극하는 오행
    "편관", "정관",   # 나를 극하는 오행
    "편인", "정인",   # 나를 생하는 오행
]


def _get_sipsin(day_element: str, day_polarity: str,
                target_element: str, target_polarity: str) -> str:
    """일간과 대상 글자의 십신 관계 판별"""
    same_pol = (day_polarity == target_polarity)

    if target_element == day_element:
        return "비견" if same_pol else "겁재"
    elif target_element == PRODUCES[day_element]:
        return "식신" if same_pol else "상관"
    elif target_element == OVERCOMES[day_element]:
        return "편재" if same_pol else "정재"
    elif day_element == PRODUCES[target_element]:
        # target이 나를 생해주는 오행
        return "편인" if same_pol else "정인"
    elif day_element == OVERCOMES[target_element]:
        # target이 나를 극하는 오행
        return "편관" if same_pol else "정관"
    # fallback (불가능하지만 안전장치)
    return "비견"


# ── 사주 기둥 계산 ──

def _calc_year_stem(year: int) -> str:
    """연간 천간"""
    return STEMS[(year - 4) % 10]


def _calc_year_branch(year: int) -> str:
    """연지 지지"""
    return BRANCHES[(year - 4) % 12]


def _calc_month_stem(year: int, month: int) -> str:
    """월간 천간 (연간 기준 오호기법)"""
    year_stem_idx = (year - 4) % 10
    # 오호기법: 갑기→병인월, 을경→무인월, 병신→경인월, 정임→임인월, 무계→갑인월
    base_map = {0: 2, 1: 4, 2: 6, 3: 8, 4: 0,
                5: 2, 6: 4, 7: 6, 8: 8, 9: 0}
    base = base_map[year_stem_idx]
    return STEMS[(base + month - 1) % 10]


def _calc_month_branch(month: int) -> str:
    """월지 지지 (인월=1월 기준)"""
    # 음력 1월=인(寅), 2월=묘(卯), ...
    return BRANCHES[(month + 1) % 12]


def _calc_day_stem(year: int, month: int, day: int) -> str:
    """일간 천간 (JDN 기반)"""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return STEMS[jdn % 10]


def _calc_day_branch(year: int, month: int, day: int) -> str:
    """일지 지지 (JDN 기반)"""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return BRANCHES[jdn % 12]


def calc_pillars(year: int, month: int, day: int) -> dict:
    """6글자 사주 기둥 계산 (시주 제외)

    Returns:
        dict: {
            "year_stem", "year_branch",
            "month_stem", "month_branch",
            "day_stem", "day_branch",
            "pillars": [(stem, branch), (stem, branch), (stem, branch)]
        }
    """
    ys = _calc_year_stem(year)
    yb = _calc_year_branch(year)
    ms = _calc_month_stem(year, month)
    mb = _calc_month_branch(month)
    ds = _calc_day_stem(year, month, day)
    db = _calc_day_branch(year, month, day)

    return {
        "year_stem": ys, "year_branch": yb,
        "month_stem": ms, "month_branch": mb,
        "day_stem": ds, "day_branch": db,
        "pillars": [(ys, yb), (ms, mb), (ds, db)],
    }


def calc_sipsin(year: int, month: int, day: int) -> dict:
    """6글자 기반 십신 분포 계산

    Returns:
        dict: {
            "day_master": {"stem": "갑", "element": "목", "polarity": "양"},
            "relations": [{"char": "병", "type": "stem/branch", "sipsin": "식신"}, ...],
            "distribution": {"비견": 1, "식신": 2, ...},  # 각 십신 등장 횟수
            "dominant": "식신",  # 최다 십신
        }
    """
    p = calc_pillars(year, month, day)
    ds = p["day_stem"]
    day_el = STEM_ELEMENT[ds]
    day_pol = STEM_POLARITY[ds]

    # 일간 제외 5글자와의 관계
    targets = [
        (p["year_stem"], "stem"),
        (p["year_branch"], "branch"),
        (p["month_stem"], "stem"),
        (p["month_branch"], "branch"),
        (p["day_branch"], "branch"),
    ]

    relations = []
    dist = {name: 0 for name in SIPSIN_NAMES}

    for char, char_type in targets:
        if char_type == "stem":
            t_el = STEM_ELEMENT[char]
            t_pol = STEM_POLARITY[char]
        else:
            t_el = BRANCH_ELEMENT[char]
            t_pol = BRANCH_POLARITY[char]

        sipsin = _get_sipsin(day_el, day_pol, t_el, t_pol)
        relations.append({"char": char, "type": char_type, "sipsin": sipsin})
        dist[sipsin] += 1

    # 최다 십신 (동률 시 첫 번째)
    dominant = max(dist, key=dist.get) if any(v > 0 for v in dist.values()) else "비견"

    return {
        "day_master": {"stem": ds, "element": day_el, "polarity": day_pol},
        "relations": relations,
        "distribution": dist,
        "dominant": dominant,
    }


# ── 십신 → 9차원 취향 보정 벡터 ──
# 이론적 근거: 십신 성격론 + MBTI-취향 연구 교차 매핑
# 각 십신이 높을 때 어떤 차원을 보정하는지 (delta 값, -0.1 ~ +0.1)
SIPSIN_FLAVOR_MAP = {
    "비견": {  # 독립적, 경쟁적, 자기주관 강함
        "adventurous": +0.06, "energetic": +0.04, "comfort": -0.04,
    },
    "겁재": {  # 사교적, 경쟁적, 대범함
        "social": +0.08, "energetic": +0.06, "budget": +0.04,
    },
    "식신": {  # 창의적, 온화, 미식가, 감각적
        "aesthetic": +0.08, "comfort": +0.04, "bitter": +0.04,
    },
    "상관": {  # 반항적, 예술적, 독창적
        "maximalist": +0.08, "adventurous": +0.06, "aesthetic": +0.04,
    },
    "편재": {  # 사교적, 활동적, 소비적
        "social": +0.06, "budget": +0.08, "urban": +0.04,
    },
    "정재": {  # 검소, 안정, 성실
        "comfort": +0.08, "budget": -0.06, "urban": +0.04,
    },
    "편관": {  # 권위적, 강인, 도전적
        "energetic": +0.08, "urban": +0.06, "maximalist": +0.04,
    },
    "정관": {  # 규율적, 체계적, 안정 추구
        "comfort": +0.06, "urban": +0.06, "aesthetic": +0.04,
    },
    "편인": {  # 독특, 학구적, 비주류
        "adventurous": +0.08, "aesthetic": +0.06, "social": -0.04,
    },
    "정인": {  # 양육적, 전통적, 학문적
        "comfort": +0.08, "social": +0.04, "aesthetic": +0.04,
    },
}


def sipsin_to_flavor_delta(sipsin_result: dict) -> dict:
    """십신 분포 → 9차원 보정 벡터 (delta)

    5글자의 십신 분포를 가중 평균하여 각 차원의 delta 값 산출.
    이 delta를 설문 프로필에 더하면 십신 보정 적용.

    Returns:
        dict: {"social": 0.02, "adventurous": -0.01, ...}
    """
    from config import DIMENSIONS

    delta = {d: 0.0 for d in DIMENSIONS}
    total = sum(sipsin_result["distribution"].values())
    if total == 0:
        return delta

    for sipsin_name, count in sipsin_result["distribution"].items():
        if count == 0:
            continue
        weight = count / total
        for dim, val in SIPSIN_FLAVOR_MAP.get(sipsin_name, {}).items():
            delta[dim] += val * weight

    return {d: round(v, 4) for d, v in delta.items()}
