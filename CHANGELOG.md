# Leoflavor CHANGELOG

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
