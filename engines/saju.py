"""
사주팔자 계산 엔진 v2.0 — Deep Saju Engine

4주 계산 → 7개 분석 축:
  일간(Day Master), 오행 분포, 지장간 보정 오행,
  십신 분포, 격국, 음양 비율, 신강/신약
"""

from engines.calendar import jdn, get_month_branch, hour_to_branch
from engines.saju_tables import (
    STEMS, BRANCHES, ELEMENTS,
    STEM_ELEMENT, STEM_YIN_YANG,
    BRANCH_ELEMENT, BRANCH_YIN_YANG,
    HIDDEN_STEMS, HIDDEN_WEIGHTS,
    SIKSHIN_GROUPS, GEOKGUK_NAMES,
    DAY_MASTER_TYPES,
)


# ──────────────────────────────────────────────
# 4주 계산
# ──────────────────────────────────────────────

def _year_pillar(year: int, month: int, day: int):
    """년주 — 입춘(2/4) 기준 연도 전환"""
    y = year
    if month < 2 or (month == 2 and day < 4):
        y = year - 1
    stem = (y - 4) % 10
    branch = (y - 4) % 12
    return stem, branch


def _month_pillar(year_stem: int, month: int, day: int):
    """월주 — 절기 기반 월지 + 연간 기반 월간"""
    branch = get_month_branch(month, day)
    start_stem = ((year_stem % 5) * 2 + 2) % 10  # 인월 시작 천간
    months_from_in = (branch - 2 + 12) % 12
    stem = (start_stem + months_from_in) % 10
    return stem, branch


def _day_pillar(year: int, month: int, day: int):
    """일주 — JDN 기반 60갑자"""
    j = jdn(year, month, day)
    # 기준: JDN 2415021 = 1900-01-01 = 갑술(甲戌, 60갑자 index 10)
    cycle = (j - 2415021 + 10) % 60
    stem = cycle % 10
    branch = cycle % 12
    return stem, branch


def _hour_pillar(day_stem: int, hour: int):
    """시주 — 일간 기반 시간"""
    branch = hour_to_branch(hour)
    start_stem = ((day_stem % 5) * 2) % 10
    stem = (start_stem + branch) % 10
    return stem, branch


# ──────────────────────────────────────────────
# 십신 계산
# ──────────────────────────────────────────────

def get_sikshin(day_stem: int, target_stem: int) -> str:
    """일간 기준으로 target_stem의 십신 반환"""
    d_el = STEM_ELEMENT[day_stem]
    t_el = STEM_ELEMENT[target_stem]
    same_polarity = (STEM_YIN_YANG[day_stem] == STEM_YIN_YANG[target_stem])

    relation = (t_el - d_el) % 5
    table = {
        (0, True): "비견", (0, False): "겁재",
        (1, True): "식신", (1, False): "상관",
        (2, True): "편재", (2, False): "정재",
        (3, True): "편관", (3, False): "정관",
        (4, True): "편인", (4, False): "정인",
    }
    return table[(relation, same_polarity)]


# ──────────────────────────────────────────────
# 오행 분포 (지장간 포함)
# ──────────────────────────────────────────────

def _element_distribution(pillars):
    """8자 기본 오행 분포 [목,화,토,금,수] 카운트"""
    dist = [0, 0, 0, 0, 0]
    for stem, branch in pillars:
        dist[STEM_ELEMENT[stem]] += 1
        dist[BRANCH_ELEMENT[branch]] += 1
    return dist


def _element_distribution_with_hidden(pillars):
    """지장간 포함 보정 오행 분포 (가중치 적용, 합계=8)"""
    dist = [0.0, 0.0, 0.0, 0.0, 0.0]

    # 천간: 각 1.0
    for stem, _ in pillars:
        dist[STEM_ELEMENT[stem]] += 1.0

    # 지지: 지장간 가중치 적용, 합계 1.0 per 지지
    for _, branch in pillars:
        hidden = HIDDEN_STEMS[branch]
        weights = list(HIDDEN_WEIGHTS)

        # 중기 없으면 정기에 합산
        if hidden[1] is None:
            weights = [HIDDEN_WEIGHTS[0], 0.0, HIDDEN_WEIGHTS[0] + HIDDEN_WEIGHTS[2]]
            # 여기 + 정기만
            for i, (h, w) in enumerate(zip(hidden, weights)):
                if h is not None and w > 0:
                    dist[STEM_ELEMENT[h]] += w
        else:
            for h, w in zip(hidden, weights):
                if h is not None:
                    dist[STEM_ELEMENT[h]] += w

    return dist


# ──────────────────────────────────────────────
# 음양 비율
# ──────────────────────────────────────────────

def _yin_yang_ratio(pillars):
    """8자 중 양(+) 비율 반환 (0.0=전음, 1.0=전양)"""
    yang = 0
    total = len(pillars) * 2  # 천간 + 지지
    for stem, branch in pillars:
        yang += STEM_YIN_YANG[stem]
        yang += BRANCH_YIN_YANG[branch]
    return yang / total


# ──────────────────────────────────────────────
# 십신 분포
# ──────────────────────────────────────────────

def _sikshin_distribution(day_stem, pillars):
    """일간 vs 나머지 7자 → 십신 분포 (5그룹 카운트)"""
    counts = {"비겁": 0, "식상": 0, "재성": 0, "관성": 0, "인성": 0}
    sikshin_list = []

    # 다른 천간 3개 (년간, 월간, 시간)
    for i, (stem, branch) in enumerate(pillars):
        if i != 2:  # 일간 자신 제외 (index 2 = 일주)
            ss = get_sikshin(day_stem, stem)
            sikshin_list.append(ss)
            for group, members in SIKSHIN_GROUPS.items():
                if ss in members:
                    counts[group] += 1

    # 4개 지지의 정기(正氣) 기준 십신
    for _, branch in pillars:
        hidden = HIDDEN_STEMS[branch]
        main_stem = hidden[2]  # 정기
        if main_stem is not None:
            ss = get_sikshin(day_stem, main_stem)
            sikshin_list.append(ss)
            for group, members in SIKSHIN_GROUPS.items():
                if ss in members:
                    counts[group] += 1

    return counts, sikshin_list


# ──────────────────────────────────────────────
# 격국 판단
# ──────────────────────────────────────────────

def _determine_geokguk(day_stem, month_branch):
    """월지 정기(正氣)의 십신 → 격국 결정"""
    main_hidden = HIDDEN_STEMS[month_branch][2]  # 정기
    if main_hidden is None:
        return "비견격"
    ss = get_sikshin(day_stem, main_hidden)
    # 십신 → 격국 이름
    geokguk_map = {
        "비견": "비견격", "겁재": "겁재격",
        "식신": "식신격", "상관": "상관격",
        "편재": "편재격", "정재": "정재격",
        "편관": "편관격", "정관": "정관격",
        "편인": "편인격", "정인": "정인격",
    }
    return geokguk_map.get(ss, "비견격")


# ──────────────────────────────────────────────
# 신강/신약 판단
# ──────────────────────────────────────────────

def _calculate_strength(day_stem, pillars):
    """일간 강약 점수 (0~100)"""
    score = 0
    day_element = STEM_ELEMENT[day_stem]

    # 1. 득령 (월지 검사) — 40점
    month_branch = pillars[1][1]  # 월주 지지
    month_main = HIDDEN_STEMS[month_branch][2]  # 정기
    if month_main is not None:
        month_el = STEM_ELEMENT[month_main]
        if month_el == day_element:  # 비겁 (같은 오행)
            score += 40
        elif (month_el + 1) % 5 == day_element:  # 인성 (나를 생함)
            score += 30

    # 2. 득지 (지지 통근) — 30점
    for i, (_, branch) in enumerate(pillars):
        hidden = HIDDEN_STEMS[branch]
        for h in hidden:
            if h is not None and STEM_ELEMENT[h] == day_element:
                score += 8 if i == 2 else 5  # 일지 통근은 가중
                break

    # 3. 득세 (천간 도움) — 30점
    for i, (stem, _) in enumerate(pillars):
        if i == 2:  # 일간 자신 제외
            continue
        s_el = STEM_ELEMENT[stem]
        if s_el == day_element:  # 비겁
            score += 10
        elif (s_el + 1) % 5 == day_element:  # 인성
            score += 7

    return min(100, score)


# ──────────────────────────────────────────────
# 메인 분석 함수
# ──────────────────────────────────────────────

def calc_saju(year: int, month: int, day: int, hour: int = 12):
    """사주 전체 분석 — 기존 API 호환 + 확장 데이터

    Returns:
        dict with keys:
          - pillars: {year, month, day, hour} 간지 문자열 (기존 호환)
          - elements: {목,화,토,금,수} 카운트 (기존 호환)
          - saju_detail: 확장 분석 데이터 (Phase 1 신규)
    """
    # 4주 계산
    y_stem, y_branch = _year_pillar(year, month, day)
    m_stem, m_branch = _month_pillar(y_stem, month, day)
    d_stem, d_branch = _day_pillar(year, month, day)
    h_stem, h_branch = _hour_pillar(d_stem, hour)

    pillars = [
        (y_stem, y_branch),  # 0: 년주
        (m_stem, m_branch),  # 1: 월주
        (d_stem, d_branch),  # 2: 일주
        (h_stem, h_branch),  # 3: 시주
    ]

    # 기본 오행 분포 (8자)
    elem_dist = _element_distribution(pillars)
    elements = {
        "목": elem_dist[0], "화": elem_dist[1], "토": elem_dist[2],
        "금": elem_dist[3], "수": elem_dist[4]
    }

    # 지장간 보정 오행
    elem_hidden = _element_distribution_with_hidden(pillars)

    # 음양 비율
    yy_ratio = _yin_yang_ratio(pillars)

    # 십신 분포
    sikshin_counts, sikshin_list = _sikshin_distribution(d_stem, pillars)

    # 격국
    geokguk = _determine_geokguk(d_stem, m_branch)

    # 신강/신약
    strength = _calculate_strength(d_stem, pillars)

    # 일간 타입 (L1)
    day_master = DAY_MASTER_TYPES[d_stem]

    # L2 타입 코드: "갑_정관격_강"
    strength_label = "강" if strength >= 50 else "약"
    type_code = f"{STEMS[d_stem]}_{geokguk}_{strength_label}"

    return {
        # 기존 호환 필드
        "pillars": {
            "year":  f"{STEMS[y_stem]}{BRANCHES[y_branch]}",
            "month": f"{STEMS[m_stem]}{BRANCHES[m_branch]}",
            "day":   f"{STEMS[d_stem]}{BRANCHES[d_branch]}",
            "hour":  f"{STEMS[h_stem]}{BRANCHES[h_branch]}",
        },
        "elements": elements,

        # Phase 1 확장 필드
        "saju_detail": {
            "day_master": {
                "stem_idx": d_stem,
                "stem": STEMS[d_stem],
                "element": ELEMENTS[STEM_ELEMENT[d_stem]],
                "yin_yang": "양" if STEM_YIN_YANG[d_stem] else "음",
                "type": day_master,
            },
            "elements_hidden": {
                "목": round(elem_hidden[0], 2),
                "화": round(elem_hidden[1], 2),
                "토": round(elem_hidden[2], 2),
                "금": round(elem_hidden[3], 2),
                "수": round(elem_hidden[4], 2),
            },
            "sikshin": sikshin_counts,
            "sikshin_list": sikshin_list,
            "geokguk": geokguk,
            "yin_yang_ratio": round(yy_ratio, 3),
            "strength": strength,
            "strength_label": strength_label,
            "type_code": type_code,

            # 원본 인덱스 (벡터 계산용)
            "pillars_idx": {
                "year":  (y_stem, y_branch),
                "month": (m_stem, m_branch),
                "day":   (d_stem, d_branch),
                "hour":  (h_stem, h_branch),
            },
        },
    }
