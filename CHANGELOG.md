# Leoflavor CHANGELOG

---

## 2026-07-11 — 오염 차단 UX + 별격 감지 (sf-3)

### Changed (오염 차단 — Leo 승인)
- `static/shared/quiz-engine.js` + 레거시 인라인 4파일(vol2/vol3 DNA·사주):
  선천 성향 배너를 응답 **후** 노출로 변경 (자기귀인 오염 차단, EVIDENCE_AUDIT 완화책 1)
  - 문항 화면: 배너 → 중립 질문 헤더, A/B 순서 innate 기반 → 문항별 랜덤 (위치 편향 제거)
  - 답변에 `ux:'nv1'` 플래그 — 하네스가 오염 전/후 응답 구분 가능
  - `agreed_with_innate` = 방향 일치 의미로 재정의

### New (별격 감지 v1 — SCHEMA sf-3)
- `engines/saju_features.py` `_special_gyeokguk()` — 합화/양기성상/전왕/종격 감지
  + 순세 용신 (왕신 따름). 판정: reports/theory/VERDICT_2026-07-11_byeolgyeok.md
- 록겁 격명 매핑: 월지 본기 비견→건록격, 겁재→양인격(양간)
- `flatten()` `gyeokguk_special` one-hot 추가
- 격국 정확도: 전체 44.9%→61.7%, 별격 0%→51.3%, 자평진전 75% 유지
- 테스트 43개 (별격 앵커 6개 추가)

---

## 2026-07-10 — Leoflavor Engine v0.2 (사주 검증 게이트)

### New
- `engines/saju_features.py` — 사주 피처 추출 v2 (십신 강도 지장간·궁성 가중,
  신강약 연속 점수, 억부용신, 격국+투간, 상호작용 7종, 시간미상 처리). SCHEMA sf-1
- `SIPSIN_FLAVOR_MAP_V2` — 십신→9차원 prior 가설 테이블 (근거 등급 명기, 검증 대상)
- `engines/gated_blend.py` + `config/saju_gate.json` — 검증 게이트 블렌드.
  **가중치 전부 0 = v0.1과 동일 동작** (테스트 보증). fail-safe 로더
- `scripts/data_io.py` — 데이터 IO + 위생 필터 (더미 제외, person dedupe, hour 판정)
- `scripts/validate_saju_signal.py` — 검증 하네스 (Spearman+순열검정+BH-FDR+부트스트랩,
  게이트 기준 pre-registered). 리포트는 reports/saju_signal/에 git 커밋
- `tests/` — 단위 테스트 31개 (만세력 앵커, 게이트 항등성, thumb 가중치 등)
- `submissions.saju_json` 컬럼 — 사주 피처 벡터 저장 (옛 행 NULL, /result 하위호환)
- 설계서: `docs/ENGINE_V02_DESIGN.md`

### Fixed
- `engines/sipsin.py` — 지장간 본기를 여기(餘氣)로 읽던 버그 (`arr[-1]`→`arr[0]`)
- `engines/recommend.py` — 🎯(thumb=2)가 👎로 집계되던 버그 → THUMB_VALUE 가중 투표,
  min_sim 0.5→0.3, min_contributors=3 미달 시 confidence=None
- `scripts/measure_accuracy.py` — 동일 thumb 버그 수정, 가중 적중률 병기
- `requirements.txt` — python-dotenv 누락 추가 (app.py가 이미 import 중이었음)

### Changed
- `api/submit.py` — 사주 피처 계산·저장 + 게이트 블렌드(현재 no-op) +
  피드백 학습 경로 배선 (아이템 불변, confidence 주석만)
- `ENGINE_VERSION` "0.1" → "0.2" (게이트 0이므로 추천 결과는 v0.1과 동일)

### 원칙 변경
- "설문 = 추천의 100%" → **검증 게이트**: 사주 prior는 저장·검증되며, 커밋된
  하네스가 Stage 2(n≥200) 기준을 통과한 차원만 Leo 승인으로 가중치 개방

---

## 2026-03-12 — Leoflavor Engine v0.1 (엔진 재설계)

### Breaking Changes
- 사주 blend 완전 제거 (설문 100% 기반 추천)
- 사주 엔진 파일 삭제 (saju.py, blend.py, vector.py, gap.py, calendar.py, saju_tables.py)
- `PROFILE_VERSION` → `ENGINE_VERSION`
- `get_personality_type()` 시그니처 변경 (saju_detail 파라미터 제거)

### New
- `engines/persona.py` — 사주 → 캐릭터명 (마케팅 훅 전용)
- `engines/recommend.py` — 피드백 학습 기반 하이브리드 추천
- `db/repository.py: get_feedback_data()` — 피드백 학습용 데이터 조회

### Changed
- `api/submit.py` — 파이프라인 단순화 (survey → profile → recommend → persona)
- `config.py` — ENGINE_VERSION="0.1", DIMENSIONS 리스트 추가
- `engines/personality.py` — L3(9차원) 전용으로 단순화

### Archive
- 이전 사주 엔진: `v1.5-archive` 태그, `archive/saju-engine-v1.5` 브랜치
- 사주 가설 판정: 60건 분석 결과 통계적 미지지 (p=0.575, CV R²=-0.222)

---

## Archive (v1.0~v1.5)

사주 기반 엔진 이력은 `archive/saju-engine-v1.5` 브랜치 참조.
- Phase 0: 모듈 분리 (d468924)
- Phase 1: Deep Saju Engine (42bed49)
- Phase 2: 타입+갭 시스템 (730ba75)
- 매핑 v3 (fdf530f)
- v1.5: A/B + 스와이프 + 비교 + UX투표
