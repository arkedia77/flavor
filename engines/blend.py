"""오행 보정 + 설문 블렌딩 → 취향 프로필"""


def elements_to_profile(elements: dict, gender: str, survey: dict) -> dict:
    """오행(내부 보정용) + 설문 → 취향 프로필

    [v1.1 수정]
    - 사주 보정값을 [0,1] 전 범위로 정규화 (기존: 최대 0.5 → 사주 기여 1/8에 불과)
    - aesthetic 공식: 금 위주로 재조정 (금*0.7 + 수*0.3)
    - 오행 합산 방식: wood+fire는 각 비율 합 → [0,1] 범위 보장
    """
    total = sum(elements.values()) or 1

    wood  = elements.get("목", 0) / total
    fire  = elements.get("화", 0) / total
    earth = elements.get("토", 0) / total
    metal = elements.get("금", 0) / total
    water = elements.get("수", 0) / total

    def blend(saju_val, survey_val, w=0.25):
        """사주 보정값 25%, 설문값 75% 블렌딩"""
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
