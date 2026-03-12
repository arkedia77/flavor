"""사주 계산 (간단 버전) — Phase 1에서 정통 사주 엔진으로 교체 예정"""

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
             + [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334][month - 1] + day)
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
