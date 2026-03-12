# Flavor CHANGELOG

---

## 2026-03-12

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
