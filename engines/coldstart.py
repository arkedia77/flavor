"""콜드스타트 카테고리 취향 예측 — 파일럿 A (커피 쓴맛형/산미형)

근거: fableself 리서치 (2026-07-12,
agent-comm/projects/fableself/exchange/flavor-taste-research-v01.md).
자체 설문·데이터 0에서 base rate 초과를 노리는 하이브리드 콜드스타트:
  성별×연령 코호트 사전확률(문헌 계수) × seed 자연어 우도(LLM 주입 가능) → 베이지안.

정직성 (효과크기):
  단일 신호→취향 상관은 전부 약함(성격→장르 r≈0.06, 개별 0.1~0.2). 실전 lift는
  결합에서 나온다. 아래 계수는 fitted 값이 아니라 문헌 방향성 prior다.
  - Barragán 2018 (18-80): 연령↑ → 쓴맛 선호↑, 단맛↓
  - Frontiers 2024: 여성 → 단·산미 / 남성 → 쓴·짠
  - PTC 테이스터 여성 72% > 남성 64% (쓴맛 민감 → 쓴맛 회피 경향)
  - 사주·별자리·출생계절 = 외부 예측력 ≈ 0 → 미사용. 생년월일은 연령 환원분만 투입.

engines/는 Flask 무의존. LLM은 llm_infer 콜러블로 주입(미지정 시 오프라인 키워드
휴리스틱). 실제 LLM(Claude) 연결은 자연어 seed 수집이 생긴 뒤의 확장 지점이다.
"""

# 커피 타입 축: 쓴맛형(bitter) vs 산미형(acidic/sweet-mild)
TYPE_KR = {"bitter": "쓴맛형", "acidic": "산미형"}

# ── 코호트 사전확률 계수 (P(bitter) 기준, 방향성 prior) ──
_AGE_PIVOT = 40          # 기준 연령 (이 나이에서 연령 효과 0)
_AGE_SLOPE = 0.006       # 1세당 쓴맛 선호 +0.6%p (18→80에서 약 ±0.13)
_GENDER_OFFSET_MALE = 0.08
_GENDER_OFFSET_FEMALE = -0.08
_P_MIN, _P_MAX = 0.15, 0.85  # 코호트만으로는 확신 금지

_MALE_TOKENS = {"male", "m", "man", "남", "남성", "남자"}
_FEMALE_TOKENS = {"female", "f", "woman", "여", "여성", "여자"}

# seed 키워드 휴리스틱 (오프라인 기본 — LLM 미주입 시). 우도 곱에 쓰는 근사.
_BITTER_KW = ["아메리카노", "에스프레소", "핸드드립", "블랙", "진하", "다크",
              "쓴", "콜드브루", "드립", "룽고"]
_ACIDIC_KW = ["라떼", "바닐라", "카라멜", "달달", "달콤", "시럽", "산미", "프룻",
              "플랫화이트", "플랫 화이트", "오트", "연하"]

# 커피 풀 아이템 → 타입 라벨 (recommend_coffee 분기 의도 기준).
# 애매한 것은 "mixed" — 엄격 일치도 지표에서 제외.
COFFEE_ITEM_TYPE = {
    "스페셜티 싱글오리진 핸드드립": "bitter",
    "에스프레소·아이스 아메리카노": "bitter",
    "스페셜티 콜드브루·블랙워터": "bitter",
    "따뜻한 아메리카노·단골 블렌드": "bitter",
    "카페라떼·바닐라라떼": "acidic",
    "달달한 라떼·플랫화이트": "acidic",
    "오트밀크 라떼·콜드브루": "acidic",
    "아이스 라떼·아메리카노": "mixed",  # 라떼+아메리카노 혼재
}


def _norm_gender(gender) -> str:
    g = str(gender).strip().lower()
    if g in _MALE_TOKENS:
        return "male"
    if g in _FEMALE_TOKENS:
        return "female"
    return "unknown"


def _clamp(v, lo=_P_MIN, hi=_P_MAX):
    return max(lo, min(hi, v))


def cohort_bitter_prior(age, gender) -> float:
    """(연령, 성별) → P(쓴맛형) 사전확률. 결정적. 문헌 방향성 prior."""
    p = 0.50
    if age is not None:
        p += _AGE_SLOPE * (age - _AGE_PIVOT)
    g = _norm_gender(gender)
    if g == "male":
        p += _GENDER_OFFSET_MALE
    elif g == "female":
        p += _GENDER_OFFSET_FEMALE
    return _clamp(p)


def _keyword_likelihood(seed_text: str):
    """seed 자연어 → (L_bitter, L_acidic) 우도 근사. 매칭 없으면 (1,1)=무정보."""
    t = str(seed_text).lower()
    nb = sum(1 for kw in _BITTER_KW if kw in t)
    na = sum(1 for kw in _ACIDIC_KW if kw in t)
    # 매칭당 우도비 1.6배 (약한 신호 — 과신 방지)
    return 1.6 ** nb, 1.6 ** na


def coffee_item_type(item: str) -> str:
    """커피 풀 아이템명 → 'bitter'|'acidic'|'mixed'|'unknown'"""
    return COFFEE_ITEM_TYPE.get(item, "unknown")


def predict_coffee_type(age, gender, seeds=None, llm_infer=None) -> dict:
    """(연령, 성별, seed들) → 커피 타입 예측. 결정적(llm_infer 미주입 시).

    seeds: 자연어 seed 리스트 (예: ["아메리카노 진하게"]). 없으면 코호트만.
    llm_infer: seed_text -> {"bitter": Lb, "acidic": La} 우도 콜러블 (선택).
               미지정 시 오프라인 키워드 휴리스틱 사용.
    """
    prior_b = cohort_bitter_prior(age, gender)
    lb, la = 1.0, 1.0
    for s in (seeds or []):
        if not s:
            continue
        if llm_infer is not None:
            l = llm_infer(s) or {}
            lb *= max(1e-6, float(l.get("bitter", 1.0)))
            la *= max(1e-6, float(l.get("acidic", 1.0)))
        else:
            kb, ka = _keyword_likelihood(s)
            lb *= kb
            la *= ka

    denom = prior_b * lb + (1.0 - prior_b) * la
    post_b = (prior_b * lb) / denom if denom > 0 else prior_b
    post_b = _clamp(post_b, 0.01, 0.99)
    typ = "bitter" if post_b >= 0.5 else "acidic"
    return {
        "type": typ,
        "type_kr": TYPE_KR[typ],
        "p_bitter": round(post_b, 3),
        "prior_bitter": round(prior_b, 3),
        "method": "cohort+seed" if (seeds and any(seeds)) else "cohort",
        "used_seeds": [s for s in (seeds or []) if s],
    }


def age_from_birth_year(birth_year: int, reference_year: int) -> int:
    return reference_year - birth_year
