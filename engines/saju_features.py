"""사주 피처 추출 엔진 v2 — Leoflavor v0.2 검증 게이트용

lunar_python 기반 만세력에서 통계 검증 가능한 결정적 피처 벡터를 추출한다.
- 십신 강도 (지장간·궁성 가중), 신강약 연속 점수, 억부용신, 격국, 음양, 오행
- 모든 출력은 JSON-serializable, 동일 입력 → 동일 출력 (결정적)
- 시간 미상(hour=None) 시 시주 슬롯을 제외하고 재정규화 (12시 가짜 주입 금지)

이 모듈의 피처는 추천에 직접 반영되지 않는다. config/saju_gate.json의
가중치가 검증 게이트(scripts/validate_saju_signal.py) 통과로 개방되기 전까지
sipsin_prior_delta / saju_prior_9d는 저장·검증용으로만 쓰인다.

주의: 오행 count 회귀는 2026-03-12에 신호 없음 판정(CV R²=-0.222).
elements.counts는 그 실패 베이스라인과의 대조를 위해 유지하는 피처다.
"""

from lunar_python import Solar

from engines.sipsin import (
    STEM_ELEMENT, STEM_POLARITY, BRANCH_ELEMENT, BRANCH_POLARITY,
    PRODUCES, OVERCOMES, SIPSIN_NAMES, _to_kr,
)

SCHEMA_VERSION = "sf-1"

ELEMENTS = ["목", "화", "토", "금", "수"]
_EL_IDX = {el: i for i, el in enumerate(ELEMENTS)}

SIKSHIN_GROUPS = {
    "비겁": ["비견", "겁재"],
    "식상": ["식신", "상관"],
    "재성": ["편재", "정재"],
    "관성": ["편관", "정관"],
    "인성": ["편인", "정인"],
}
_GROUP_OF = {ss: g for g, members in SIKSHIN_GROUPS.items() for ss in members}

# 궁성(위치) 가중 — 월지 본기가 사령부라는 자평 원칙 반영
PALACE_WEIGHTS = {
    "년간": 1.0, "월간": 1.2, "시간": 1.0,
    "년지": 1.0, "월지": 2.5, "일지": 1.5, "시지": 1.0,
}

# 지장간 가중 — lunar_python 순서 [본기, 중기, 여기] 기준 (실측 확인)
HIDDEN_WEIGHTS_BY_LEN = {
    1: [1.0],
    2: [0.7, 0.3],
    3: [0.6, 0.3, 0.1],
}

# 신강약: 슬롯이 일간을 돕는 정도 (비겁 1.0, 인성 0.8, 기타 0)
# 균등분포 기대값 = 0.2*1.0 + 0.2*0.8 = 0.36 → 중화점
STRENGTH_NEUTRAL = 0.36
STRENGTH_STRONG = 0.42   # label용
STRENGTH_WEAK = 0.30


# ── 십신 → 9차원 prior 가설 테이블 v2 ──
# 근거: engines/research/sipsin_mbti_tcm_research.md
#   evidence "MBTI-p05" = 십신↔MBTI 상관 논문 유의(p<0.05) 5쌍
#   evidence "실무"     = 실무 아키타입/TCM 프로파일 (논문 무관)
# 순수 데이터 테이블 — 방향성이 본질, 진폭은 검증 후 회귀로 재추정 대상.
SIPSIN_FLAVOR_MAP_V2 = {
    "상관": {"delta": {"maximalist": +0.08, "adventurous": +0.08, "social": +0.06,
                       "aesthetic": +0.05, "comfort": -0.05},
             "rationale": "EF(외향감정) + 반항아/서브컬처/실험적 스타일",
             "evidence": "MBTI-p05"},
    "정관": {"delta": {"urban": +0.06, "comfort": +0.05, "aesthetic": +0.04,
                       "maximalist": -0.06, "adventurous": -0.05},
             "rationale": "ET(외향사고) + 클래식/정돈/브랜드 정통성",
             "evidence": "MBTI-p05"},
    "정재": {"delta": {"comfort": +0.08, "budget": -0.08, "adventurous": -0.06,
                       "social": -0.04, "urban": +0.03},
             "rationale": "IS(내향감각) + 가성비/실용/전통",
             "evidence": "MBTI-p05"},
    "편재": {"delta": {"adventurous": +0.08, "social": +0.07, "urban": +0.06,
                       "budget": +0.06, "comfort": -0.04},
             "rationale": "ES(외향감각) + 모험가/여행/새 음식/과시 소비",
             "evidence": "MBTI-p05"},
    "식신": {"delta": {"aesthetic": +0.07, "comfort": +0.06, "bitter": +0.05,
                       "social": -0.03, "energetic": -0.03},
             "rationale": "IF(내향감정) + 미식가/감성 경험/깊은맛",
             "evidence": "MBTI-p05"},
    "비견": {"delta": {"adventurous": +0.05, "comfort": +0.03, "social": -0.05},
             "rationale": "자기동일/독립적 취향/브랜드 충성 — 군중 비의존",
             "evidence": "실무"},
    "겁재": {"delta": {"social": +0.07, "budget": +0.06, "maximalist": +0.06,
                       "energetic": +0.05, "urban": +0.05},
             "rationale": "경쟁자/트렌드 민감/한정판/과시적 소비",
             "evidence": "실무"},
    "편관": {"delta": {"energetic": +0.08, "adventurous": +0.06, "maximalist": +0.05,
                       "urban": +0.04, "comfort": -0.06},
             "rationale": "투사/강렬한 경험/스포츠/자극적 음식",
             "evidence": "실무"},
    "편인": {"delta": {"adventurous": +0.07, "bitter": +0.06, "aesthetic": +0.04,
                       "social": -0.06, "urban": -0.03},
             "rationale": "탐구자/마이너·비주류/영적 경험 (MBTI 무관 판정 → 독자 모델)",
             "evidence": "실무"},
    "정인": {"delta": {"comfort": +0.07, "bitter": +0.04, "aesthetic": +0.03,
                       "maximalist": -0.05, "budget": -0.03},
             "rationale": "스승/전통문화/건강식/교육 (MBTI 무관 판정 → 독자 모델)",
             "evidence": "실무"},
}

# flatten()용 로마자 키
_SIPSIN_ASCII = {
    "비견": "bigyeon", "겁재": "geopjae", "식신": "siksin", "상관": "sanggwan",
    "편재": "pyeonjae", "정재": "jeongjae", "편관": "pyeongwan", "정관": "jeonggwan",
    "편인": "pyeonin", "정인": "jeongin",
}
_GROUP_ASCII = {"비겁": "bigyeop", "식상": "siksang", "재성": "jaeseong",
                "관성": "gwanseong", "인성": "inseong"}
_EL_ASCII = {"목": "wood", "화": "fire", "토": "earth", "금": "metal", "수": "water"}


# ── 오행 관계 헬퍼 ──

def _rel_elements(day_el: str) -> dict:
    """일간 오행 기준 5관계 오행"""
    return {
        "비겁": day_el,
        "식상": PRODUCES[day_el],                                   # 내가 생
        "재성": OVERCOMES[day_el],                                  # 내가 극
        "관성": next(k for k, v in OVERCOMES.items() if v == day_el),  # 나를 극
        "인성": next(k for k, v in PRODUCES.items() if v == day_el),   # 나를 생
    }


def _sipsin_of(day_stem: str, target_stem: str) -> str:
    """일간 대비 target 천간의 십신 판정 (v1.5 get_sikshin 포팅, 한글 기반)"""
    d = _EL_IDX[STEM_ELEMENT[day_stem]]
    t = _EL_IDX[STEM_ELEMENT[target_stem]]
    same = STEM_POLARITY[day_stem] == STEM_POLARITY[target_stem]
    relation = (t - d) % 5
    table = {
        (0, True): "비견", (0, False): "겁재",
        (1, True): "식신", (1, False): "상관",
        (2, True): "편재", (2, False): "정재",
        (3, True): "편관", (3, False): "정관",
        (4, True): "편인", (4, False): "정인",
    }
    return table[(relation, same)]


# ── 만세력 → 가중 슬롯 전개 ──

def _get_eight_char(year, month, day, hour):
    solar = Solar.fromYmdHms(year, month, day, hour, 0, 0)
    return solar.getLunar().getEightChar()


def _hidden_kr(hide_gan_list) -> list:
    return [_to_kr(g) for g in hide_gan_list]


def _weighted_slots(ba, hour_known: bool):
    """8자(6자) → [(천간글자, weight, 위치태그)] 전개.

    천간은 그대로, 지지는 지장간([본기,중기,여기])으로 전개해
    궁성가중 × 지장간가중을 곱한다. 일간은 기준점이므로 제외.
    """
    slots = []
    stems = [("년간", ba.getYearGan()), ("월간", ba.getMonthGan())]
    branches = [
        ("년지", ba.getYearHideGan()),
        ("월지", ba.getMonthHideGan()),
        ("일지", ba.getDayHideGan()),
    ]
    if hour_known:
        stems.append(("시간", ba.getTimeGan()))
        branches.append(("시지", ba.getTimeHideGan()))

    for tag, gan in stems:
        slots.append((_to_kr(gan), PALACE_WEIGHTS[tag], tag))

    for tag, hidden in branches:
        kr = _hidden_kr(hidden)
        weights = HIDDEN_WEIGHTS_BY_LEN[len(kr)]
        for stem, hw in zip(kr, weights):
            slots.append((stem, PALACE_WEIGHTS[tag] * hw, tag))

    return slots


# ── 개별 피처 계산 ──

def _sipsin_features(day_stem: str, slots) -> dict:
    strength = {name: 0.0 for name in SIPSIN_NAMES}
    total = sum(w for _, w, _ in slots)
    for stem, w, _ in slots:
        strength[_sipsin_of(day_stem, stem)] += w
    if total > 0:
        strength = {k: v / total for k, v in strength.items()}

    groups = {g: sum(strength[s] for s in members)
              for g, members in SIKSHIN_GROUPS.items()}
    ranked = sorted(strength.items(), key=lambda kv: (-kv[1], SIPSIN_NAMES.index(kv[0])))
    dominant = ranked[0][0]
    margin = ranked[0][1] - ranked[1][1]

    return {
        "strength": {k: round(v, 4) for k, v in strength.items()},
        "groups": {k: round(v, 4) for k, v in groups.items()},
        "dominant": dominant,
        "dominant_margin": round(margin, 4),
    }


def _strength_features(day_stem: str, ba, slots, hour_known: bool) -> dict:
    day_el = STEM_ELEMENT[day_stem]
    rel = _rel_elements(day_el)

    def support(el: str) -> float:
        if el == rel["비겁"]:
            return 1.0
        if el == rel["인성"]:
            return 0.8
        return 0.0

    total = sum(w for _, w, _ in slots)
    score = sum(w * support(STEM_ELEMENT[stem]) for stem, w, _ in slots) / total

    # 득령: 월지 본기
    month_main = _hidden_kr(ba.getMonthHideGan())[0]
    m_el = STEM_ELEMENT[month_main]
    deukryeong = 1.0 if m_el == rel["비겁"] else (0.75 if m_el == rel["인성"] else 0.0)

    # 득지: 지지 통근 (지장간에 일간 오행 존재), 일지 1.5배 가중
    branch_hiddens = [("년지", ba.getYearHideGan()), ("월지", ba.getMonthHideGan()),
                      ("일지", ba.getDayHideGan())]
    if hour_known:
        branch_hiddens.append(("시지", ba.getTimeHideGan()))
    root_w, root_total = 0.0, 0.0
    for tag, hidden in branch_hiddens:
        w = 1.5 if tag == "일지" else 1.0
        root_total += w
        if any(STEM_ELEMENT[s] == day_el for s in _hidden_kr(hidden)):
            root_w += w
    deukji = root_w / root_total

    # 득세: 타 천간 중 비겁/인성 비율
    other_stems = [_to_kr(ba.getYearGan()), _to_kr(ba.getMonthGan())]
    if hour_known:
        other_stems.append(_to_kr(ba.getTimeGan()))
    deukse = sum(support(STEM_ELEMENT[s]) for s in other_stems) / len(other_stems)

    if score > STRENGTH_STRONG:
        label = "신강"
    elif score < STRENGTH_WEAK:
        label = "신약"
    else:
        label = "중화"

    return {
        "score": round(score, 4), "label": label,
        "득령": round(deukryeong, 4), "득지": round(deukji, 4), "득세": round(deukse, 4),
    }


def _yongsin_features(day_stem: str, strength_score: float, elements_weighted: dict) -> dict:
    """억부용신 — 결정적 규칙.

    신약: 인성/비겁 오행 중 명식 내 가중 비중이 큰 쪽 (동률 시 인성)
    신강: 식상/재성/관성 오행 중 가중 비중 최대 (있는 것을 쓴다), 희신 = 용신을 생하는 오행
    조후용신은 유파 이견이 커서 제외 — method 필드로 향후 확장.
    """
    rel = _rel_elements(STEM_ELEMENT[day_stem])

    if strength_score < STRENGTH_NEUTRAL:
        cands = [rel["인성"], rel["비겁"]]
        yongsin = max(cands, key=lambda el: (elements_weighted[el], el == rel["인성"]))
        huisin = cands[0] if yongsin == cands[1] else cands[1]
    else:
        cands = [rel["식상"], rel["재성"], rel["관성"]]
        yongsin = max(cands, key=lambda el: (elements_weighted[el], -cands.index(el)))
        huisin = next(k for k, v in PRODUCES.items() if v == yongsin)

    degree = min(1.0, abs(strength_score - STRENGTH_NEUTRAL) / STRENGTH_NEUTRAL)
    return {
        "method": "억부", "element": yongsin, "희신": huisin,
        "degree": round(degree, 4),
        "strength_in_chart": round(elements_weighted[yongsin], 4),
    }


def _gyeokguk_features(day_stem: str, ba, hour_known: bool) -> dict:
    """격국 — 월지 본기 기준 + 투간 보정.

    월지 지장간 중 천간(년간/월간/시간)에 투출한 글자가 있으면 우선
    (본기 투출 > 중기 > 여기), 미투출 시 본기.
    시간 미상이면 시간(時干)은 투간 후보에서 제외 (가짜 12시 누출 금지).
    """
    hidden = _hidden_kr(ba.getMonthHideGan())  # [본기, 중기, 여기]
    visible = {_to_kr(ba.getYearGan()), _to_kr(ba.getMonthGan())}
    if hour_known:
        visible.add(_to_kr(ba.getTimeGan()))

    chosen, tugan = hidden[0], False
    for h in hidden:
        if h in visible:
            chosen, tugan = h, True
            break

    ss = _sipsin_of(day_stem, chosen)
    return {"name": f"{ss}격", "group": _GROUP_OF[ss], "tugan": tugan}


def _element_features(day_stem: str, ba, slots, hour_known: bool) -> dict:
    import math

    # raw counts: 천간 + 지지 대표오행 (v0.1 실패 베이스라인 대조군)
    chars = [(_to_kr(ba.getYearGan()), _to_kr(ba.getYearZhi())),
             (_to_kr(ba.getMonthGan()), _to_kr(ba.getMonthZhi())),
             (_to_kr(ba.getDayGan()), _to_kr(ba.getDayZhi()))]
    if hour_known:
        chars.append((_to_kr(ba.getTimeGan()), _to_kr(ba.getTimeZhi())))
    counts = {el: 0 for el in ELEMENTS}
    for stem, branch in chars:
        counts[STEM_ELEMENT[stem]] += 1
        counts[BRANCH_ELEMENT[branch]] += 1

    # 가중 분포: 십신 슬롯 + 일간(1.0) 포함
    weighted = {el: 0.0 for el in ELEMENTS}
    weighted[STEM_ELEMENT[day_stem]] += 1.0
    for stem, w, _ in slots:
        weighted[STEM_ELEMENT[stem]] += w
    total = sum(weighted.values())
    weighted = {el: v / total for el, v in weighted.items()}

    entropy = -sum(p * math.log(p) for p in weighted.values() if p > 0) / math.log(5)

    return {
        "counts": counts,
        "weighted": {el: round(v, 4) for el, v in weighted.items()},
        "entropy": round(entropy, 4),
    }


def _yinyang_ratio(ba, hour_known: bool) -> float:
    pairs = [(_to_kr(ba.getYearGan()), _to_kr(ba.getYearZhi())),
             (_to_kr(ba.getMonthGan()), _to_kr(ba.getMonthZhi())),
             (_to_kr(ba.getDayGan()), _to_kr(ba.getDayZhi()))]
    if hour_known:
        pairs.append((_to_kr(ba.getTimeGan()), _to_kr(ba.getTimeZhi())))
    yang = sum((STEM_POLARITY[s] == "양") + (BRANCH_POLARITY[b] == "양") for s, b in pairs)
    return yang / (len(pairs) * 2)


def _interaction_features(sipsin: dict, strength: dict, yongsin: dict,
                          yang_ratio: float) -> dict:
    g = sipsin["groups"]
    sc = strength["score"]

    def ratio(a, b):
        return round(a / (a + b), 4) if (a + b) > 0 else 0.5

    return {
        "식상관성비": ratio(g["식상"], g["관성"]),
        "재성x신강": round(g["재성"] * sc, 4),
        "관성x신강": round(g["관성"] * sc, 4),
        "식상x신강": round(g["식상"] * sc, 4),
        "인성식상비": ratio(g["인성"], g["식상"]),
        "용신강도": yongsin["strength_in_chart"],
        "양기x비겁": round(yang_ratio * g["비겁"], 4),
    }


# ── 메인 진입점 ──

def extract_features(year: int, month: int, day: int, hour=None) -> dict:
    """생년월일(시) → 사주 피처 벡터. 완전 결정적, JSON-serializable.

    hour=None이면 시주 슬롯을 제외하고 재정규화한다 (가짜 12시 주입 금지 —
    일주 산출용 lunar 호출만 12시 고정, 시주는 어떤 피처에도 안 들어감).
    """
    hour_known = hour is not None
    ba = _get_eight_char(year, month, day, hour if hour_known else 12)

    day_stem = _to_kr(ba.getDayGan())
    slots = _weighted_slots(ba, hour_known)

    sipsin = _sipsin_features(day_stem, slots)
    strength = _strength_features(day_stem, ba, slots, hour_known)
    elements = _element_features(day_stem, ba, slots, hour_known)
    yongsin = _yongsin_features(day_stem, strength["score"], elements["weighted"])
    gyeokguk = _gyeokguk_features(day_stem, ba, hour_known)
    yang_ratio = _yinyang_ratio(ba, hour_known)
    interactions = _interaction_features(sipsin, strength, yongsin, yang_ratio)

    pillars = {
        "년주": _to_kr(ba.getYearGan()) + _to_kr(ba.getYearZhi()),
        "월주": _to_kr(ba.getMonthGan()) + _to_kr(ba.getMonthZhi()),
        "일주": _to_kr(ba.getDayGan()) + _to_kr(ba.getDayZhi()),
    }
    if hour_known:
        pillars["시주"] = _to_kr(ba.getTimeGan()) + _to_kr(ba.getTimeZhi())

    degraded = [] if hour_known else [
        "sipsin", "strength", "yongsin", "yinyang", "elements", "interactions",
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "input": {"year": year, "month": month, "day": day,
                  "hour": hour if hour_known else None, "hour_known": hour_known},
        "pillars": pillars,
        "day_master": {"stem": day_stem, "element": STEM_ELEMENT[day_stem],
                       "polarity": STEM_POLARITY[day_stem]},
        "sipsin": sipsin,
        "strength": strength,
        "yongsin": yongsin,
        "gyeokguk": gyeokguk,
        "yinyang": {"yang_ratio": round(yang_ratio, 4)},
        "elements": elements,
        "interactions": interactions,
        "degraded_features": degraded,
    }


def extract_features_from_birth(birth_date: str, birth_time,
                                trust_default_noon: bool = False) -> dict:
    """DB 문자열 → extract_features 위임.

    birth_date: "YYYY-MM-DD"
    birth_time: "16" | "unknown" | "12" | None
    trust_default_noon: False면 birth_time=="12"를 미상으로 간주
      (비사주 트랙은 12가 하드코딩 기본값이라 실제 시간이 아닐 수 있음)
    """
    y, m, d = (int(p) for p in birth_date.split("-"))
    hour = None
    if birth_time not in (None, "", "unknown"):
        try:
            h = int(birth_time)
            if 0 <= h <= 23 and (trust_default_noon or h != 12):
                hour = h
        except (ValueError, TypeError):
            hour = None
    return extract_features(y, m, d, hour)


def flatten(features: dict) -> dict:
    """통계 하네스용 1-depth dict (ascii snake_case, categorical은 one-hot)"""
    f = features
    out = {}
    for name, v in f["sipsin"]["strength"].items():
        out[f"ss_{_SIPSIN_ASCII[name]}"] = v
    for name, v in f["sipsin"]["groups"].items():
        out[f"grp_{_GROUP_ASCII[name]}"] = v
    out["dominant_margin"] = f["sipsin"]["dominant_margin"]
    out["strength"] = f["strength"]["score"]
    out["deukryeong"] = f["strength"]["득령"]
    out["deukji"] = f["strength"]["득지"]
    out["deukse"] = f["strength"]["득세"]
    out["yongsin_degree"] = f["yongsin"]["degree"]
    out["yongsin_strength"] = f["yongsin"]["strength_in_chart"]
    for el in ELEMENTS:
        out[f"yongsin_el_{_EL_ASCII[el]}"] = 1.0 if f["yongsin"]["element"] == el else 0.0
        out[f"el_{_EL_ASCII[el]}"] = f["elements"]["weighted"][el]
        out[f"el_count_{_EL_ASCII[el]}"] = float(f["elements"]["counts"][el])
        out[f"day_el_{_EL_ASCII[el]}"] = 1.0 if f["day_master"]["element"] == el else 0.0
    for g in SIKSHIN_GROUPS:
        out[f"gyeokguk_grp_{_GROUP_ASCII[g]}"] = 1.0 if f["gyeokguk"]["group"] == g else 0.0
    out["el_entropy"] = f["elements"]["entropy"]
    out["yang_ratio"] = f["yinyang"]["yang_ratio"]
    out["day_polarity_yang"] = 1.0 if f["day_master"]["polarity"] == "양" else 0.0
    ix_ascii = {"식상관성비": "ix_siksang_gwanseong", "재성x신강": "ix_jae_x_strength",
                "관성x신강": "ix_gwan_x_strength", "식상x신강": "ix_siksang_x_strength",
                "인성식상비": "ix_in_siksang", "용신강도": "ix_yongsin_strength",
                "양기x비겁": "ix_yang_x_bigyeop"}
    for name, key in ix_ascii.items():
        out[key] = f["interactions"][name]
    out["hour_known"] = 1.0 if f["input"]["hour_known"] else 0.0
    return out


def sipsin_prior_delta(features: dict, scale: float = 1.0,
                       yongsin_boost: float = 0.0) -> dict:
    """십신 strength 가중합 × MAP_V2 → 9차원 delta.

    yongsin_boost: 용신 오행에 속한 십신의 delta 증폭 (기본 0 = off, 검증 전엔 끔)
    """
    from config import DIMENSIONS

    delta = {d: 0.0 for d in DIMENSIONS}
    day_stem = features["day_master"]["stem"]
    yongsin_el = features["yongsin"]["element"]

    for name, w in features["sipsin"]["strength"].items():
        if w == 0:
            continue
        boost = 1.0
        if yongsin_boost > 0:
            rel = _rel_elements(STEM_ELEMENT[day_stem])
            if rel[_GROUP_OF[name]] == yongsin_el:
                boost = 1.0 + yongsin_boost
        for dim, val in SIPSIN_FLAVOR_MAP_V2[name]["delta"].items():
            delta[dim] += val * w * scale * boost

    return {d: round(v, 4) for d, v in delta.items()}


def saju_prior_9d(features: dict, base: float = 0.5) -> dict:
    """delta를 [0,1] 프로필 공간으로: prior_d = clamp(base + delta_d)

    gated_blend가 survey와 같은 공간에서 섞을 수 있는 형태.
    """
    delta = sipsin_prior_delta(features)
    return {d: round(min(1.0, max(0.0, base + v)), 4) for d, v in delta.items()}
