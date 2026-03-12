# Flavor CHANGELOG

---

## 2026-03-12

### 매핑 v3 + 동적 가중치 (캘리브레이션 1차)
- gap.py: baseline+편차 구조 도입 (방향 일치율 64%→88%, bitter 25%→100%)
- blend.py: 편향도 기반 동적 사주 가중치 (15%~50%) + 차원별 확신도 보정
- 8건 실데이터 기반 검증, 60건 도착 시 재보정 예정

### Phase 1: Deep Saju Engine
- saju.py → v2.0: 4주(입춘/절기/JDN), 십신, 지장간 보정 오행, 격국, 신강/신약
- saju_tables.py: 천간/지지/오행/지장간/절기/십신/격국/일간타입 정적 테이블
- calendar.py: JDN, 절기 기반 월지, 시간→지지 변환
- vector.py: saju_to_innate_vector() → 12D innate vector
- 기존 API 호환 유지

### Phase 2: 타입 + 갭 시스템
- personality.py → L1(일간 10종) + L2(격국×강약 20종) + L3(9D 아키타입) 하이브리드
- gap.py: innate vector → expected 9D 매핑, 선천-후천 갭 분석 + 해석
- blend.py: blend_profile() 추가 (12D innate vector 기반, 기존 elements_to_profile 하위호환)
- submit.py: Phase 2 파이프라인 통합 (saju_detail, innate_vector, gap 응답 포함)

### Phase 0: 모듈 분리
- app.py 1187줄 → 34줄 (앱 팩토리 + Blueprint 등록)
- engines/ 생성: saju.py, survey.py, blend.py, personality.py, domains.py
- api/ 생성: public.py (페이지 라우트), submit.py (API 라우트)
- db/ 생성: connection.py, repository.py
- config.py 생성: 상수, 경계값, 임계점
- .gitignore 추가 (__pycache__/)
- 전체 11개 라우트 테스트 통과, 하위호환 유지
- commit: d468924
- CLAUDE.md, KANBAN.md, CHANGELOG.md 생성

---

## 2026-03-11

### 프로젝트 정비
- project_flavor.md 생성 + MEMORY.md 등록
- 전체 리소스 위치 수집 (GitHub, Google Drive, agent-comm)
- mukl DB 현황 확인: submissions 60건, feedbacks 210건

---

## 2026-03-09 ~ 2026-03-11

### v1.5 시리즈
- A/B 바이너리 퀴즈 (/ab)
- 스와이프 카드 UI (/swipe) + z-index 수정
- 3종 UX 비교 랜딩 (/compare) + /api/ux-vote
- 브랜딩: '사주' → '생년월일/취향 유형'
