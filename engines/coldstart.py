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

import json

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


# ── 랜덤 노출 arm (측정 무교란화) ────────────────────────────────────
# fableself 점검 Q2: 노출이 비랜덤(9차원 규칙이 아이템 선택)이면 concordance lift가
# 셀렉션 바이어스로 교란된다 — match 셀에 "시스템이 원래 잘 서빙하던 유저×아이템"이
# 몰려 lift 과대/과소. 소급 재계산은 로깅 문제만 풀 뿐 배정 교란은 못 푼다.
# 유일한 무교란 추정치 = 노출의 일부를 풀 내 무작위로 서빙하는 랜덤 arm. 비용 ≈ 0.
# 단 랜덤 배정은 소급 불가 → 리셋 순간부터 켜야 한다. 게이트: config/coldstart_arm.json.

def apply_random_arm(results: dict, config: dict, rng) -> dict:
    """콜드스타트 랜덤 노출 arm. results를 변형하지 않고 (교체·태그된) 새 dict 반환.

    OFF(config 없음/enabled=False/random_frac<=0)면 results를 **그대로** 반환(완전 항등,
    노출·저장 무변경 — 사주/학습 게이트와 동일 fail-safe).
    ON이면 config['domains'] 중 results에 있는 도메인마다:
      rng.random() < random_frac → 풀(DOMAIN_POOL)에서 무작위 아이템 서빙, _arm='random'
      아니면 규칙 픽 유지, _arm='rule'
    _arm 태그가 results_json에 저장되어 lift 분석이 랜덤 arm만 골라 무교란 추정 가능.
    _rule_item = 랜덤일 때 규칙이 원래 고른 아이템(감사용).

    rng: random.random()/random.choice() 인터페이스 (라이브=random 모듈, 테스트=Random(seed)).
    """
    if not config or not config.get("enabled") or float(config.get("random_frac", 0.0)) <= 0.0:
        return results
    from engines.domains import DOMAIN_POOL

    frac = float(config["random_frac"])
    out = dict(results)
    for domain in (config.get("domains") or []):
        rec = out.get(domain)
        if not isinstance(rec, dict):
            continue
        pool = DOMAIN_POOL.get(domain) or []
        if pool and rng.random() < frac:
            pick = dict(rng.choice(pool))
            pick["_arm"] = "random"
            pick["_rule_item"] = rec.get("item")
            out[domain] = pick
        else:
            new = dict(rec)
            new["_arm"] = "rule"
            out[domain] = new
    return out


# ── LLM 우도 인터페이스 (seed 자연어 → bitter/acidic 우도) ────────────
# predict_coffee_type(..., llm_infer=<콜러블>)에 주입하는 어댑터. 자연어 seed 수집이
# 라이브가 된 뒤의 확장 지점 — 그 전까지 predict는 오프라인 키워드 휴리스틱을 쓴다.
# 키워드 이분 매칭보다 강하고(동의어·신조어 흡수) 풀-LLM보다 쌈(단문 1콜).
# 총 우도비는 캡(seed 과신 방지, fableself 점검 Q3의 곱셈 스태킹 함정 대응).

LLM_LIKELIHOOD_PROMPT = """\
너는 커피 취향 분류기다. 사용자가 커피에 대해 적은 한 줄(seed)을 읽고,
이 사람이 '쓴맛·진한 블랙 커피(bitter)'를 좋아할 가능성 대 '부드러운·달콤한 커피
(acidic/sweet-mild)'를 좋아할 가능성의 우도비를 매겨라.
seed가 취향 정보를 거의 안 주면 1.0(무정보)에 가깝게.
출력은 JSON 한 줄만: {"bitter": <0.3~3.0>, "acidic": <0.3~3.0>}

예시:
seed: "아메리카노만 마셔요 진하게" → {"bitter": 2.4, "acidic": 0.5}
seed: "바닐라라떼 시럽 추가" → {"bitter": 0.5, "acidic": 2.3}
seed: "커피 잘 몰라요" → {"bitter": 1.0, "acidic": 1.0}
seed: "산미 있는 핸드드립 좋아함" → {"bitter": 0.7, "acidic": 2.0}

seed: "%s" →"""

_LLM_LR_CAP = 3.0  # 단일 seed 우도비 상한 (양방향, 과신 방지)


def build_llm_infer(complete_fn, lr_cap: float = _LLM_LR_CAP):
    """seed_text -> {"bitter": Lb, "acidic": La} 콜러블 생성.

    complete_fn: prompt(str) -> 응답 텍스트(str) 콜러블 (예: Claude 래퍼). 주입식이라
    engines/는 Flask·SDK 무의존 유지. 파싱 실패/예외 시 (1.0, 1.0)=무정보로 폴백.
    반환 우도비는 [1/lr_cap, lr_cap]로 클램프.
    """
    def _clip(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return 1.0
        return max(1.0 / lr_cap, min(lr_cap, v))

    def infer(seed_text: str) -> dict:
        try:
            raw = complete_fn(LLM_LIKELIHOOD_PROMPT % str(seed_text).replace('"', "'"))
            start, end = raw.find("{"), raw.rfind("}")
            obj = json.loads(raw[start:end + 1]) if 0 <= start < end else {}
            return {"bitter": _clip(obj.get("bitter", 1.0)),
                    "acidic": _clip(obj.get("acidic", 1.0))}
        except Exception:
            return {"bitter": 1.0, "acidic": 1.0}

    return infer
