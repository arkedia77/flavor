"""오행 보정 + 설문 블렌딩 → 취향 프로필

Phase 2: 12D innate vector 기반 사주 기여 (지장간 보정 오행 + 십신)
기존 API: elements_to_profile(elements, gender, survey) — 하위호환 유지
신규 API: blend_profile(innate_vector, survey) — Phase 2 권장
"""

from engines.gap import innate_to_expected_profile


def elements_to_profile(elements: dict, gender: str, survey: dict) -> dict:
    """오행(기본) + 설문 → 취향 프로필 (기존 호환 v1.x)

    [v1.1 수정]
    - 사주 보정값을 [0,1] 전 범위로 정규화
    - aesthetic 공식: 금 위주로 재조정 (금*0.7 + 수*0.3)
    """
    total = sum(elements.values()) or 1

    wood  = elements.get("목", 0) / total
    fire  = elements.get("화", 0) / total
    earth = elements.get("토", 0) / total
    metal = elements.get("금", 0) / total
    water = elements.get("수", 0) / total

    def blend(saju_val, survey_val, w=0.25):
        return round(min(1.0, max(0.0, saju_val * w + survey_val * (1 - w))), 3)

    saju_social      = min(1.0, wood + fire)
    saju_aesthetic   = min(1.0, metal * 0.7 + water * 0.3)
    saju_adventurous = min(1.0, fire + wood * 0.6)
    saju_comfort     = min(1.0, earth + metal)
    saju_energetic   = min(1.0, fire + wood * 0.5)
    saju_bitter      = min(1.0, water * 1.5)

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


def _calc_skewness(vals):
    """값 목록의 편향도 (CV) — 균등하면 0, 편향되면 높음"""
    mean = sum(vals) / len(vals) if vals else 0
    if mean == 0:
        return 0
    import math
    return math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals)) / mean


def _calc_dim_confidence(expected_val):
    """예상값이 극단(0 or 1 근처)일수록 높은 확신도 (0~1)"""
    return abs(expected_val - 0.5) * 2  # 0.5→0, 0.0/1.0→1


def dynamic_saju_weight(innate_vector: list) -> float:
    """편향도 기반 동적 사주 가중치 (15%~50%)

    편향 클수록 사주를 더 신뢰 (sigmoid 형태)
    """
    import math
    el = innate_vector[0:5]
    ss = innate_vector[5:10]
    skew = (_calc_skewness(el) + _calc_skewness(ss)) / 2
    # sigmoid: 편향 0.3→~18%, 0.5→~25%, 0.7→~35%, 1.0→~45%
    return 0.15 + 0.35 / (1 + math.exp(-5 * (skew - 0.5)))


def blend_profile(innate_vector: list, survey: dict, saju_weight: float = None) -> dict:
    """12D innate vector + 설문 → 취향 프로필 (Phase 2)

    saju_weight=None이면 편향도 기반 동적 가중치 사용.
    차원별로도 확신도에 따라 미세 조정.
    """
    expected = innate_to_expected_profile(innate_vector)

    if saju_weight is None:
        base_weight = dynamic_saju_weight(innate_vector)
    else:
        base_weight = saju_weight

    profile = {}
    for dim in expected:
        saju_val = expected[dim]
        survey_val = survey.get(dim, 0.5)

        # 차원별 가중치 조정: 예상값이 극단일수록 사주 가중치 ↑
        confidence = _calc_dim_confidence(saju_val)
        dim_weight = base_weight * (1 + confidence * 0.5)  # 최대 1.5배
        dim_weight = min(0.6, dim_weight)  # 상한 60%

        qw = 1 - dim_weight
        profile[dim] = round(min(1.0, max(0.0, saju_val * dim_weight + survey_val * qw)), 3)

    return profile
