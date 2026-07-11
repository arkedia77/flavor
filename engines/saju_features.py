"""사주 피처 추출 엔진 v2 — Leoflavor v0.2 검증 게이트용

lunar_python 기반 만세력에서 통계 검증 가능한 결정적 피처 벡터를 추출한다.
- 십신 강도 (지장간·궁성 가중), 신강약 연속 점수, 억부용신, 격국, 음양, 오행
- 모든 출력은 JSON-serializable, 동일 입력 → 동일 출력 (결정적)
- 시간 미상(hour=None) 시 시주 슬롯을 제외하고 재정규화 (12시 가짜 주입 금지)
- 입력 경로 2개: 생년월일시(extract_features) / 간지 직접(extract_features_from_pillars
  — 고전 명식 정답지 검증용, 지장간은 lunar와 동일한 LunarUtil.ZHI_HIDE_GAN 사용)
- params로 가중치 체계를 교체 가능 (민감도 분석용) — 기본값이 프로덕션 공식

이 모듈의 피처는 추천에 직접 반영되지 않는다. config/saju_gate.json의
가중치가 검증 게이트(scripts/validate_saju_signal.py) 통과로 개방되기 전까지
sipsin_prior_delta / saju_prior_9d는 저장·검증용으로만 쓰인다.

주의: 오행 count 회귀는 2026-03-12에 신호 없음 판정(CV R²=-0.222).
elements.counts는 그 실패 베이스라인과의 대조를 위해 유지하는 피처다.
"""

import math

from lunar_python import Solar
from lunar_python.util import LunarUtil

from engines.sipsin import (
    STEM_ELEMENT, STEM_POLARITY, BRANCH_ELEMENT, BRANCH_POLARITY,
    PRODUCES, OVERCOMES, SIPSIN_NAMES, _to_kr,
)

SCHEMA_VERSION = "sf-3"  # sf-3: 별격 감지 + 록겁(건록/양인) 격명 + 별격 순세 용신 (2026-07-11)

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

# 지지 → 지장간 (lunar EightChar가 쓰는 것과 동일 테이블, 한글 변환)
# 순서: index 0 = 본기, 이후 세력 내림차순
HIDDEN_STEMS_KR = {
    _to_kr(zhi): [_to_kr(g) for g in gans]
    for zhi, gans in LunarUtil.ZHI_HIDE_GAN.items()
}

# ── 기본 파라미터 (프로덕션 공식 = sf-1) ──
# 민감도 분석에서 params 인자로 교체 가능. 기본값 변경은 SCHEMA_VERSION 변경 사항.
DEFAULT_PARAMS = {
    # 궁성(위치) 가중 — 월지 본기가 사령부라는 자평 원칙 반영
    "palace_weights": {
        "년간": 1.0, "월간": 1.2, "시간": 1.0,
        "년지": 1.0, "월지": 2.5, "일지": 1.5, "시지": 1.0,
    },
    # 지장간 가중 — index 0 = 본기 (길이별)
    "hidden_weights_by_len": {1: [1.0], 2: [0.7, 0.3], 3: [0.6, 0.3, 0.1]},
    # 신강약: 슬롯이 일간을 돕는 정도
    "support_bigyeop": 1.0,
    "support_inseong": 0.8,
    # 균등분포 기대값 = 0.2*(비겁+인성 support) → 중화점
    "strength_neutral": 0.36,
    "strength_strong": 0.42,   # label용
    "strength_weak": 0.30,
    # 억부용신 v2 (원인 기반)
    "yongsin_taewang": 0.55,   # 이 이상이면 태왕 → 극 불가, 설기(식상)
    "yongsin_min_w": 0.05,     # 용신 후보 오행의 최소 유력 기준 (가중 비중)
    # 별격(외격) 감지 v1 (sf-3) — 적천수천미 별격 115건 캘리브레이션 (2026-07-11)
    # 홀짝 분할 교차평가로 강건성 확인. 상세: reports/theory/VERDICT_2026-07-11_byeolgyeok.md
    "special_hap_min_w": 0.15,        # 합화: 화신 최소 가중 비중
    "special_hap_score_max": 0.40,    # 합화: 일간 신강 상한 (강하면 합화 불성립)
    "special_yanggi_min_chars": 3,    # 양기성상: 두 오행 각각 최소 글자 수
    "special_jw_score": 0.60,         # 전왕: 신강 점수 하한
    "special_jw_gwan_max": 0.14,      # 전왕: 관성 비중 상한 (관살 무력 요건)
    "special_jong_score": 0.26,       # 종격: 신강 점수 상한
    "special_jong_ins_max": 0.10,     # 종격: 인성 비중 상한 (인성 있으면 종하지 않음)
    "special_jong_bg_max": 0.20,      # 종격: 비겁 비중 상한
    "special_jong_deukji_max": 0.50,  # 종격: 득지(통근) 상한
    "special_jong_dom_min": 0.35,     # 종격: 지배 세력 최소 비중
}

# 하위 호환 상수 (기존 import 대응)
PALACE_WEIGHTS = DEFAULT_PARAMS["palace_weights"]
HIDDEN_WEIGHTS_BY_LEN = DEFAULT_PARAMS["hidden_weights_by_len"]
STRENGTH_NEUTRAL = DEFAULT_PARAMS["strength_neutral"]
STRENGTH_STRONG = DEFAULT_PARAMS["strength_strong"]
STRENGTH_WEAK = DEFAULT_PARAMS["strength_weak"]


# ── 십신 → 9차원 prior 가설 테이블 v2.1 ──
# 근거 감사 (2026-07-10, reports/theory/EVIDENCE_AUDIT_2026-07-10.md):
#   기존 "십신→MBTI 5쌍 p<0.05" 인용은 실존 논문 미확인 → 전량 강등.
#   evidence "실무수렴" = 독립 실무 소스 3개+ 수렴 아키타입 (논문 근거 아님)
#   evidence "실무단독" = 소스 수렴 약함/양면적
#   rationale 안 (추정)은 어떤 소스에도 근거 없는 speculative delta — urban 전량 해당.
# 순수 데이터 테이블 — 방향성 가설이며, 최종 타당성은 검증 게이트가 판정.
SIPSIN_FLAVOR_MAP_V2 = {
    "상관": {"delta": {"maximalist": +0.08, "adventurous": +0.08, "social": +0.04,
                       "aesthetic": +0.05, "comfort": -0.05},
             "rationale": "다재다능/호기심/과시욕/실험적 스타일 수렴. social은 양면적"
                          "(사교적 vs 관계훼손 서술 공존)이라 진폭 축소",
             "evidence": "실무수렴"},
    "정관": {"delta": {"urban": +0.06, "comfort": +0.05, "aesthetic": +0.04,
                       "maximalist": -0.06, "adventurous": -0.05},
             "rationale": "원칙/명예/계획성/보수 수렴 → comfort+/maximalist-/adventurous-."
                          " urban+/aesthetic+는 (추정)",
             "evidence": "실무수렴"},
    "정재": {"delta": {"comfort": +0.08, "budget": -0.08, "adventurous": -0.06,
                       "social": -0.04, "urban": +0.03},
             "rationale": "성실/절약/보수적 재정관리 수렴 → comfort+/budget-/adventurous-."
                          " social-/urban+는 (추정)",
             "evidence": "실무수렴"},
    "편재": {"delta": {"adventurous": +0.08, "social": +0.07, "urban": +0.06,
                       "budget": +0.06, "comfort": -0.04},
             "rationale": "활동적/기회포착/큰 씀씀이/다정다감 수렴 → adv+/soc+/budget+."
                          " urban+/comfort-는 (추정)",
             "evidence": "실무수렴"},
    "식신": {"delta": {"aesthetic": +0.07, "comfort": +0.06, "bitter": +0.05},
             "rationale": "미식가/의식주/풍류 수렴 → aesthetic+/comfort+. bitter+는"
                          " 미식→깊은맛 (추정). 구버전 social-/energetic-는 실무 소스와"
                          " 정면 모순(사교 능함·활동력)이라 삭제 (감사 2026-07-10)",
             "evidence": "실무수렴"},
    "비견": {"delta": {"adventurous": +0.05, "comfort": +0.03, "social": -0.05},
             "rationale": "독립/주체성/자존 수렴. social 방향은 소스 불일치"
                          "(원만 vs 지배성) — 군중 비의존 해석 채택, 재검토 대상",
             "evidence": "실무단독"},
    "겁재": {"delta": {"social": +0.07, "budget": +0.06, "maximalist": +0.06,
                       "energetic": +0.05, "urban": +0.05},
             "rationale": "경쟁심/승부욕/충동 소비 수렴 → budget+/maximalist+."
                          " urban+는 (추정)",
             "evidence": "실무수렴"},
    "편관": {"delta": {"energetic": +0.08, "adventurous": +0.06, "maximalist": +0.05,
                       "urban": +0.04, "comfort": -0.06},
             "rationale": "카리스마/인내/위험감수 수렴 → energetic+/adventurous+."
                          " urban+는 (추정)",
             "evidence": "실무수렴"},
    "편인": {"delta": {"adventurous": +0.07, "bitter": +0.06, "aesthetic": +0.04,
                       "social": -0.06, "urban": -0.03},
             "rationale": "비주류/특수분야 몰입/직관 수렴 → adventurous+/social-."
                          " bitter+/urban-는 (추정)",
             "evidence": "실무수렴"},
    "정인": {"delta": {"comfort": +0.07, "bitter": +0.04, "aesthetic": +0.03,
                       "maximalist": -0.05, "budget": -0.03},
             "rationale": "학문/수용/안정/보수 수렴 → comfort+/maximalist-."
                          " bitter+는 (추정)",
             "evidence": "실무수렴"},
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

# ── 별격(외격) 상수 ──
# 천간합 (canonical 순서 = 간지 순서 빠른 쪽 먼저) → 화신 오행
_HAP_PAIRS = {("갑", "기"): "토", ("을", "경"): "금", ("병", "신"): "수",
              ("정", "임"): "목", ("무", "계"): "화"}
_HANJA_STEM = {"갑": "甲", "을": "乙", "병": "丙", "정": "丁", "무": "戊",
               "기": "己", "경": "庚", "신": "辛", "임": "壬", "계": "癸"}
_HANJA_EL = {"목": "木", "화": "火", "토": "土", "금": "金", "수": "水"}
# 일행득기격 명칭 (일간 오행별) — 정답지 표기 준수 (곡직인수격)
_JEONWANG_NAME = {"목": "곡직인수격", "화": "염상격", "토": "가색격",
                  "금": "종혁격", "수": "윤하격"}
# 양기성상격 국 명칭 — 정답지 표기(한자) 준수. 인성국은 골든 부재 + 전왕과 중복이라 제외
_YANGGI_GUK = {"식상": "食傷局", "재성": "財局", "관성": "官局"}


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


# ── 명식 정규화 (chart dict) ──
# chart = {
#   "day_stem": "무",
#   "stems": [("년간","정"), ("월간","갑"), ("시간","경")?],   # 일간 제외
#   "branches": [("년지","사",[지장간...]), ..., ("시지",...)?],  # [본기, ...]
#   "pillars": {"년주":"정사", ...},
#   "hour_known": bool,
# }

def _build_chart_from_date(year, month, day, hour):
    hour_known = hour is not None
    solar = Solar.fromYmdHms(year, month, day, hour if hour_known else 12, 0, 0)
    ba = solar.getLunar().getEightChar()

    stems = [("년간", _to_kr(ba.getYearGan())), ("월간", _to_kr(ba.getMonthGan()))]
    branches = [
        ("년지", _to_kr(ba.getYearZhi()), [_to_kr(g) for g in ba.getYearHideGan()]),
        ("월지", _to_kr(ba.getMonthZhi()), [_to_kr(g) for g in ba.getMonthHideGan()]),
        ("일지", _to_kr(ba.getDayZhi()), [_to_kr(g) for g in ba.getDayHideGan()]),
    ]
    pillars = {
        "년주": stems[0][1] + branches[0][1],
        "월주": stems[1][1] + branches[1][1],
        "일주": _to_kr(ba.getDayGan()) + branches[2][1],
    }
    if hour_known:
        stems.append(("시간", _to_kr(ba.getTimeGan())))
        tz = _to_kr(ba.getTimeZhi())
        branches.append(("시지", tz, [_to_kr(g) for g in ba.getTimeHideGan()]))
        pillars["시주"] = stems[2][1] + tz

    return {"day_stem": _to_kr(ba.getDayGan()), "stems": stems,
            "branches": branches, "pillars": pillars, "hour_known": hour_known}


def _build_chart_from_pillars(pillars: dict):
    """간지 직접 입력 — {"년주":"정사","월주":"갑진","일주":"무술","시주":"경신"(선택)}

    고전 명식 검증용. 지장간은 lunar와 동일한 HIDDEN_STEMS_KR 사용.
    """
    def split(p):
        if not p or len(p) != 2:
            raise ValueError(f"간지 형식 오류: {p!r} (예: '정사')")
        s, b = p[0], p[1]
        if s not in STEM_ELEMENT or b not in BRANCH_ELEMENT:
            raise ValueError(f"알 수 없는 간지: {p!r}")
        return s, b

    ys, yb = split(pillars["년주"])
    ms, mb = split(pillars["월주"])
    ds, db = split(pillars["일주"])
    hour_known = bool(pillars.get("시주"))

    stems = [("년간", ys), ("월간", ms)]
    branches = [
        ("년지", yb, HIDDEN_STEMS_KR[yb]),
        ("월지", mb, HIDDEN_STEMS_KR[mb]),
        ("일지", db, HIDDEN_STEMS_KR[db]),
    ]
    out_pillars = {"년주": pillars["년주"], "월주": pillars["월주"], "일주": pillars["일주"]}
    if hour_known:
        hs, hb = split(pillars["시주"])
        stems.append(("시간", hs))
        branches.append(("시지", hb, HIDDEN_STEMS_KR[hb]))
        out_pillars["시주"] = pillars["시주"]

    return {"day_stem": ds, "stems": stems, "branches": branches,
            "pillars": out_pillars, "hour_known": hour_known}


def _weighted_slots(chart, params):
    """명식 → [(천간글자, weight, 위치태그)] 전개. 일간은 기준점이므로 제외."""
    pw = params["palace_weights"]
    hw = params["hidden_weights_by_len"]
    slots = []
    for tag, stem in chart["stems"]:
        slots.append((stem, pw[tag], tag))
    for tag, _branch, hidden in chart["branches"]:
        for stem, w in zip(hidden, hw[len(hidden)]):
            slots.append((stem, pw[tag] * w, tag))
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


def _strength_features(chart, slots, params) -> dict:
    day_el = STEM_ELEMENT[chart["day_stem"]]
    rel = _rel_elements(day_el)

    def support(el: str) -> float:
        if el == rel["비겁"]:
            return params["support_bigyeop"]
        if el == rel["인성"]:
            return params["support_inseong"]
        return 0.0

    total = sum(w for _, w, _ in slots)
    score = sum(w * support(STEM_ELEMENT[stem]) for stem, w, _ in slots) / total

    # 득령: 월지 본기
    month_hidden = next(h for tag, _b, h in chart["branches"] if tag == "월지")
    m_el = STEM_ELEMENT[month_hidden[0]]
    deukryeong = 1.0 if m_el == rel["비겁"] else (0.75 if m_el == rel["인성"] else 0.0)

    # 득지: 지지 통근 (지장간에 일간 오행 존재), 일지 1.5배 가중
    root_w, root_total = 0.0, 0.0
    for tag, _b, hidden in chart["branches"]:
        w = 1.5 if tag == "일지" else 1.0
        root_total += w
        if any(STEM_ELEMENT[s] == day_el for s in hidden):
            root_w += w
    deukji = root_w / root_total

    # 득세: 타 천간 중 비겁/인성 지지율
    other = [s for _tag, s in chart["stems"]]
    deukse = sum(support(STEM_ELEMENT[s]) for s in other) / len(other)

    if score > params["strength_strong"]:
        label = "신강"
    elif score < params["strength_weak"]:
        label = "신약"
    else:
        label = "중화"

    return {
        "score": round(score, 4), "label": label,
        "득령": round(deukryeong, 4), "득지": round(deukji, 4), "득세": round(deukse, 4),
    }


def _yongsin_features(day_stem: str, strength_score: float, elements_weighted: dict,
                      sipsin_groups: dict, params) -> dict:
    """억부용신 v2 — 원인 기반 결정적 규칙 (sf-2, 2026-07-11).

    적천수천미 393 정격 대조에서 v1(유력한 쪽) 37.4% → v2 47.6% (∪희신 74.3%).
    고전 규칙 근거 (reports/theory/SCHOOL_PARAMS_2026-07-10.md):
      신약 — 병(압박 세력 최강자) 기반: 재다신약→비겁, 관살/식상 과다→인성
      신강 — 인다신강→재성(제인), 태왕→식상(설기, 극하면 반발),
             비겁왕→관성 (단 관성 무력 시 식상→재성 순 대체)
    조후용신은 유파 이견이 커서 제외 — method 필드로 향후 확장.
    """
    rel = _rel_elements(STEM_ELEMENT[day_stem])
    neutral = params["strength_neutral"]
    g = sipsin_groups

    if strength_score < neutral:
        # 병 = 압박 세력 최강자 (동률 시 관성 > 재성 > 식상 순 — 극신 우선)
        opp_order = ["관성", "재성", "식상"]
        strongest = max(opp_order, key=lambda k: (g[k], -opp_order.index(k)))
        if strongest == "재성":
            yongsin, huisin = rel["비겁"], rel["인성"]   # 재다신약 → 비겁
        else:
            yongsin, huisin = rel["인성"], rel["비겁"]   # 관살/식상 과다 → 인성
    elif g["인성"] > g["비겁"]:
        yongsin, huisin = rel["재성"], rel["식상"]       # 인다신강 → 재성 제인
    elif strength_score >= params["yongsin_taewang"]:
        yongsin, huisin = rel["식상"], rel["재성"]       # 태왕 → 설기
    elif elements_weighted[rel["관성"]] >= params["yongsin_min_w"]:
        yongsin, huisin = rel["관성"], rel["재성"]       # 비겁왕 → 관성 (재생관)
    elif elements_weighted[rel["식상"]] >= params["yongsin_min_w"]:
        yongsin, huisin = rel["식상"], rel["재성"]       # 관성 무력 → 식상
    else:
        yongsin, huisin = rel["재성"], rel["식상"]       # 둘 다 무력 → 재성

    degree = min(1.0, abs(strength_score - neutral) / neutral)
    return {
        "method": "억부-원인기반", "element": yongsin, "희신": huisin,
        "degree": round(degree, 4),
        "strength_in_chart": round(elements_weighted[yongsin], 4),
    }


def _gyeokguk_features(chart) -> dict:
    """격국 — 월지 본기 기준 + 투간 보정 + 록겁(건록/양인) 매핑.

    월지 본기가 비겁이면 십신격을 취하지 않고 건록격/양인격 (자평 원칙,
    sf-3 — 적천수천미 대조에서 록겁월 77건 중 무조건 매핑 57 > 투간 우선 54 > 기존 6).
    그 외: 월지 지장간 중 천간(년간/월간/시간)에 투출한 글자가 있으면 우선
    (본기 투출 > 중기 > 여기), 미투출 시 본기.
    시간 미상이면 시간(時干)은 투간 후보에서 제외 (가짜 12시 누출 금지).
    """
    month_hidden = next(h for tag, _b, h in chart["branches"] if tag == "월지")
    ss_bongi = _sipsin_of(chart["day_stem"], month_hidden[0])
    if ss_bongi == "비견":
        return {"name": "건록격", "group": "비겁", "tugan": False}
    if ss_bongi == "겁재":
        # 양인격은 양간 전용 — 음간 겁재월은 건록격으로 (골든 라벨 전례 없음)
        name = "양인격" if STEM_POLARITY[chart["day_stem"]] == "양" else "건록격"
        return {"name": name, "group": "비겁", "tugan": False}

    visible = {s for _tag, s in chart["stems"]}
    chosen, tugan = month_hidden[0], False
    for h in month_hidden:
        if h in visible:
            chosen, tugan = h, True
            break

    ss = _sipsin_of(chart["day_stem"], chosen)
    return {"name": f"{ss}격", "group": _GROUP_OF[ss], "tugan": tugan}


def _special_gyeokguk(chart, sipsin_groups, strength, elements, p):
    """별격(외격) 감지 — 해당 없으면 None (sf-3, 2026-07-11).

    검사 순서: 합화 → 양기성상 → 전왕 → 종격 (구체 조건 우선).
    임계값은 적천수천미 별격 115건 + 정격 391건으로 캘리브레이션 (in-sample,
    홀짝 분할 교차평가로 강건성만 확인 — VERDICT_2026-07-11_byeolgyeok.md).
    반환 dict의 sunse_element는 순세 용신(왕신 따름) 재정의에 쓰인다.
    """
    day_stem = chart["day_stem"]
    day_el = STEM_ELEMENT[day_stem]
    rel = _rel_elements(day_el)
    groups = sipsin_groups
    score = strength["score"]
    weighted = elements["weighted"]
    counts = elements["counts"]
    month_hidden = next(h for tag, _b, h in chart["branches"] if tag == "월지")

    # 1) 합화격: 일간이 월간/시간과 천간합 + 화신이 월지 지장간에 존재(득령)
    #    + 일간 약 + 화신 유력. (통근 배제 조건은 골든 8/10이 위반해 미채용)
    adjacent = {s for tag, s in chart["stems"] if tag in ("월간", "시간")}
    for (a, b), hua in _HAP_PAIRS.items():
        partner = b if day_stem == a else (a if day_stem == b else None)
        if partner is None:
            continue
        if (partner in adjacent
                and any(STEM_ELEMENT[s] == hua for s in month_hidden)
                and score <= p["special_hap_score_max"]
                and weighted[hua] >= p["special_hap_min_w"]):
            name = f"합화격 {_HANJA_STEM[a]}{_HANJA_STEM[b]}合{_HANJA_EL[hua]}"
            return {"name": name, "group": "별격", "subtype": "합화",
                    "tugan": False, "sunse_element": hua}

    # 2) 양기성상격: 팔자가 두 오행으로만 구성 + 양쪽 균형
    present = [(el, v) for el, v in counts.items() if v > 0]
    if (len(present) == 2
            and min(v for _el, v in present) >= p["special_yanggi_min_chars"]):
        other = next((el for el, _v in present if el != day_el), None)
        if other:
            grp = next(g for g, el in rel.items() if el == other)
            if grp in _YANGGI_GUK:
                return {"name": f"양기성상격 {_YANGGI_GUK[grp]}", "group": "별격",
                        "subtype": "양기성상", "tugan": False, "sunse_element": other}

    # 3) 전왕격(일행득기/종강): 극신강 + 관살 무력 + 득령
    m_el = STEM_ELEMENT[month_hidden[0]]
    deukryeong = m_el in (rel["비겁"], rel["인성"])
    if (score >= p["special_jw_score"]
            and groups["관성"] <= p["special_jw_gwan_max"] and deukryeong):
        sub = "종강격" if groups["인성"] > groups["비겁"] else _JEONWANG_NAME[day_el]
        return {"name": f"전왕격 {sub}", "group": "별격", "subtype": "전왕",
                "tugan": False, "sunse_element": day_el}

    # 4) 종격: 극신약 + 인성·비겁 무력 + 통근 약함 + 지배 세력 존재
    if (score <= p["special_jong_score"]
            and groups["인성"] <= p["special_jong_ins_max"]
            and groups["비겁"] <= p["special_jong_bg_max"]
            and strength["득지"] <= p["special_jong_deukji_max"]):
        opp = {k: groups[k] for k in ("식상", "재성", "관성")}
        dom = max(opp, key=opp.get)
        if opp[dom] >= p["special_jong_dom_min"]:
            sub = {"식상": "종아격", "재성": "종재격", "관성": "종관격"}[dom]
            return {"name": f"종격 {sub}", "group": "별격", "subtype": "종격",
                    "tugan": False, "sunse_element": rel[dom]}

    return None


def _element_features(chart, slots) -> dict:
    # raw counts: 천간 + 지지 대표오행 (v0.1 실패 베이스라인 대조군)
    counts = {el: 0 for el in ELEMENTS}
    counts[STEM_ELEMENT[chart["day_stem"]]] += 1
    for _tag, s in chart["stems"]:
        counts[STEM_ELEMENT[s]] += 1
    for _tag, b, _h in chart["branches"]:
        counts[BRANCH_ELEMENT[b]] += 1

    # 가중 분포: 십신 슬롯 + 일간(1.0) 포함
    weighted = {el: 0.0 for el in ELEMENTS}
    weighted[STEM_ELEMENT[chart["day_stem"]]] += 1.0
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


def _yinyang_ratio(chart) -> float:
    yang = STEM_POLARITY[chart["day_stem"]] == "양"
    n = 1
    for _tag, s in chart["stems"]:
        yang += STEM_POLARITY[s] == "양"
        n += 1
    for _tag, b, _h in chart["branches"]:
        yang += BRANCH_POLARITY[b] == "양"
        n += 1
    return yang / n


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


# ── 공통 조립 ──

def _features_from_chart(chart, input_info, params=None) -> dict:
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update(params)

    day_stem = chart["day_stem"]
    slots = _weighted_slots(chart, p)

    sipsin = _sipsin_features(day_stem, slots)
    strength = _strength_features(chart, slots, p)
    elements = _element_features(chart, slots)
    yongsin = _yongsin_features(day_stem, strength["score"], elements["weighted"],
                                sipsin["groups"], p)
    gyeokguk = _gyeokguk_features(chart)

    # 별격 감지 시 격국 교체 + 용신을 순세(왕신 따름)로 재정의.
    # 골든 별격 115건에서 순세∈(용신∪희신) 95.7% vs 억부 34.8% (VERDICT 참조)
    special = _special_gyeokguk(chart, sipsin["groups"], strength, elements, p)
    if special:
        special["normal_name"] = gyeokguk["name"]
        gyeokguk = special
        sunse = special["sunse_element"]
        yongsin = {
            "method": "순세-별격", "element": sunse,
            "희신": next(k for k, v in PRODUCES.items() if v == sunse),  # 용신 생조자
            "degree": round(min(1.0, abs(strength["score"] - p["strength_neutral"])
                                / p["strength_neutral"]), 4),
            "strength_in_chart": round(elements["weighted"][sunse], 4),
        }

    yang_ratio = _yinyang_ratio(chart)
    interactions = _interaction_features(sipsin, strength, yongsin, yang_ratio)

    degraded = [] if chart["hour_known"] else [
        "sipsin", "strength", "yongsin", "yinyang", "elements", "interactions",
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "input": input_info,
        "pillars": chart["pillars"],
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


# ── 메인 진입점 ──

def extract_features(year: int, month: int, day: int, hour=None, params=None) -> dict:
    """생년월일(시) → 사주 피처 벡터. 완전 결정적, JSON-serializable.

    hour=None이면 시주 슬롯을 제외하고 재정규화한다 (가짜 12시 주입 금지 —
    일주 산출용 lunar 호출만 12시 고정, 시주는 어떤 피처에도 안 들어감).
    """
    hour_known = hour is not None
    chart = _build_chart_from_date(year, month, day, hour)
    return _features_from_chart(chart, {
        "year": year, "month": month, "day": day,
        "hour": hour if hour_known else None, "hour_known": hour_known,
    }, params)


def extract_features_from_pillars(pillars: dict, params=None) -> dict:
    """간지 직접 입력 → 사주 피처 벡터 (고전 명식 정답지 검증용).

    pillars: {"년주":"정사","월주":"갑진","일주":"무술","시주":"경신"(선택)}
    """
    chart = _build_chart_from_pillars(pillars)
    return _features_from_chart(chart, {
        "pillars_direct": True, "hour_known": chart["hour_known"],
    }, params)


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
    out["gyeokguk_special"] = 1.0 if f["gyeokguk"]["group"] == "별격" else 0.0
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
