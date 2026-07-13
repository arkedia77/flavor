# 콜드스타트 측정 설계 — 랜덤 arm · seed 수집 · LLM 우도

**날짜**: 2026-07-13
**승인**: Leo ("①리셋 전 필수부터" 선택) — 페플셀프 점검 회신 반영
**근거**: `agent-comm/projects/fableself/exchange/flavor-pilotA-review-v01.md` (점검 소견)
**상태**: 게이트형 구현 완료, **기본 OFF=완전 항등**. 개방은 DB 리셋 시점부터 Leo 승인 커밋으로만.

---

## 왜 지금(데이터 0) 해야 하나 — 소급 불가성

페플셀프 점검의 핵심: **예측은 소급 재계산되지만, 두 가지는 영원히 소급 불가**다.
데이터가 쌓인 뒤엔 못 만든다 → 리셋 순간부터 켜져 있어야 한다.

| 항목 | 소급 가능? | 이유 |
|------|-----------|------|
| 코호트 예측(연령·성별) | ✅ 가능 | birth_date·gender가 컬럼 → 언제든 재계산 |
| **노출 arm(랜덤/규칙)** | ❌ **불가** | 무엇을 보여줬는지의 **배정 규칙**은 그 시점에만 존재. 사후에 "랜덤이었다" 못 만듦 |
| **seed 자연어** | ❌ **불가** | 안 물어봤으면 그 텍스트는 영원히 없음 |

## Q2 결함 — concordance lift의 셀렉션 바이어스

현 lift 지표:
```
concordance lift = P(👍 | 보여준 아이템 타입 == 예측 타입) − P(👍 | 불일치)
```
노출이 비랜덤(9차원 규칙이 아이템 선택)이고 그 규칙이 연령·성별과 상관이면:
- match 셀에 "시스템이 원래 잘 서빙하던 유저×아이템"이 몰림 → lift 과대
- 인기 아이템이 한쪽 타입에 몰리면 인기 효과가 match 셀에 실려 또 과대
- **소급 재계산은 로깅 문제만 풀 뿐 배정(assignment) 교란은 못 푼다**

→ 유일한 무교란 추정치 = **노출의 일부를 풀 내 무작위로 서빙하는 랜덤 arm**. 비용 ≈ 0.

---

## 구현 (전부 게이트 OFF=항등)

### 1. 랜덤 노출 arm

- **게이트**: `config/coldstart_arm.json` — `enabled:false, random_frac:0.0, domains:["커피"]`.
  로더 `config.load_coldstart_arm()` fail-safe(비정상 값 → OFF). 사주/학습 게이트와 동일 철학.
- **엔진**: `engines/coldstart.apply_random_arm(results, config, rng)` — 순수 함수.
  - OFF(enabled=False ∨ frac≤0) → `results` 그대로 반환(완전 항등, 태그도 안 붙임).
  - ON → `domains`의 각 도메인에서 `rng.random() < frac`이면 `DOMAIN_POOL`에서 무작위
    아이템 서빙(`_arm:"random"`, `_rule_item`=규칙 원픽), 아니면 규칙 픽 유지(`_arm:"rule"`).
  - 원본 results 불변(얕은 복사). `_arm` 태그가 `results_json`에 저장 → 소급 가능.
- **배선**: `api/submit.py`에서 `recommend()` 직후 `apply_random_arm(results, COLDSTART_ARM, random)`.
  라이브 rng=`random` 모듈, 테스트=`Random(seed)`.
- **분석**: `measure_coldstart_lift.py --arm random` → 랜덤 arm만 골라 **무교란** lift.
  태그 없는 옛 행은 `rule`로 간주. `--arm all/rule`은 교란 가능 경고 출력.

### 2. seed 수집

- **저장**: submit이 `data["seeds"]`(자연어 리스트, 최대 3개) → `results["_coldstart"].seeds`에
  네임스페이스 저장(스키마·시그니처 무변경, `results_json` 블롭 안). seed 없고 게이트 OFF면
  `_coldstart` 키 자체를 안 붙임(완전 항등).
- **예측 반영**: lift 하네스가 `_coldstart.seeds`를 읽어 `predict_coffee_type(..., seeds=)`에
  투입. seed 있는 행만 seed 보정, 없으면 코호트-only(기존과 동일).
- **온보딩 문항(프론트 TODO, 개방 전 배선)**: 커피 카테고리 진입 시 1문항 —
  "커피는 보통 뭐로 드세요? (한 줄, 예: 아메리카노 진하게 / 바닐라라떼)". 자유 입력 →
  `seeds:["..."]`로 submit에 전달. 별도 테이블 불필요.

### 3. LLM 우도 인터페이스

- `engines/coldstart.build_llm_infer(complete_fn, lr_cap=3.0)` → `seed_text → {bitter,acidic}`
  콜러블 생성. `complete_fn`=텍스트 완성 콜러블 주입식(engines/ Flask·SDK 무의존 유지).
  파싱 실패·예외 → `(1.0,1.0)` 무정보 폴백. 우도비 `[1/cap, cap]` 클램프.
- 프롬프트: `LLM_LIKELIHOOD_PROMPT`(few-shot 4예시, JSON 한 줄 출력).
- `predict_coffee_type(..., llm_infer=infer)`로 주입. 미주입 시 오프라인 키워드 휴리스틱(현행).
- **Q3 대응**: 단일 seed 우도비 캡 3배(곱셈 스태킹 과신 방지). 다중 seed 곱은
  predict에서 누적되므로 seed 수는 3개로 제한.

---

## 개방 체크리스트 (DB 리셋 시점, Leo 승인 필요)

1. `config/coldstart_arm.json`: `enabled:true, random_frac:0.10~0.20`, `seed_collection:true`.
2. 온보딩 seed 문항 프론트 배선(커피 진입 1문항).
3. **클라이언트 렌더가 `results`의 `_`접두 메타키(`_arm`, `_coldstart`)를 건너뛰는지 확인** —
   OFF 상태에선 안 붙어 현재 무영향이나, 개방 시 도메인 카드 렌더가 메타키를 무시해야 함.
4. (선택) `build_llm_infer`에 Claude 래퍼 주입 — seed 우도를 키워드→LLM으로 승격.
5. 수집 후: `measure_coldstart_lift.py --db <path> --arm random` → 무교란 lift. 셀당 n≥30 전엔
   수치 보고 보류(하네스가 n<30 경고). lift 확정 시 추천 교체 게이트 별도 개방(Leo 승인).

## 아직 안 한 것 (의도적 — 별도 승인/작업)

- **키워드 사전 교정**(핸드드립 축 혼동 등, 점검 Q1·Q6) — 엔진 변경이라 Leo 승인 대기(옵션②).
  이 문서는 ①(랜덤 arm+seed+LLM 인터페이스)만 다룸.
- 추천 아이템의 예측 기반 실제 교체 — 실 lift 검증 후.
- pivot=유저 평균 연령 교체(점검 Q1) — 첫 100명 수집 후 1줄 수정.
- 임베딩 매칭 사다리(점검 Q5) — 중기 업그레이드.

## 테스트

`tests/test_coldstart_arm.py` 20개 — OFF 항등(4)·ON frac/태그/불변/도메인한정(6)·하네스 arm
필터+seed(5)·LLM 파싱/클램프/폴백(5)·로더 fail-safe(2). 전체 107개 통과.
