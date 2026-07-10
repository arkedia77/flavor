> **나는 flavor 프로젝트다.** reklcli는 내가 돌아가는 머신의 에이전트 이름일 뿐이다.
> - 내 이름: flavor
> - 내 작업 폴더: ~/projects/flavor (여기서 코드/파일 작업)
> - 내 통신 채널: agent-comm/projects/flavor (메시지만 주고받는 곳)
> - 세션 저장/메모리: 이 폴더(~/projects/flavor)의 .claude/ 스코프에 저장
> - agent-comm 안에 저장하지 않는다


# Leoflavor Engine v0.2

**목적**: 설문 기반 취향 분석 + 사주 검증 게이트 + 피드백 학습 서비스
**서비스 URL**: https://flavor.arkedia.work
**최종 수정**: 2026-07-10
**엔진 버전**: Leoflavor v0.2 (설계서: docs/ENGINE_V02_DESIGN.md)

---

## 핵심 원칙

1. **검증 게이트**: 사주 피처(십신/용신/신강약)는 계산·저장·검증되지만,
   추천 가중치는 config/saju_gate.json — **전부 0에서 시작** (= 설문 100%와 동일 동작).
   커밋된 하네스(scripts/validate_saju_signal.py)가 Stage 2(n≥200) 기준을 통과한
   차원만 Leo 승인 커밋으로 개방. 기준 원문은 설계서 §4 (pre-registered, 사후 변경 금지)
2. **사주 = 마케팅 훅 + 검증 대상 prior** (페르소나는 유지, prior는 게이트 뒤에서 대기)
3. **피드백이 추천을 개선** (유사 유저 기반 학습 루프 — v0.2에서 배선 완료)
4. **데이터가 쌓일수록 똑똑해지는 구조**
5. **분석은 커밋한다** — 검증 리포트는 reports/saju_signal/에 데이터 해시와 함께 git 보존

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
├── config.py              ← ENGINE_VERSION, 상수, SAJU_GATE 로더 (fail-safe)
├── config/saju_gate.json  ← 검증 게이트 가중치 (전부 0, 개방은 Leo 승인 커밋만)
├── engines/               ← Flask 무의존 순수 Python
│   ├── survey.py          ← raw_to_survey() (9차원 계산)
│   ├── saju_features.py   ← 사주 피처 v2 (십신/신강약/용신/격국, MAP_V2, prior)
│   ├── gated_blend.py     ← apply_gated_blend() (가중치 0 = 항등)
│   ├── recommend.py       ← recommend() (규칙 + 피드백 학습, THUMB_VALUE)
│   ├── sipsin.py          ← lunar 기반 만세력 상수/십신 (v0.1 호환 표면)
│   ├── personality.py     ← get_personality_type() (9차원 아키타입)
│   ├── persona.py         ← get_persona() (사주 → 캐릭터명)
│   └── domains.py         ← run_all_domains() (8도메인 규칙, cold-start)
├── api/
│   ├── public.py          ← /, /survey, /result, /ab, /swipe, /compare, /health
│   └── submit.py          ← /api/submit (사주 피처+게이트 블렌드), /api/feedback 등
├── db/
│   ├── connection.py      ← init_db(), get_db_connection()
│   └── repository.py      ← CRUD + get_feedback_data()
├── scripts/
│   ├── data_io.py         ← fetch + 위생 필터 (더미 제외, person dedupe)
│   ├── validate_saju_signal.py ← 검증 하네스 (게이트 판정 도구)
│   └── measure_accuracy.py ← 적중률 측정
├── reports/saju_signal/   ← 검증 리포트 (git 커밋 필수)
├── tests/                 ← unittest (만세력 앵커, 게이트 항등성 등)
├── docs/ENGINE_V02_DESIGN.md ← v0.2 설계서 (게이트 기준 원문)
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

## 통신 규칙 (CHANNEL_RULES v5.5)

```
수신함: ~/projects/agent-comm/projects/flavor/messages/
발신: 받는 쪽 프로젝트의 projects/{to}/messages/에 파일 생성
파일명: {to}_{from}_YYYYMMDD_HHMMSS_{키워드}.json
from/to는 프로젝트명만 사용 (머신명 mukl/reklcli 금지) — 이 프로젝트는 "flavor"
규칙 전문: agent-comm/CHANNEL_RULES.md
```

## 배포

```
서버: mushin@mac-mini
프로세스: gunicorn (systemd flavor.service)
터널: Cloudflare → flavor.arkedia.work → localhost:8000
재시작: sudo systemctl restart flavor
```

## 세션 종료 시
1. KANBAN.md IN PROGRESS 상태 업데이트
2. 작업 결과/인계사항 메시지 작성 → messages/ push
3. agent-comm git push
