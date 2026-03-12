# Flavor 프로젝트 가이드

**목적**: 사주(생년월일) 기반 취향 분석 서비스 — B2B 타겟팅 + 바이럴 큐레이션
**서비스 URL**: https://flavor.arkedia.work
**최종 수정**: 2026-03-12
**엔진 버전**: v1.2 (Phase 0 모듈 분리 완료)

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

## 환경 계층

```
1순위: ~/projects/flavor/       ← 메인 (Source of Truth)
2순위: GitHub (arkedia77/flavor) ← 백업 + 배포 경로
3순위: 서버 (mushin@mac-mini)    ← 프로덕션
```

## 폴더 구조

```
~/projects/flavor/
├── CLAUDE.md              ← 이 파일
├── KANBAN.md              ← 작업 현황판
├── CHANGELOG.md           ← 변경 이력
├── app.py                 ← 앱 팩토리 + Blueprint 등록 (~34줄)
├── config.py              ← 상수, DB_PATH, PROFILE_VERSION
├── engines/               ← Flask 무의존 순수 Python
│   ├── saju.py            ← calc_saju() (간소화, Phase 1에서 교체)
│   ├── survey.py          ← raw_to_survey()
│   ├── blend.py           ← elements_to_profile()
│   ├── personality.py     ← get_personality_type()
│   └── domains.py         ← recommend_*() 8개 + run_all_domains()
├── api/                   ← Flask Blueprints
│   ├── public.py          ← /, /survey, /result, /ab, /swipe, /compare, /health
│   └── submit.py          ← /api/submit, /api/feedback, /api/results 등
├── db/
│   ├── connection.py      ← init_db(), get_db_connection()
│   ├── repository.py      ← CRUD 함수
│   └── schema.sql         ← PostgreSQL 목표 스키마
├── quizzes/               ← 퀴즈 HTML (vol2_ab, vol3_swipe, compare)
├── test_stages/           ← survey.html (vol1)
├── Procfile               ← gunicorn app:app
└── requirements.txt
```

---

## 절대 규칙

### 1. Leo 승인 필수
```
- 엔진 공식/가중치 변경
- PROFILE_VERSION 변경 (기존 데이터 호환 영향)
- DB 스키마 변경
- 새 퀴즈 포맷 도입
- 배포 요청
```

### 2. engines/ Flask 무의존
```
- engines/ 폴더는 Flask import 금지 (순수 Python)
- B2B API, 배치 처리, 테스트에서 독립 사용 가능해야 함
- Flask 의존 코드는 api/ 에만 배치
```

### 3. 기존 데이터 호환
```
- /result/<id> URL 기존 60건 정상 동작 보장
- profile_json, results_json 구조 변경 시 하위호환 필수
- PROFILE_VERSION 변경 시 기존 데이터 재계산 절차 포함
```

### 4. DB 규칙
```
- 로컬 테스트: DB_PATH=/tmp/test_flavor.db
- 서버 실 DB: /Users/mushin/data/saju_submissions.db (mukl 관리)
- 로컬에서 실 DB 직접 수정 금지
```

---

## 세션 루틴

### 세션 시작
```
1. project_flavor.md 읽기 (메모리 복구)
2. KANBAN.md 읽기 (현재 TODO 파악)
3. agent-comm 새 메시지 확인: cd ~/projects/agent-comm && git fetch && git log origin/main -3
```

### 세션 종료 (/clear 전)
```
1. project_flavor.md "🚀 다음 세션 시작점" 업데이트
2. KANBAN.md 업데이트 (완료/진행 현황)
3. CHANGELOG.md 기록
4. git push 확인
```

---

## 통신 규칙

```
agent-comm 채널: ~/projects/agent-comm/flavor/
├── from_reklcli/   ← reklcli만 쓰기
├── from_mukl/      ← mukl만 쓰기
├── from_cowork/    ← cowork만 쓰기

파일명: {to}_YYYYMMDD_HHMMSS_{키워드}.json
JSON 필수 필드: msg_id, from, to, created_at, type, priority, title, body

자기 폴더만 Write. 남의 폴더는 Read-Only.
```

---

## 배포

```
서버: mushin@mac-mini
프로세스: gunicorn (systemd flavor.service)
터널: Cloudflare → flavor.arkedia.work → localhost:8000
재시작: sudo systemctl restart flavor

배포 절차:
1. reklcli: 코드 수정 → git push
2. agent-comm 태스크: mukl에게 배포 요청
3. mukl: git pull → systemctl restart flavor
```

---

## v2.0 로드맵 (Phase별)

| Phase | 내용 | 상태 |
|-------|------|------|
| **0** | 모듈 분리 (app.py → engines/+api/+db/) | ✅ 완료 |
| **1** | Deep Saju Engine (절기/JDN/십신/격국/강약 → 12D vector) | 대기 |
| **2** | 타입 시스템 (L1 10개/L2 ~160개) + 갭 분석 | 대기 |
| **3** | B2B API (/api/v1/profile) | 대기 |
| **4** | 외부 체계 매핑 (MBTI/에니어그램/혈액형) | 대기 |
| **5** | 캘리브레이션 엔진 | 대기 |
| **6** | 갭 퀴즈 콘텐츠 (vol4) | 대기 |

---

## 주요 참조 경로

| 항목 | 경로 |
|------|------|
| 프로젝트 메모리 | `~/.claude/projects/-Users-leo/memory/project_flavor.md` |
| 사주 엔진 연구 | `~/.claude/projects/-Users-leo/memory/saju_engine_research.md` |
| Gemini 원본 | `GoogleDrive/1. work/gemini/sajuflavor/` (saju.js — 정통 사주 엔진) |
| agent-comm | `~/projects/agent-comm/flavor/` |
| 설계서 v1 | `agent-comm/general/FLAVOR_SERVICE_DESIGN.md` |
| 설계서 v2 | `agent-comm/general/FLAVOR_SERVICE_DESIGN_v2.md` |

---

## 이력

| 버전 | 변경 |
|------|------|
| v1.0 | 초기 (설문+사주+추천) |
| v1.1 | blend 정규화 수정 |
| v1.2 | 백엔드 SoT, PROFILE_VERSION |
| v1.3 | 위트 설명 + 피드백 |
| v1.4 | 취향 타입명 + 결과 리디자인 |
| v1.5 | A/B + 스와이프 + 비교 + UX투표 + 브랜딩 |
| v2.0-Phase0 | 모듈 분리 (2026-03-12) |
