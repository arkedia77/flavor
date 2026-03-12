# Leoflavor Engine v0.1

**목적**: 설문 기반 취향 분석 + 피드백 학습 서비스
**서비스 URL**: https://flavor.arkedia.work
**최종 수정**: 2026-03-12
**엔진 버전**: Leoflavor v0.1

---

## 핵심 원칙

1. **설문 = 추천의 100%** (사주 blend 폐기, 데이터로 검증 완료)
2. **사주 = 마케팅 훅** (캐릭터명/페르소나만, 엔진 내부에 영향 없음)
3. **피드백이 추천을 개선** (유사 유저 기반 학습 루프)
4. **데이터가 쌓일수록 똑똑해지는 구조**

---

## 역할 분리

```
reklcli (Leo+나)          mukl (Mac mini 서버)
─────────────────         ──────────────────
프로젝트 총괄              서버 배포 (git pull + restart)
엔진 설계·코드 작성        DB 관리 (실 서버 DB)
agent-comm 태스크 발행     Cloudflare 터널 운영
```

---

## 폴더 구조

```
~/projects/flavor/
├── CLAUDE.md              ← 이 파일
├── KANBAN.md              ← 작업 현황판
├── CHANGELOG.md           ← 변경 이력
├── app.py                 ← 앱 팩토리 + Blueprint 등록
├── config.py              ← ENGINE_VERSION, 상수
├── engines/               ← Flask 무의존 순수 Python
│   ├── survey.py          ← raw_to_survey() (9차원 계산)
│   ├── recommend.py       ← recommend() (규칙 + 피드백 학습)
│   ├── personality.py     ← get_personality_type() (9차원 아키타입)
│   ├── persona.py         ← get_persona() (사주 → 캐릭터명)
│   └── domains.py         ← run_all_domains() (8도메인 규칙, cold-start)
├── api/
│   ├── public.py          ← /, /survey, /result, /ab, /swipe, /compare, /health
│   └── submit.py          ← /api/submit, /api/feedback, /api/results 등
├── db/
│   ├── connection.py      ← init_db(), get_db_connection()
│   └── repository.py      ← CRUD + get_feedback_data()
├── quizzes/               ← 퀴즈 HTML
└── test_stages/           ← survey.html
```

---

## 절대 규칙

### 1. Leo 승인 필수
- 엔진 공식/가중치 변경
- ENGINE_VERSION 변경
- DB 스키마 변경
- 새 퀴즈 포맷 도입
- 배포 요청

### 2. engines/ Flask 무의존
- engines/ 폴더는 Flask import 금지 (순수 Python)
- B2B API, 배치 처리, 테스트에서 독립 사용 가능해야 함

### 3. 기존 데이터 호환
- /result/<id> URL 기존 60건 정상 동작 보장
- DB 스키마 유지 (submissions, feedbacks, milestones 테이블)

### 4. DB 규칙
- 로컬 테스트: DB_PATH=/tmp/test_flavor.db
- 서버 실 DB: /Users/mushin/data/saju_submissions.db (mukl 관리)

---

## 아카이브

- **태그**: `v1.5-archive` (사주 기반 엔진 최종본)
- **브랜치**: `archive/saju-engine-v1.5`
- 사주 가설 판정 리포트: Notion (2026-03-12)

---

## 통신 규칙

```
agent-comm 채널: ~/projects/agent-comm/flavor/
파일명: {to}_YYYYMMDD_HHMMSS_{키워드}.json
자기 폴더만 Write. 남의 폴더는 Read-Only.
```

## 배포

```
서버: mushin@mac-mini
프로세스: gunicorn (systemd flavor.service)
터널: Cloudflare → flavor.arkedia.work → localhost:8000
재시작: sudo systemctl restart flavor
```
