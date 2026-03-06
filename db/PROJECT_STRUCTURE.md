# Flavor 프로젝트 구조

```
flavor/
├── app.py                        # Flask 메인 (라우팅)
├── config.py                     # 환경변수, 상수 관리
├── requirements.txt
├── Procfile
│
├── engines/                      # 핵심 계산 엔진
│   ├── saju.py                   # 오행 계산 (백엔드 전용)
│   ├── profile.py                # survey → 9차원 벡터 변환
│   ├── blend.py                  # 사주 × 설문 블렌딩
│   ├── personality.py            # 벡터 → 취향 타입
│   └── domains.py                # 취향 → 도메인별 추천
│
├── quizzes/                      # 퀴즈 시리즈별 콘텐츠
│   ├── vol1_taste/               # Vol.1 설문형 (현재 라이브)
│   │   ├── survey.html           # 설문 + 결과 UI
│   │   └── questions.json        # 문항 데이터 (분리 예정)
│   └── vol2_ab/                  # Vol.2 A/B 바이너리 (파일럿)
│       ├── ab.html               # A/B 퀴즈 UI
│       └── questions.json        # A/B 문항 쌍 + 차원 매핑
│
├── db/
│   ├── schema.sql                # PostgreSQL 정식 스키마
│   ├── schema_sqlite.sql         # SQLite 현재 스키마 (마이그레이션 전)
│   └── migrations/               # 버전별 마이그레이션
│       └── 001_initial.sql
│
├── admin/                        # 튜닝 툴 (내부 전용)
│   ├── dashboard.py              # 어드민 라우트
│   └── dashboard.html            # 가중치 시뮬레이터 UI
│
└── static/
    ├── css/flavor.css            # 공통 스타일
    └── js/flavor.js              # 공통 유틸
```

## 개발 원칙

### 데이터 레이어 분리
```
취향 문항  → profile_json / ab_sessions → 엔진 학습 100% 활용
심리 요소  → 결과 표현용 (가중치 0, 엔진 미사용)
```

### 퀴즈 추가 기준
- 엔진에 필요한 **미수집 취향 차원**이 있을 때만
- 재미 때문에 만들지 않는다
- 각 퀴즈는 `questions.json`으로 콘텐츠 분리 (코드 변경 없이 문항 교체 가능)

### 버전 관리
```
PROFILE_VERSION  — 가중치/공식 변경 시 bump
QUIZ_VERSION     — 문항 변경 시 bump (같은 버전끼리만 비교)
```

### DB 마이그레이션 계획
```
현재:  SQLite (app.py 내 init_db)
목표:  PostgreSQL (schema.sql)
시점:  500명 도달 전 or 독립 도메인 이전 시
방법:  sqlite3 → psql 마이그레이션 스크립트 작성
```
