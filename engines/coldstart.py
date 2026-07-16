"""콜드스타트 카테고리 취향 예측 — 파일럿 A (커피 축 a: 진한 블랙형/부드러운 스위트형)

근거: fableself 리서치 (2026-07-12) + 점검 (2026-07-13,
agent-comm/projects/fableself/exchange/flavor-pilotA-review-v01.md).
자체 설문·데이터 0에서 base rate 초과를 노리는 하이브리드 콜드스타트:
  성별×연령 코호트 사전확률(문헌 계수) × seed 자연어 우도(LLM 주입 가능) → 베이지안.

축 정직화 (점검 Q1·Q6): 현 키워드·8아이템이 실제로 재는 건 '우유·단맛 유무'(축 a:
진한 블랙 vs 부드러운 스위트)이지 '로스팅 쓴맛↔산미'(축 b)가 아니다. 문헌의 쓴맛 내성
계수도 축 a에 더 잘 이식된다(쓴맛 내성↑ → 우유·설탕 없는 블랙 선호↑). 산미/라이트로스트
어휘(핸드드립·산미·프룻)는 축 b 예약어로 분리(현재 미사용).

정직성 (효과크기):
  단일 신호→취향 상관은 전부 약함(성격→장르 r≈0.06, 개별 0.1~0.2). 실전 lift는
  결합에서 나온다. 아래 계수는 fitted 값이 아니라 문헌 방향성 prior다.
  - Barragán 2018 (18-80): 연령↑ → 쓴맛 내성↑ → 블랙 선호↑
  - Frontiers 2024 / PTC 테이스터(여 72%>남 64% 쓴맛 민감): 남성 → 블랙 / 여성 → 스위트
  - 사주·별자리·출생계절 = 외부 예측력 ≈ 0 → 미사용. 생년월일은 연령 환원분만 투입.

engines/는 Flask 무의존. LLM은 llm_infer 콜러블로 주입(미지정 시 오프라인 키워드
휴리스틱). 실제 LLM(Claude) 연결은 자연어 seed 수집이 생긴 뒤의 확장 지점이다.
"""

import json

# 커피 취향 축 (a): 진한 블랙형(black) vs 부드러운 스위트형(sweet)
# fableself 점검 Q1·Q6: 현 키워드·8아이템 풀이 실제로 재는 건 '우유·단맛 유무'(축 a)이지
# '로스팅 쓴맛↔산미'(축 b)가 아니다. 축 이름을 실물에 맞게 정직화하고, 산미/라이트로스트
# 어휘(핸드드립·산미·프룻)는 축 b 예약어로 분리(현재 우도 미사용). SKU에 라이트로스트
# 라인이 생기면 축 b를 2번째 축으로 승격(SCA 휠 어휘 재사용).
TYPE_KR = {"black": "진한 블랙형", "sweet": "부드러운 스위트형"}

# ── 코호트 사전확률 계수 (P(black)=진한 블랙 선호, 방향성 prior) ──
# fableself: 문헌의 '쓴맛 내성' 계수는 축 b(로스팅)보다 축 a(블랙·진함)에 더 잘 이식된다
# (쓴맛 내성↑ → 우유·설탕 없는 블랙 선호↑). 그래서 prior의 출력은 P(black)이다.
_AGE_PIVOT = 40          # 기본 pivot(이 연령에서 연령효과 0). 유저 베이스 평균 연령으로
                         # 교체 권장(리셋 후 첫 100명) — 계통편향 제거. predict의 age_pivot 인자.
_AGE_SLOPE = 0.006       # 1세당 블랙 선호 +0.6%p (18→80에서 약 ±0.13). Barragán 2018 방향성.
_GENDER_OFFSET_MALE = 0.08
_GENDER_OFFSET_FEMALE = -0.08
_P_MIN, _P_MAX = 0.15, 0.85  # 코호트만으로는 확신 금지

_MALE_TOKENS = {"male", "m", "man", "남", "남성", "남자"}
_FEMALE_TOKENS = {"female", "f", "woman", "여", "여성", "여자"}

# seed 키워드 패밀리 (오프라인 기본 — LLM 미주입 시). fableself Q3: 상관 키워드 이중
# 계상 방지 위해 패밀리당 최대 1회만 계상하고, 총 우도비는 캡한다(predict).
_BLACK_FAMILIES = [
    ["아메리카노", "룽고"],
    ["에스프레소"],
    ["블랙"],
    ["진하", "다크"],
    ["콜드브루"],
]
_SWEET_FAMILIES = [
    ["라떼", "플랫화이트", "플랫 화이트"],
    ["바닐라", "카라멜", "시럽"],
    ["달달", "달콤"],
    ["오트"],
    ["연하"],
]
# 축 b(로스팅: 산미·라이트로스트) 예약어 — 현재 우도 미사용. 핸드드립은 산미 감상 대표
# 추출법이라 블랙 키워드에서 제거해 여기로 이동(fableself Q1). 라이트로스트 SKU가 생기면
# 이 어휘로 축 b를 활성화.
_ACIDITY_RESERVED = ["핸드드립", "드립", "산미", "프룻", "게이샤", "라이트로스트", "라이트 로스트"]

_KW_LR = 1.6              # 패밀리당 우도비 (약한 신호)
_SEED_TOTAL_LR_CAP = 3.0  # 총 우도비 상한 (fableself Q3: 곱셈 스태킹 과신 방지)

# 커피 풀 아이템 → 축 a 라벨. 축 a는 '우유·단맛 유무'라 핸드드립 아이템도 블랙(우유 무).
# 애매한 것은 "mixed" — 엄격 일치도 지표에서 제외.
COFFEE_ITEM_TYPE = {
    "스페셜티 싱글오리진 핸드드립": "black",
    "에스프레소·아이스 아메리카노": "black",
    "스페셜티 콜드브루·블랙워터": "black",
    "따뜻한 아메리카노·단골 블렌드": "black",
    "카페라떼·바닐라라떼": "sweet",
    "달달한 라떼·플랫화이트": "sweet",
    "오트밀크 라떼·콜드브루": "sweet",
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


def cohort_black_prior(age, gender, age_pivot: float = _AGE_PIVOT) -> float:
    """(연령, 성별) → P(진한 블랙형) 사전확률. 결정적. 문헌 방향성 prior.

    age_pivot: 이 연령에서 연령효과 0. 기본 40 → 유저 평균 연령으로 교체 시 계통편향 제거.
    """
    p = 0.50
    if age is not None:
        p += _AGE_SLOPE * (age - age_pivot)
    g = _norm_gender(gender)
    if g == "male":
        p += _GENDER_OFFSET_MALE
    elif g == "female":
        p += _GENDER_OFFSET_FEMALE
    return _clamp(p)


def _keyword_likelihood(seed_text: str):
    """seed 자연어 → (L_black, L_sweet) 우도 근사. 패밀리당 최대 1회 계상(이중 계상 방지).
    매칭 없으면 (1,1)=무정보."""
    t = str(seed_text).lower()

    def n_fam(families):
        return sum(1 for fam in families if any(kw in t for kw in fam))

    return _KW_LR ** n_fam(_BLACK_FAMILIES), _KW_LR ** n_fam(_SWEET_FAMILIES)


def coffee_item_type(item: str) -> str:
    """커피 풀 아이템명 → 'black'|'sweet'|'mixed'|'unknown' (축 a)"""
    return COFFEE_ITEM_TYPE.get(item, "unknown")


def predict_coffee_type(age, gender, seeds=None, llm_infer=None,
                        age_pivot: float = _AGE_PIVOT) -> dict:
    """(연령, 성별, seed들) → 커피 타입 예측(축 a: black/sweet). 결정적(llm_infer 미주입 시).

    seeds: 자연어 seed 리스트 (예: ["아메리카노 진하게"]). 없으면 코호트만.
    llm_infer: seed_text -> {"black": Lb, "sweet": Ls} 우도 콜러블 (선택).
               미지정 시 오프라인 키워드 휴리스틱 사용.
    age_pivot: 코호트 prior의 연령 pivot (유저 평균 연령 주입 지점).
    총 우도비는 [1/cap, cap]로 제한(fableself Q3: seed 과신 방지).
    """
    prior_black = cohort_black_prior(age, gender, age_pivot)
    lb, ls = 1.0, 1.0
    for s in (seeds or []):
        if not s:
            continue
        if llm_infer is not None:
            l = llm_infer(s) or {}
            lb *= max(1e-6, float(l.get("black", 1.0)))
            ls *= max(1e-6, float(l.get("sweet", 1.0)))
        else:
            kb, ks = _keyword_likelihood(s)
            lb *= kb
            ls *= ks

    # 총 우도비 캡: seed 영향을 [1/cap, cap]로 제한
    if ls > 0:
        ratio = max(1.0 / _SEED_TOTAL_LR_CAP, min(_SEED_TOTAL_LR_CAP, lb / ls))
        lb, ls = ratio, 1.0

    denom = prior_black * lb + (1.0 - prior_black) * ls
    post = (prior_black * lb) / denom if denom > 0 else prior_black
    post = _clamp(post, 0.01, 0.99)
    typ = "black" if post >= 0.5 else "sweet"
    return {
        "type": typ,
        "type_kr": TYPE_KR[typ],
        "p_black": round(post, 3),
        "prior_black": round(prior_black, 3),
        "method": "cohort+seed" if (seeds and any(seeds)) else "cohort",
        "used_seeds": [s for s in (seeds or []) if s],
    }


def age_from_birth_year(birth_year: int, reference_year: int) -> int:
    return reference_year - birth_year


# ── 커피 자아 카드 (표현층, 2026-07-16) ──────────────────────────────
# Leo 원칙: 참여자도 재밌고 공유할 개인 컨텐츠가 형성돼야 함. seed를 추출형으로 걷지 말고
# '커피 자아 캐릭터'로 되돌려준다. 측정용 predict_coffee_type(코호트+seed 베이지안)과 분리된
# 순수 표현 매핑 — seed 키워드로 결정. 축 a(black/sweet) 위에 결(flavor)을 얹어 개인화.
# **노출 배치(피드백 전/후·공유카드 한정)는 측정 오염 우려로 fableself 결정 대기** —
# 이 함수는 내용만 제공하고 어디서 렌더할지는 배선 시 확정.
_PERSONA_UNKNOWN_KW = ["잘 몰라", "잘몰라", "모르", "아무거나", "글쎄", "안 마", "안마", "없"]
_DESSERT_KW = ["프라푸치노", "프라페", "휘핑", "휘프", "생크림", "크림", "디저트", "밀크쉐이크", "쉐이크"]

# 자아 = (키, 이름, 이모지, 한 줄, 축 a 극). 키워드 우선순위대로 첫 매칭 채택.
COFFEE_PERSONA = {
    "acidity":   {"name": "산미 헌터",     "emoji": "🫐", "pole": "black",
                  "oneliner": "커피 한 잔에서 과일 향까지 사냥하는 미식가"},
    "black":     {"name": "블랙 미니멀리스트", "emoji": "☕", "pole": "black",
                  "oneliner": "군더더기 없는 쓴맛에서 평온을 찾는 타입"},
    "dessert":   {"name": "디저트 겸용파",  "emoji": "🎂", "pole": "sweet",
                  "oneliner": "이게 커피야 디저트야? 둘 다임"},
    "sweet":     {"name": "달달 로맨티스트", "emoji": "🍦", "pole": "sweet",
                  "oneliner": "인생은 달아야지, 커피도 예외 없음"},
    "sprout":    {"name": "커피 새싹",      "emoji": "🌱", "pole": "unknown",
                  "oneliner": "아직 내 취향을 찾는 중 — 그것도 매력"},
}


def coffee_persona(seed_text: str) -> dict:
    """seed 자연어 → 커피 자아 카드(표현층, 결정적). 측정 예측과 독립.

    키워드 우선순위: 산미(축 b 어휘)→디저트→블랙→스위트→무정보(새싹).
    무정보 seed도 긍정적으로 되돌려줘(새싹) 추출감 제거. 반환 dict에 공유 문구 포함.
    """
    t = str(seed_text or "").lower().strip()
    key = "sprout"
    if not t or any(kw in t for kw in _PERSONA_UNKNOWN_KW):
        key = "sprout"
    elif any(kw in t for kw in _ACIDITY_RESERVED):
        key = "acidity"
    elif any(kw in t for kw in _DESSERT_KW):
        key = "dessert"
    elif any(any(kw in t for kw in fam) for fam in _BLACK_FAMILIES):
        key = "black"
    elif any(any(kw in t for kw in fam) for fam in _SWEET_FAMILIES):
        key = "sweet"

    p = COFFEE_PERSONA[key]
    return {
        "key": key,
        "name": p["name"],
        "emoji": p["emoji"],
        "oneliner": p["oneliner"],
        "pole": p["pole"],
        "share": f"내 커피 자아 = {p['name']} {p['emoji']}",
    }


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
이 사람이 '우유·설탕 없는 진한 블랙 커피(black)'를 좋아할 가능성 대
'우유·시럽 들어간 부드럽고 달콤한 커피(sweet)'를 좋아할 가능성의 우도비를 매겨라.
(로스팅 산미가 아니라 '우유·단맛 유무' 축이다 — 핸드드립처럼 산미 얘기는 중립에 가깝게.)
seed가 취향 정보를 거의 안 주면 1.0(무정보)에 가깝게.
출력은 JSON 한 줄만: {"black": <0.3~3.0>, "sweet": <0.3~3.0>}

예시:
seed: "아메리카노만 마셔요 진하게" → {"black": 2.4, "sweet": 0.5}
seed: "바닐라라떼 시럽 추가" → {"black": 0.5, "sweet": 2.3}
seed: "커피 잘 몰라요" → {"black": 1.0, "sweet": 1.0}
seed: "산미 있는 핸드드립 좋아함" → {"black": 1.2, "sweet": 1.0}

seed: "%s" →"""

_LLM_LR_CAP = 3.0  # 단일 seed 우도비 상한 (양방향, 과신 방지)


def build_llm_infer(complete_fn, lr_cap: float = _LLM_LR_CAP):
    """seed_text -> {"black": Lb, "sweet": Ls} 콜러블 생성.

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
            return {"black": _clip(obj.get("black", 1.0)),
                    "sweet": _clip(obj.get("sweet", 1.0))}
        except Exception:
            return {"black": 1.0, "sweet": 1.0}

    return infer
