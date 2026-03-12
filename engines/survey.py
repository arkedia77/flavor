"""raw 설문 → 9개 차원 계산"""


def raw_to_survey(raw: dict) -> dict:
    """q1~q27 원본 응답 → 9개 차원 계산

    [v1.2 변경사항]
    - 백엔드가 유일한 계산 주체 (프론트엔드 computeProfile()과 동일 로직)
    - adventurous 다변화: 여행 4개 → 음식/여행스타일/여행목적/결정방식으로 분산
    - budget 보강: q25 단일 → q25 + 숙소선택(q22) 결합
    - maximalist 보강: q12(충동구매) 약하게 추가
    """
    def qv(k):
        v = raw.get(k) or raw.get(str(k))
        return float(v) if v is not None else 0.5

    def avg(*vals):
        return sum(vals) / len(vals)

    def clamp(v):
        return min(1.0, max(0.0, v))

    social      = clamp(avg(qv('q1'), 1 - qv('q2'), qv('q3') * 0.6 + 0.2, qv('q17') * 0.4 + 0.2))
    adventurous = clamp(avg(qv('q13'), qv('q21'), qv('q23'), qv('q5') * 0.8 + 0.1))
    aesthetic   = clamp(avg(qv('q14'), qv('q9') * 0.7 + 0.1, qv('q24'), qv('q10') * 0.5 + 0.2))
    budget      = clamp(avg(qv('q25'), (1 - qv('q22')) * 0.5 + 0.1))
    comfort     = clamp(avg(qv('q26'), qv('q27')))
    maximalist  = clamp(avg(qv('q6'), qv('q7'), qv('q11') * 0.8, qv('q10') * 0.6, qv('q12') * 0.4))
    energetic   = clamp(avg(qv('q19'), qv('q20') * 0.6 + 0.1, qv('q4') * 0.5 + 0.2, qv('q3') * 0.4 + 0.2))
    urban       = clamp(qv('q8'))
    bitter      = clamp(avg(qv('q16'), qv('q15') * 0.7 + 0.1))

    return {
        'social':      round(social,      3),
        'adventurous': round(adventurous, 3),
        'aesthetic':   round(aesthetic,   3),
        'budget':      round(budget,      3),
        'comfort':     round(comfort,     3),
        'maximalist':  round(maximalist,  3),
        'energetic':   round(energetic,   3),
        'urban':       round(urban,       3),
        'bitter':      round(bitter,      3),
    }
