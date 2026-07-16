# Leoflavor KANBAN

**최종 수정**: 2026-07-16
**엔진**: Leoflavor v0.2 (사주 검증 게이트, 피처 sf-3 — sf-4 국 감지는 검증 후 미채택)

---

## 🔄 IN PROGRESS

| 항목 | 우선순위 | 담당 | 비고 |
|------|---------|------|------|
| 커피 자아 카드 노출 배치 결정 | High | **fableself** | Leo가 결정 위임(7/16). seed 예측을 참여자에게 되돌려줄 때 lift 오염 여부·배치(피드백 전/후·공유카드 한정) 결정 요청 발신(fableself_flavor_20260716_151200). 캐릭터 내용층(coffee_persona)은 구현 완료, 회신 후 렌더 배선 |
| flavor 서비스 레오서버 이관 | High | **admin** | Leo 결정 (7/11, mukl 재시작 대신 이관). 요청 발신 admin_flavor_20260711_173956 — **7/12 무회신 확인, 서버 여전히 502. Leo 보고됨** |

> **Leo 결정 (7/10)**: 실데이터 수집은 0으로 리셋 후 재시작. 그 전에 이론·가설 완전 검증.
> 순서: 이론 검증 → 플랫폼(서버/카카오 로그인) → 유통. 배포·유통은 검증 완료까지 보류.
> **Leo 결정 (7/11)**: ① 서버는 레오서버로 이관(admin) ② 오염 차단 UX 승인(완료) ③ 별격 감지 진행(완료)

---

## 🚧 BLOCKED

| 항목 | 담당 | 사유 |
|------|------|------|
| Stage 1 검증 리포트 (실데이터) | reklcli | 서버 502 — 레오서버 이관(admin) 완료 대기 |

---

## 📋 TODO

| 항목 | 우선순위 | 담당 | 비고 |
|------|---------|------|------|
| 콜드스타트 실 lift 측정 | Medium | reklcli | 리셋 후 커피 피드백 축적 시 `measure_coldstart_lift.py --db --arm random`(무교란). lift 확인 시 seed+LLM 주입 → 추천 교체 게이트(Leo 승인) |
| 콜드스타트 arm 게이트 개방 | Medium | **Leo** | 리셋 시점. `config/coldstart_arm.json` enabled=true·frac 0.10~0.20·seed_collection=true. 개방 체크리스트=docs/COLDSTART_MEASUREMENT_DESIGN.md §개방 |
| ~~seed 온보딩 문항 프론트 배선~~ | ~~High~~ | reklcli | ✅ **완료 (7/16)** — 아래 DONE 참조 |
| 파일럿 B (음악 콜드스타트) | Low | reklcli | 커피 파일럿 실 lift 검증 후. Music4All-Onion 코호트+경량 성격 |
| 학습 게이트 개방 (learning_gate enabled=true) | Medium | **Leo** | 리셋 후 도메인별 피드백 신뢰 규모 도달 시. 구현·테스트 완료, 활성화만 |
| vol1_taste(27문항) 메타 문항 적용 여부 | Low | Leo→reklcli | 별도 포맷이라 미적용 — 유통 재개 전 결정 |
| v0.2 서버 배포 | High | Leo→reklcli | 이론 검증 완료 후. Leo 배포 승인 필요 |
| DB 리셋 실행 | High | flavor2 | Leo 확정 (7/10). 유통 재시작 직전에 실행 |
| 카카오 로그인 | High | reklcli+Leo | 유저 식별 확립 (person n 신뢰도) — 유통 전 필수 |
| 유통/바이럴 채널 결정 | Medium | Leo | 이론 검증 + 플랫폼 완료 후 |
| Stage 2 게이트 판정 | Medium | reklcli | 리셋 후 n_persons 200 도달 시 `scripts/validate_saju_signal.py` |
| Phase D: ML 전환 | Low | reklcli | 200명+ 데이터 후, 하네스 Ridge CV 활성화 |

---

## ✅ DONE (최근)

| 날짜 | 항목 |
|------|------|
| 2026-07-16 | **seed 온보딩 프론트 배선** (Leo 지정 7/13): 커피 seed 1문항 자유입력 → submit `seeds:[]`. 서버 게이트 `/api/coldstart-config`(seed_collection, 기본 OFF) 노출 → quiz-engine.js가 플래그 ON일 때만 마지막 문항 후 seed 화면 **동적 주입**(HTML 쉘 20여개 무변경). OFF=완전 항등 엔드투엔드 확인(문항 미노출·`_coldstart` 미부착). 배정 규칙(랜덤 arm)은 서버 담당이라 프론트 미노출. 테스트 115개(+3). shared 엔진 vol4~20 커버, 레거시 vol2/vol3·종합설문은 별도 JS라 이후 확장 |
| 2026-07-13 | **콜드스타트 커피 축 정직화 + 키워드 교정** (페플셀프 점검 Q1·Q3·Q6, Leo 승인): 쓴맛형/산미형 → 진한 블랙형/부드러운 스위트형(축 a=우유·단맛 유무). 핸드드립·산미=축 b 예약어 분리. seed 패밀리 계상+총 LR 캡 3배. pivot 변수화. 심볼 전수 동기, 테스트 112개 |
| 2026-07-13 | **콜드스타트 랜덤 arm + seed 수집 + LLM 우도 인터페이스** (페플셀프 점검 Q2/Q3 반영, Leo "①리셋 전 필수" 선택): 리셋 순간부터 켜야 소급 가능한 2건 게이트형 구현. apply_random_arm(OFF=완전 항등) + config/coldstart_arm.json + submit 배선(seeds→results._coldstart) + lift 하네스 --arm random 무교란 필터 + build_llm_infer. 설계서 docs/COLDSTART_MEASUREMENT_DESIGN.md. 테스트 20개(전체 107). OFF/ON 엔드투엔드 스모크 확인. 커밋 push 완료 |
| 2026-07-13 | **페플셀프 파일럿 A 점검** 의뢰·회신: 방향 충실, 실질 결함 2건(키워드 축 혼동·lift 셀렉션 바이어스). 리셋 전 필수=랜덤 arm+seed 수집(소급 불가). exchange/flavor-pilotA-review-v01.md |
| 2026-07-12 | **파일럿 A — 커피 콜드스타트 예측** (Leo 승인, fableself 리서치 기반): 코호트(연령·성별 문헌 계수)+seed 베이지안 → 쓴맛형/산미형. lift 하네스(concordance, 저장 데이터 소급 재계산) 합성검증 통과. 사주=미사용(외부 예측력 0). 실 lift는 데이터 대기, 추천 교체 미적용 |
| 2026-07-12 | **fableself 리서치 의뢰·회신**: 외부 데이터셋/방법론 shortlist. 결론=코호트+LLM seed 콜드스타트가 최속 lift, 사주=예측력 0(게이트 정합 확인) |
| 2026-07-12 | **학습 루프 실작동 (게이트)** (Leo 선택): 무력했던 confidence 주석 → 유사유저 피드백 아이템 재랭킹. domains.py 후보 풀 + recommend.py learned_rerank + config/learning_gate.json(default OFF=항등). 활성화만 Leo 승인 대기 |
| 2026-07-12 | **클라이언트 맵 MAP_V2 패리티** (§7): saju-engine.js가 감사 이전 구맵 → 서버 V2 동기화 + 가드 테스트. 감사 아크 완결 |
| 2026-07-12 | **게이트 수정안 v1.1 발효** (Leo 승인): 노출 전 원칙 + CONTAMINATION_FLAG + 신봉도 층화가 게이트 판정 정본 기준 |
| 2026-07-12 | **오염 완화책 3·4 완료**: 어휘 분리(사전+페르소나 리라이트+가드 테스트), nc/신봉도 메타 문항, 하네스 v1.1. 버그픽스 2건(클라이언트 지장간 본기, innate 집계 공회전) |
| 2026-07-12 | **sf-4 국(局) 감지 검증 → 미채택**: 별격 recall +7pp ↔ 정격 오탐 상쇄, 교차평가 이득 0. 실험 코드 experiment/sf4-guk 보존 (VERDICT_2026-07-12_guk) |
| 2026-07-11 | **오염 차단 UX** (Leo 승인): 선천 배너 응답 후 노출, A/B 랜덤 순서, ux:'nv1' 플래그 — 엔진+레거시 4파일 |
| 2026-07-11 | **별격 감지 v1 (sf-3)**: 합화/양기성상/전왕/종격 + 록겁 격명 + 순세 용신. 격국 44.9%→61.7% (VERDICT_byeolgyeok) |
| 2026-07-11 | **이론 검증 사이클 1 완결**: 신강약 87.5% ✅ / 격국(자평진전) 75% ✅ / 용신 47.8% ❌→저신뢰 태그 (VERDICT 2건) |
| 2026-07-11 | 억부용신 v2 원인 기반 규칙 (sf-2, +10.4pp), 적천수천미 508 정답지 구축 |
| 2026-07-10 | **Leoflavor v0.2 — 사주 검증 게이트** 설계+구현 (설계서 docs/ENGINE_V02_DESIGN.md) |
| 2026-07-10 | engines/saju_features.py: 십신 강도(지장간·궁성 가중)/신강약/억부용신/격국+투간/상호작용 7종 |
| 2026-07-10 | 검증 하네스 scripts/validate_saju_signal.py (Spearman+순열+BH-FDR, 기준 pre-registered) |
| 2026-07-10 | 버그픽스: sipsin.py 지장간 본기(여기로 읽던 것), recommend.py 🎯→👎 집계, measure_accuracy 동일 |
| 2026-07-10 | Phase B 배선: submit.py에 get_feedback_data 연동 (min_sim 0.3, min_contributors 3) |
| 2026-07-10 | DB saju_json 컬럼 + admin export 확장, 테스트 31개 (tests/) |
| 2026-03-22 | 피드백 UI 4단계 리액션 교체 (👍👎 → 🎯👍🤷👎, 2x2 그리드, thumb 2/1/-1/-2) |
| 2026-03-20 | 시즌 매거진 허브 리디자인 (시즌 탭, 매거진 카드, 프로그레스바, 리포트 CTA) |
| 2026-03-20 | 취향 리포트 페이지 (`/my-report`, `/my-report-saju`) — 수집 그리드, 갭분석, 공유 |
| 2026-03-20 | quiz-engine.js: 결과 타입(innate/actual) localStorage 저장 추가 |
| 2026-03-18 | 시즌 2 퀴즈 10개 (vol11-vol20) DNA+사주 20파일 생성, 40개 라우트 추가 |
| 2026-03-18 | 기존 퀴즈 전수 검수: 오타, 전문용어→일반어, 브랜드명 삽입 |
| 2026-03-18 | 퀴즈 제목 개그맨 페르소나(유재석+신동엽) 리라이트 |
| 2026-03-18 | 어드민 대시보드 `/dashboard` 생성 |
| 2026-03-18 | 피드백 UI(👍👎) 전 퀴즈 추가 (→ 3/22에 4단계 리액션으로 교체) |
| 2026-03-16 | 적중률 측정 실행 (74.8%, 테스트 데이터) |
| 2026-03-15 | 만세력 엔진 교체: lunar 라이브러리 |
| 2026-03-15 | 전체 퀴즈 135문항 실제사례 리라이트 |

---

## 📌 메모

- **현재 총 퀴즈**: 시즌1(9개) + 시즌2(10개) + 종합(1개) = 20개 (DNA+사주 = 40파일)
- **접속 현황 (3/20)**: 총 90건 누적, 최근 24시간 0건 → 유통 급선무
- **카카오 로그인**: 네이버보다 쉬움, client_secret 선택, 검수 불필요. localStorage→서버 세션 전환 필요
- 다음 milestone: 200명 (ML 전환)
