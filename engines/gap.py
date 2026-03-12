"""갭 분석 — innate vector(사주) vs survey(설문) 차이 분석

사주가 예측하는 '선천적 취향 경향'과 실제 설문 응답 간의 차이를 계산.
갭이 큰 차원 = 후천적으로 변화한 영역 (캘리브레이션 핵심 데이터)
"""

# ──────────────────────────────────────────────
# 오행/십신 → 9차원 매핑 행렬
# ──────────────────────────────────────────────
# 각 행: 오행(5) 또는 십신(5)이 9차원에 기여하는 가중치
# 열 순서: social, adventurous, aesthetic, comfort, budget, maximalist, energetic, urban, bitter

# ──────────────────────────────────────────────
# 베이스라인: 16명 설문 평균 (n이 늘면 업데이트)
# 매핑 행렬은 이 베이스라인으로부터의 "편차"를 예측
# ──────────────────────────────────────────────
BASELINE = {
    "social": 0.35, "adventurous": 0.49, "aesthetic": 0.40,
    "comfort": 0.56, "budget": 0.52, "maximalist": 0.24,
    "energetic": 0.37, "urban": 0.61, "bitter": 0.63,
}

# 오행 → 9차원 편차 (v3: v1 베이스 + 데이터 보정)
# 양수 = 해당 오행이 많으면 차원값 ↑, 음수 = ↓
ELEMENT_TO_DIM = [
    # social  adv    aes    comf   budg   maxi   ener   urban  bitter
    [+0.3,   +0.3,  +0.0,  -0.2,  -0.3,  +0.2,  +0.5,  +0.3,  +0.0],  # 목(Wood)
    [+0.4,   +0.0,  +0.1,  -0.2,  +0.0,  +0.3,  +0.5,  +0.2,  +0.0],  # 화(Fire)
    [+0.2,   +0.3,  +0.2,  +0.2,  +0.0,  +0.5,  +0.0,  +0.0,  -0.2],  # 토(Earth)
    [-0.3,   +0.0,  +0.3,  +0.5,  +0.5,  +0.0,  -0.2,  +0.0,  +0.4],  # 금(Metal)
    [+0.0,   +0.1,  +0.2,  +0.0,  +0.0,  -0.3,  +0.0,  +0.0,  +0.2],  # 수(Water)
]

# 십신 → 9차원 편차 (v3: v1 베이스 + 데이터 보정)
SIKSHIN_TO_DIM = [
    # social  adv    aes    comf   budg   maxi   ener   urban  bitter
    [-0.1,   -0.3,  +0.0,  +0.4,  +0.5,  +0.0,  +0.0,  +0.0,  +0.0],  # 비겁
    [+0.2,   +0.2,  +0.1,  +0.0,  -0.3,  +0.3,  +0.3,  +0.1,  +0.0],  # 식상
    [+0.1,   +0.4,  +0.2,  +0.0,  +0.0,  +0.1,  +0.0,  +0.4,  +0.1],  # 재성
    [+0.0,   +0.0,  +0.0,  +0.3,  +0.2,  -0.3,  +0.0,  -0.2,  +0.2],  # 관성
    [+0.4,   +0.0,  +0.3,  -0.4,  +0.0,  +0.0,  +0.0,  +0.0,  -0.2],  # 인성
]

DIM_NAMES = ["social", "adventurous", "aesthetic", "comfort",
             "budget", "maximalist", "energetic", "urban", "bitter"]


def innate_to_expected_profile(innate_vector: list) -> dict:
    """12D innate vector → 9차원 예상 프로필 (0~1)

    구조: baseline + 오행편차 + 십신편차 + 음양보정 + 강약보정
    baseline = 인구 평균 (사주와 무관한 기본값)
    편차 행렬 = 사주 특성이 baseline에서 얼마나 이동시키는가
    """
    el = innate_vector[0:5]   # 오행 비율 (합≈1)
    ss = innate_vector[5:10]  # 십신 비율 (합≈1)
    yy = innate_vector[10]    # 음양 비율
    strength = innate_vector[11]  # 신강도

    # 베이스라인에서 시작
    baseline_vals = [BASELINE[d] for d in DIM_NAMES]
    expected = list(baseline_vals)

    # 오행 편차: 각 오행 비율 × 편차 가중치 (균등분포=0.2이면 영향 없음)
    for i in range(5):
        deviation = el[i] - 0.2  # 균등(0.2)에서의 편차
        for j in range(9):
            expected[j] += deviation * ELEMENT_TO_DIM[i][j]

    # 십신 편차: 각 십신 비율 × 편차 가중치 (균등=0.2이면 영향 없음)
    for i in range(5):
        deviation = ss[i] - 0.2
        for j in range(9):
            expected[j] += deviation * SIKSHIN_TO_DIM[i][j]

    # 음양 보정 (0.5 중립)
    yang_boost = (yy - 0.5) * 0.15
    expected[0] += yang_boost   # social (양→사교적)
    expected[5] += yang_boost   # maximalist
    expected[6] += yang_boost   # energetic
    expected[8] -= yang_boost   # bitter (음→깊은맛)

    # 강약 보정 (0.5 중립)
    str_boost = (strength - 0.5) * 0.15
    expected[3] += str_boost    # comfort (강→안정)
    expected[4] += str_boost    # budget (강→투자)
    expected[1] -= str_boost    # adventurous (약→모험)
    expected[7] -= str_boost    # urban (약→도시)

    # 0~1 클램프
    expected = [round(max(0.0, min(1.0, v)), 3) for v in expected]

    return dict(zip(DIM_NAMES, expected))


def compute_gap(expected_profile: dict, survey_profile: dict) -> dict:
    """선천 예상 vs 실제 설문 → 갭 분석

    Returns:
        dict with keys:
          - gaps: {dim: float} — 양수=설문이 더 높음, 음수=사주가 더 높음
          - biggest_positive: (dim, gap) — 후천적으로 가장 발달한 영역
          - biggest_negative: (dim, gap) — 선천은 강한데 설문은 낮은 영역
          - gap_magnitude: float — 전체 갭 크기 (L2 norm)
          - alignment_score: float — 0~100, 선천-후천 일치도
    """
    gaps = {}
    for dim in DIM_NAMES:
        exp = expected_profile.get(dim, 0.5)
        act = survey_profile.get(dim, 0.5)
        gaps[dim] = round(act - exp, 3)

    sorted_gaps = sorted(gaps.items(), key=lambda x: x[1])
    biggest_neg = sorted_gaps[0]
    biggest_pos = sorted_gaps[-1]

    # L2 norm of gaps
    magnitude = sum(g ** 2 for g in gaps.values()) ** 0.5

    # alignment: 갭이 0이면 100, 갭이 클수록 낮음
    # max possible magnitude ≈ 3.0 (9 dims, each ±1)
    alignment = max(0, round(100 * (1 - magnitude / 3.0)))

    return {
        "gaps": gaps,
        "biggest_positive": {"dim": biggest_pos[0], "gap": biggest_pos[1]},
        "biggest_negative": {"dim": biggest_neg[0], "gap": biggest_neg[1]},
        "gap_magnitude": round(magnitude, 3),
        "alignment_score": alignment,
    }


# ──────────────────────────────────────────────
# 갭 해석 (결과 페이지용)
# ──────────────────────────────────────────────

GAP_INTERPRETATIONS = {
    "social": {
        "pos": "타고난 것보다 더 사교적으로 변화한 사람",
        "neg": "내면의 사교성이 아직 발현되지 않은 상태",
    },
    "adventurous": {
        "pos": "경험을 통해 모험심이 크게 성장한 사람",
        "neg": "선천적 모험성이 환경에 의해 억제된 상태",
    },
    "aesthetic": {
        "pos": "후천적으로 미적 감각이 발달한 사람",
        "neg": "타고난 미적 감수성이 아직 꽃피지 않은 상태",
    },
    "comfort": {
        "pos": "안정을 더 추구하게 된 사람",
        "neg": "안정보다 도전을 선택해온 사람",
    },
    "budget": {
        "pos": "경험을 통해 투자 가치를 알게 된 사람",
        "neg": "실용주의로 변화한 사람",
    },
    "maximalist": {
        "pos": "표현과 소유에 눈을 뜬 사람",
        "neg": "미니멀리즘으로 정제된 사람",
    },
    "energetic": {
        "pos": "후천적으로 에너지가 더 넘치게 된 사람",
        "neg": "내면의 에너지를 절제하는 방법을 배운 사람",
    },
    "urban": {
        "pos": "도시 생활에 적응하며 변화한 사람",
        "neg": "도시보다 자연을 선택해온 사람",
    },
    "bitter": {
        "pos": "깊은 맛과 취향의 세계에 눈뜬 사람",
        "neg": "대중적 취향을 즐기는 편안한 사람",
    },
}


def interpret_gap(gap_result: dict) -> dict:
    """갭 분석 → 사람이 읽을 수 있는 해석"""
    pos = gap_result["biggest_positive"]
    neg = gap_result["biggest_negative"]

    interp = {}
    if abs(pos["gap"]) > 0.15:
        dim = pos["dim"]
        interp["growth"] = {
            "dim": dim,
            "label": GAP_INTERPRETATIONS[dim]["pos"],
            "gap": pos["gap"],
        }

    if abs(neg["gap"]) > 0.15:
        dim = neg["dim"]
        interp["dormant"] = {
            "dim": dim,
            "label": GAP_INTERPRETATIONS[dim]["neg"],
            "gap": neg["gap"],
        }

    interp["alignment_score"] = gap_result["alignment_score"]

    return interp
