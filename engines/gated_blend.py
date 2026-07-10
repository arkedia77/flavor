"""검증 게이트 블렌드 — Leoflavor v0.2

profile_d = (1 - w_d) * survey_d + w_d * prior_d

- 가중치는 config/saju_gate.json에서 로드 (config.SAJU_GATE)
- 전 차원 w=0이면 항등함수: profile == survey 정확 일치 (v0.1 동작 보존)
- prior가 None이거나 차원이 없으면 해당 차원 w=0
- require_hour_known=True(기본)이고 시간 미상이면 전 차원 w=0
"""


def apply_gated_blend(survey: dict, prior, gate: dict, hour_known: bool = True):
    """(profile, applied_weights) 반환. applied_weights는 실제 적용값 (감사 로그용)"""
    weights = gate.get("weights", {}) if gate else {}
    require_hour = gate.get("require_hour_known", True) if gate else True

    profile = {}
    applied = {}
    for dim, sv in survey.items():
        w = float(weights.get(dim, 0.0))
        if prior is None or dim not in prior or (require_hour and not hour_known):
            w = 0.0
        if w == 0.0:
            profile[dim] = sv  # 항등 보존 (부동소수점 연산도 안 거침)
        else:
            profile[dim] = round((1.0 - w) * sv + w * prior[dim], 3)
        applied[dim] = w

    return profile, applied


def any_weight_open(applied_weights: dict) -> bool:
    return any(w > 0 for w in applied_weights.values())
