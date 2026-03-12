"""사주 분석 결과 → 12D Innate Vector 변환

벡터 구조 (12D):
  [0:5]  오행 분포 (지장간 보정) — 목,화,토,금,수 각 비율 (합계≈1)
  [5:10] 십신 5그룹 분포 — 비겁,식상,재성,관성,인성 각 비율 (합계≈1)
  [10]   음양 비율 (0=전음, 1=전양)
  [11]   신강/신약 (0~1, 0.5=중립)
"""


def saju_to_innate_vector(saju_detail: dict) -> list:
    """saju_detail dict → 12D innate vector (list of float)"""

    # 오행 5D (지장간 보정, 정규화)
    eh = saju_detail["elements_hidden"]
    el_values = [eh["목"], eh["화"], eh["토"], eh["금"], eh["수"]]
    el_total = sum(el_values) or 1.0
    el_norm = [v / el_total for v in el_values]

    # 십신 5D (정규화)
    ss = saju_detail["sikshin"]
    ss_values = [ss["비겁"], ss["식상"], ss["재성"], ss["관성"], ss["인성"]]
    ss_total = sum(ss_values) or 1.0
    ss_norm = [v / ss_total for v in ss_values]

    # 음양 1D
    yy = saju_detail["yin_yang_ratio"]

    # 강약 1D (0~100 → 0~1)
    strength = saju_detail["strength"] / 100.0

    vector = el_norm + ss_norm + [yy, strength]
    return [round(v, 4) for v in vector]


VECTOR_LABELS = [
    "목(Wood)", "화(Fire)", "토(Earth)", "금(Metal)", "수(Water)",
    "비겁", "식상", "재성", "관성", "인성",
    "음양비율", "신강도",
]
