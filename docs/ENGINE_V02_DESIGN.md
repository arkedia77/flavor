# Leoflavor Engine v0.2 설계서 — 사주 검증 게이트

**작성**: 2026-07-10 | **승인**: Leo (설계 방향 + 산출물 범위, AskUserQuestion 확정)
**전신**: Gemini 프로토타입 → v1.x~v1.5 blend 엔진 → v0.1 설문 100%

---

## 1. 왜 다시 사주인가

v0.1은 2026-03-12 판정(오행 count 선형회귀, n=60, p=0.575, CV R²=-0.222)으로
사주를 추천에서 완전히 제거했다. 그러나 그 판정에는 세 가지 한계가 있었다:

1. **피처가 피상적**: 오행 개수 세기뿐 — 십신·용신·격국·신강약·생극·비선형 전부 누락.
   "알파벳 빈도로 영어를 분석"한 수준 (당시 포스트모템의 자평).
2. **데이터가 오염**: 60건 전부 birth_time=12(기본값) — 시주가 전부 가짜 오시(午時)로
   계산되어 火 과대추정 노이즈. 지금은 사주 트랙 퀴즈가 실제 시주를 수집한다.
3. **분석이 증발**: 검증 스크립트가 커밋되지 않아 재현 불가. 판정문만 CHANGELOG에 남음.

~~학술 근거도 있다: 십신↔MBTI 상관 논문 유의 5쌍(p<0.05)~~
**[정정 2026-07-10]** 근거 감사 결과 해당 논문은 실존 미확인 — 학술 DB(RISS/KCI/
DBpia/ScienceON) 전수 조사에서 십신↔MBTI를 p<0.05로 보고한 동료심사 논문 없음.
가장 근접한 백강희·정미숙(2022)은 질적 연구(p값 없음), 이남호·김만태(2018)는 n=20.
MAP_V2 근거는 전량 "실무 아키타입 수렴" 티어로 강등했다
(reports/theory/EVIDENCE_AUDIT_2026-07-10.md). 사주→취향 직접 연구는 국내외 공백 —
우리의 차별점이자, 기댈 선행연구가 없다는 뜻. 최종 타당성은 검증 게이트가 판정한다.

## 2. 전신 3개 비교

| | Gemini 원본 (saju.js/flavor.js) | v1.5 blend (아카이브) | v0.1 (현행) |
|---|---|---|---|
| 사주 사용 | 100% — 오행 top2 × 십신그룹 → 6카테고리 프리셋 텍스트 | 오행 비율 → 9차원 매핑, 설문 blend (고정 25% / 동적 15~50%) | 0% — 페르소나명만 |
| 피처 | 오행 분포 + 십신 그룹 (질적) | 오행 비율, 십신 5그룹, 음양, 신강도 | — |
| 검증 | 없음 | 오행 count 회귀 실패 → 폐기 | 설문 적중률 74.8% (테스트 데이터) |
| 교훈 | 콘텐츠는 풍부하나 점수 없음 | **검증 없이 가중치를 먼저 열었다** | 사주 신호를 통째로 버렸다 |

**v0.2의 원칙: v1.5의 반대 순서.** 가중치를 먼저 열지 않는다.
피처를 제대로 뽑고 → 저장하고 → 커밋된 하네스로 검증하고 → 통과한 차원만 연다.

## 3. 아키텍처 (3레이어 + 게이트)

```
[생년월일시] → engines/saju_features.extract_features()   ← L0 선천 prior
                  ├─ saju_json 저장 (감사 기록 + 캐시)
                  └─ sipsin_prior_delta() × MAP_V2 → saju_prior_9d()
[설문]      → engines/survey.raw_to_survey()               ← L1 후천 관측
                  ↓
engines/gated_blend.apply_gated_blend(survey, prior, SAJU_GATE)
                  ↓   가중치 전부 0 = profile == survey (비트 단위 동일, 테스트 보증)
recommend(profile, get_feedback_data())                    ← L2 피드백 학습
                  ↓   confidence/feedback_signal 주석만 — 추천 아이템 불변
8도메인 결과
```

### 사주 피처 (engines/saju_features.py, SCHEMA_VERSION sf-1)

- **가중 슬롯 전개**: 궁성 가중(년간1.0/월간1.2/시간1.0/년지1.0/**월지2.5**/일지1.5/시지1.0)
  × 지장간 가중(lunar 순서 [본기,중기,여기] 기준 len3→[0.6,0.3,0.1], len2→[0.7,0.3], len1→[1.0])
- **십신 강도** 10종 + 5그룹 (합=1), dominant + margin
- **신강약 연속 점수**: 슬롯 지지율(비겁 1.0 / 인성 0.8 / 기타 0), 중화점 0.36
  (균등분포 기대값) + 득령/득지/득세 분해
- **억부용신**: 신약→인성/비겁 중 유력한 쪽, 신강→식상/재성/관성 중 유력한 것.
  degree(억부 필요 강도), strength_in_chart(용신 유력도). 조후용신은 유파 이견으로 제외
  (method 필드로 확장 여지).
- **격국**: 월지 본기 + 투간 보정 (본기>중기>여기 투출 우선). 시간 미상 시 時干 제외.
- **오행**: raw count(실패 베이스라인 대조군) + 가중 분포 + 엔트로피
- **음양비**, **상호작용 7종** (식상관성비, 재성×신강, 관성×신강, 식상×신강,
  인성식상비, 용신강도, 양기×비겁)
- **시간 미상**: 시주 슬롯 자체를 제외하고 재정규화. **12시 가짜 주입 금지.**
  비사주 트랙의 birth_time="12"는 하드코딩 기본값이므로 불신 (trust_default_noon=False).
  hour_known / degraded_features 플래그로 하네스가 층화.

### SIPSIN_FLAVOR_MAP_V2 (가설 테이블 — 검증 대상)

십신→9차원 delta. 항목별 rationale + evidence 등급 — **감사(2026-07-10) 후 전량
"실무수렴"(독립 소스 3개+ 아키타입) / "실무단독" 티어. 논문 근거 없음.**
urban 차원 delta는 전부 (추정) 표기, 식신 social-/energetic-는 실무 소스와 모순이라
삭제. **진폭(±0.08)은 방향성 가설일 뿐, 검증 후 회귀로 재추정.**

### ⚠️ 기대효과 오염 (검증 유효성의 전제)

현 quiz-engine.js는 문항마다 선천 성향 배너를 응답 **전에** 표시하고 innate 값으로
A/B 프레이밍을 뒤집는다 — 자기귀인 효과(Fichten & Sunerton 1983)로 응답이 사주
가설 방향으로 오염될 수 있어, 이 상태의 데이터는 게이트 판정에 쓸 수 없다.
리셋 후 수집 전에 **노출 전 수집 원칙**(설문 완료 후에만 사주 결과 표시) 적용 필요
— 퀴즈 UX 변경이므로 Leo 결정 사항. 상세: reports/theory/EVIDENCE_AUDIT_2026-07-10.md

### 검증 게이트 (config/saju_gate.json)

- 9차원 가중치 전부 **0.0**에서 시작. max_weight 0.30, require_hour_known true.
- 로더(config.load_saju_gate)는 파싱 실패/음수/초과 시 **전부 0 폴백** (fail-safe).
- profile_version: 가중치가 하나라도 열린 행만 `_g{gate_version}` suffix.
- 롤백 = saju_gate.json을 0으로 되돌리는 1줄 커밋. survey 원본이 항상 저장되므로
  어떤 행이든 재계산 가능.

## 4. 게이트 기준 (pre-registered — 사후 변경 금지)

> **Stage 1 (n_persons < 200)**: 탐색 전용. 어떤 가중치도 열지 않는다.
> **Stage 2 (n_persons ≥ 200)**: 차원 d "signal confirmed" ⇔
> |Spearman ρ_d| ≥ 0.20 AND BH-FDR q_d < 0.05 (9검정) AND 순열검정 p < 0.01 (10,000회)
> AND 시간분할 부호 일치. 통과 차원만 w_d = 0.15 (**Leo 승인 커밋**).
> **Stage 3 (n_persons ≥ 500)**: Stage 2 판정 **이후 신규 데이터만으로** 동일 기준
> 재확인 시 w_d ≤ 0.30 (cap).
> 시주 의존 차원은 hour_known 부분집합 n으로 별도 충족 필요.

근거: n=200에서 r=0.2는 α=0.05 양측 검정력 ~0.8. 기존 마일스톤(200/500명)과 일치.

**주 타깃 = 사주 prior → 9차원 survey** (person 단위). 게이트가 열리면 prior가
대체하는 대상이 정확히 survey 차원이므로 검증 대상과 배포 사용처가 일치한다.
피드백 thumb은 규칙 엔진 품질과 교락되어 게이트 기준으로 쓰지 않는다 (모니터링만).

### 수정안 v1.1 (2026-07-12 — DB 리셋·수집 재개 **전** 등록, EVIDENCE_AUDIT 완화책 4)

> 원 기준의 "사후 변경 금지"는 데이터 관측 후 기준 변경 금지를 뜻한다. 이 수정안은
> 게이트 대상 데이터가 아직 0건인 시점(리셋 전)에 오염 통제를 **추가**하는 것으로,
> 기존 통과 문턱은 완화하지 않고 강화만 한다.
> **발효: Leo 승인 (2026-07-12) — 이 커밋부터 v1.1이 게이트 판정의 정본 기준.**
> 이후 변경은 다시 "사후 변경 금지" 대상이다.

1. **노출 전 응답 원칙**: 게이트 판정의 주 대상은 person의 **시간순 첫 제출**
   survey(해당 제출이 실제 측정한 차원만). 이후 제출은 결과 화면에서 선천
   성향·페르소나를 본 뒤라 자기귀인 오염 가능(Fichten & Sunerton 1983).
   전체 평균 기준은 참고 지표로 병기.
2. **네거티브 컨트롤**: 퀴즈에 nc_* 문항(사주 이론·표시 카피와 무연결 취향,
   MAP_V2 delta 영구 부재 서약)을 포함. 어떤 prior 차원이든 nc 차원과
   CONFIRMED 동등 기준(|ρ|≥0.20 ∧ q<0.05 ∧ p_perm<0.01)을 충족하면
   **CONTAMINATION_FLAG** — 해당 리포트의 모든 CONFIRMED 무효, 원인 규명 전
   게이트 개방 금지.
3. **신봉도 층화**: meta_belief 문항(사주 신봉 여부)으로 층화. CONFIRMED 차원이
   비신봉군에서 |ρ|<0.05 이거나 부호가 뒤집히면 **SELF_ATTRIBUTION_SUSPECT**
   — 해당 차원 개방 보류(바넘/자기귀인 의심), Leo 판단.

구현: 퀴즈 메타 문항(static/shared/quiz-engine.js META_QUESTIONS + 레거시 4파일),
하네스 v1.1(scripts/validate_saju_signal.py), 어휘 분리 가드
(config/dimension_lexicon.json + tests/test_lexicon_separation.py).

## 5. 검증 하네스 (scripts/)

- `data_io.py`: fetch(API/DB) + 위생 필터 — DUMMY_CUTOFF=2026-03-14 이전 제외,
  person dedupe((name,birth_date,gender) 키, survey 평균, birth_time 모순 시 미상 강등)
- `validate_saju_signal.py`: confirmatory 9검정(Spearman+순열+BH+부트스트랩CI+시간분할)
  / exploratory 스크린(개별 피처 × 9차원, Fisher-z 근사 — **게이트 사용 금지**, 가설 개정용)
  / 보조(innate 동의율 이항검정) / 모니터링(도메인별 피드백)
- 출력: `reports/saju_signal/{날짜}_{gitsha}_{datahash}.json+.md` — **git 커밋 필수**.
  판정만 남고 스크립트가 증발했던 2026-03-12의 재발 방지.

## 6. 이번에 함께 수리한 것 (사주 무관)

- `engines/sipsin.py:135`: 지장간 본기를 `arr[-1]`(여기)로 읽던 버그 → `arr[0]`
  (lunar_python 순서 [본기,중기,여기] 실측 확인)
- `engines/recommend.py`: thumb==1만 up으로 세어 🎯(2)가 👎로 집계되던 버그 →
  THUMB_VALUE={2:1.0, 1:0.5, -1:-0.5, -2:-1.0} 가중 투표. min_sim 0.5→0.3,
  min_contributors=3 미만이면 confidence=None.
- `api/submit.py`: 피드백 학습 경로 배선 (recommend에 get_feedback_data 연결).
  feedback_boost는 아이템을 바꾸지 못하므로(주석만) 최악에도 추천은 규칙 결과와 동일.
- `scripts/measure_accuracy.py`: 동일 thumb 버그 수정 + 가중 적중률 병기.
- DB: `submissions.saju_json` 컬럼 추가 (기존 ALTER 마이그레이션 패턴).
  옛 행 NULL — /result/<id> 하위호환 유지, 백필 불필요(결정적 재계산 가능).

## 7. 명시적 이월 (v0.3+)

- 조후용신, 합충형해 생극 그래프 피처
  - 합충 동적 피처 실험 sf-4(국 감지)는 검증 후 미채택 (VERDICT_2026-07-12_guk.md)
- ~~도메인별 대안 랭킹 (item swap)~~ → **구현 완료(게이트 방식, 2026-07-12)**.
  domains.py `DOMAIN_POOL` + recommend.py `learned_rerank`. config/learning_gate.json
  `enabled=false`가 기본 = 규칙 top 불변(v0.1 동작, 테스트 보증). 아이템 단위 신호는
  저장된 results_json + 도메인 피드백으로 재구성(feedbacks 테이블 무변경). 활성화는
  데이터 축적 + Leo 승인 커밋으로만. 스토어 포맷은 additive(learned/rule_item 키만
  추가) — /result 하위호환 유지.
- ~~클라이언트 saju-engine.js의 MAP_V2 패리티~~ → **완료(2026-07-12)**.
  SIPSIN_FLAVOR_MAP을 서버 MAP_V2에 동기화 + 패리티 가드 테스트.
- Ridge CV 회귀 (n≥150에서 하네스에 활성화), ML 전환 (Phase D, 200명+)

### 학습 게이트 (config/learning_gate.json) — 사주 게이트와 대칭

- `enabled` false 시작. min_sim 0.3 / min_contributors 3 / min_advantage 0.5.
- 로더(config.load_learning_gate)는 파싱 실패/비정상 값 시 **enabled=False 폴백** (fail-safe).
- 재랭킹 조건: 유사 유저(sim≥min_sim)의 아이템별 유사도-가중 thumb 평균에서,
  기여자 min_contributors 이상인 후보 최고점이 규칙 픽 대비 min_advantage 이상 우수 ∧
  순양수일 때만 풀에서 승격. 규칙 픽 데이터 부재 시 순양수 최고 후보 승격.
- 게이트 열기 = 도메인별 피드백이 신뢰 규모(리셋 후 person n)에 도달했을 때 Leo 판단.
  롤백 = enabled false 1줄. survey/prior/results 원본이 항상 저장되므로 재계산 가능.

## 8. 테스트 앵커

- 1977-04-11 16시(신시) = 정사/갑진/무술/경신, 일간 무(토양) — 외부 만세력 검증 완료 명식
- 야자시: lunar_python 기본 동작(23시 당일 일주 유지 + 자시)을 테스트로 고정
- 핵심 보증 테스트: **게이트 전부 0 → profile == survey 정확 일치** (v0.1 동작 보존)
