"""십신(十神) 엔진 — lunar_python (6tail/lunar) 기반 만세력

절기 기반 년주/월주 경계, JDN 기반 일주, 시주 완전 계산.
한국 명리학 기준 KST 직접 사용.
"""

from lunar_python import Solar

# ── 한자 → 한글 매핑 ──
_STEM_CK = {
    '甲': '갑', '乙': '을', '丙': '병', '丁': '정', '戊': '무',
    '己': '기', '庚': '경', '辛': '신', '壬': '임', '癸': '계',
}
_BRANCH_CK = {
    '子': '자', '丑': '축', '寅': '인', '卯': '묘', '辰': '진', '巳': '사',
    '午': '오', '未': '미', '申': '신', '酉': '유', '戌': '술', '亥': '해',
}
_SIPSIN_CK = {
    '比肩': '비견', '劫财': '겁재', '劫財': '겁재',
    '食神': '식신', '伤官': '상관', '傷官': '상관',
    '偏财': '편재', '偏財': '편재', '正财': '정재', '正財': '정재',
    '七杀': '편관', '七殺': '편관', '正官': '정관',
    '偏印': '편인', '正印': '정인',
}


def _to_kr(ch: str) -> str:
    return _STEM_CK.get(ch, _BRANCH_CK.get(ch, ch))


def _sipsin_kr(s: str) -> str:
    return _SIPSIN_CK.get(s, s)


# ── 천간/지지 상수 (하위 호환) ──
STEMS = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
STEM_ELEMENT = {
    "갑": "목", "을": "목", "병": "화", "정": "화", "무": "토",
    "기": "토", "경": "금", "신": "금", "임": "수", "계": "수",
}
STEM_POLARITY = {
    "갑": "양", "을": "음", "병": "양", "정": "음", "무": "양",
    "기": "음", "경": "양", "신": "음", "임": "양", "계": "음",
}
BRANCHES = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
BRANCH_ELEMENT = {
    "자": "수", "축": "토", "인": "목", "묘": "목", "진": "토", "사": "화",
    "오": "화", "미": "토", "신": "금", "유": "금", "술": "토", "해": "수",
}
BRANCH_POLARITY = {
    "자": "양", "축": "음", "인": "양", "묘": "음", "진": "양", "사": "음",
    "오": "양", "미": "음", "신": "양", "유": "음", "술": "양", "해": "음",
}
PRODUCES = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
OVERCOMES = {"목": "토", "토": "수", "수": "화", "화": "금", "금": "목"}

SIPSIN_NAMES = [
    "비견", "겁재", "식신", "상관", "편재", "정재",
    "편관", "정관", "편인", "정인",
]


def _get_eight_char(year: int, month: int, day: int, hour: int = 12):
    """한국 명리학 기준 KST 시간 그대로 EightChar 반환"""
    solar = Solar.fromYmdHms(year, month, day, hour, 0, 0)
    return solar.getLunar().getEightChar()


def calc_pillars(year: int, month: int, day: int) -> dict:
    """6글자 사주 기둥 계산 (시주 제외, 기본 12시)

    Returns:
        dict: year_stem, year_branch, month_stem, month_branch,
              day_stem, day_branch, pillars
    """
    ba = _get_eight_char(year, month, day, 12)
    ys = _to_kr(ba.getYearGan())
    yb = _to_kr(ba.getYearZhi())
    ms = _to_kr(ba.getMonthGan())
    mb = _to_kr(ba.getMonthZhi())
    ds = _to_kr(ba.getDayGan())
    db = _to_kr(ba.getDayZhi())

    return {
        "year_stem": ys, "year_branch": yb,
        "month_stem": ms, "month_branch": mb,
        "day_stem": ds, "day_branch": db,
        "pillars": [(ys, yb), (ms, mb), (ds, db)],
    }


def calc_pillars_full(year: int, month: int, day: int, hour: int) -> dict:
    """8글자 사주 기둥 계산 (시주 포함)"""
    ba = _get_eight_char(year, month, day, hour)
    ys = _to_kr(ba.getYearGan())
    yb = _to_kr(ba.getYearZhi())
    ms = _to_kr(ba.getMonthGan())
    mb = _to_kr(ba.getMonthZhi())
    ds = _to_kr(ba.getDayGan())
    db = _to_kr(ba.getDayZhi())
    hs = _to_kr(ba.getTimeGan())
    hb = _to_kr(ba.getTimeZhi())

    return {
        "year_stem": ys, "year_branch": yb,
        "month_stem": ms, "month_branch": mb,
        "day_stem": ds, "day_branch": db,
        "hour_stem": hs, "hour_branch": hb,
        "pillars": [(ys, yb), (ms, mb), (ds, db), (hs, hb)],
    }


def calc_sipsin(year: int, month: int, day: int) -> dict:
    """6글자 기반 십신 분포 계산 (lunar 라이브러리 사용)

    Returns:
        dict: day_master, relations, distribution, dominant
    """
    ba = _get_eight_char(year, month, day, 12)
    ds = _to_kr(ba.getDayGan())
    day_el = STEM_ELEMENT[ds]
    day_pol = STEM_POLARITY[ds]

    dist = {name: 0 for name in SIPSIN_NAMES}

    # 천간 십신 (년간, 월간)
    for ss in [ba.getYearShiShenGan(), ba.getMonthShiShenGan()]:
        kr = _sipsin_kr(ss)
        if kr in dist:
            dist[kr] += 1

    # 지지 십신 (년지, 월지, 일지) — 본기만 카운트
    for arr in [ba.getYearShiShenZhi(), ba.getMonthShiShenZhi(), ba.getDayShiShenZhi()]:
        if arr and len(arr) > 0:
            kr = _sipsin_kr(arr[-1])  # 본기 = 마지막
            if kr in dist:
                dist[kr] += 1

    dominant = max(dist, key=dist.get) if any(v > 0 for v in dist.values()) else "비견"

    return {
        "day_master": {"stem": ds, "element": day_el, "polarity": day_pol},
        "distribution": dist,
        "dominant": dominant,
    }


# ── 십신 → 9차원 취향 보정 벡터 ──
SIPSIN_FLAVOR_MAP = {
    "비견": {"adventurous": +0.06, "energetic": +0.04, "comfort": -0.04},
    "겁재": {"social": +0.08, "energetic": +0.06, "budget": +0.04},
    "식신": {"aesthetic": +0.08, "comfort": +0.04, "bitter": +0.04},
    "상관": {"maximalist": +0.08, "adventurous": +0.06, "aesthetic": +0.04},
    "편재": {"social": +0.06, "budget": +0.08, "urban": +0.04},
    "정재": {"comfort": +0.08, "budget": -0.06, "urban": +0.04},
    "편관": {"energetic": +0.08, "urban": +0.06, "maximalist": +0.04},
    "정관": {"comfort": +0.06, "urban": +0.06, "aesthetic": +0.04},
    "편인": {"adventurous": +0.08, "aesthetic": +0.06, "social": -0.04},
    "정인": {"comfort": +0.08, "social": +0.04, "aesthetic": +0.04},
}


def sipsin_to_flavor_delta(sipsin_result: dict) -> dict:
    """십신 분포 → 9차원 보정 벡터 (delta)"""
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
