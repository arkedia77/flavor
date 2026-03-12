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


def blend_profile(innate_vector: list, survey: dict, saju_weight: float = 0.25) -> dict:
    """12D innate vector + 설문 → 취향 프로필 (Phase 2)

    사주 기여: innate vector → 9차원 예상 프로필 (gap.py 매핑)
    설문 기여: survey 9차원 그대로
    블렌딩: saju_weight (기본 25%) / survey (75%)
    """
    expected = innate_to_expected_profile(innate_vector)
    sw = saju_weight
    qw = 1 - sw

    profile = {}
    for dim in expected:
        saju_val = expected[dim]
        survey_val = survey.get(dim, 0.5)
        profile[dim] = round(min(1.0, max(0.0, saju_val * sw + survey_val * qw)), 3)

    return profile
