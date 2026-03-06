-- ============================================================
-- Flavor DB Schema — PostgreSQL
-- SAJU 추천 엔진 RAG + 학습 데이터 수집
-- ============================================================

-- 확장
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ──────────────────────────────────────────
-- 유저 (익명 + 선택적 식별)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_token TEXT UNIQUE,          -- 로컬스토리지용 (기기 연결)
    email         TEXT UNIQUE,          -- 선택 입력 (시리즈 영구 연결용)
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ──────────────────────────────────────────
-- 퀴즈 설문 제출 (Vol.1 설문형)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS submissions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID REFERENCES users(id),          -- nullable (익명)
    quiz_type        TEXT NOT NULL DEFAULT 'vol1_taste', -- vol1_taste / vol2_ab / ...
    name             TEXT,
    birth_date       TEXT,
    birth_time       TEXT,
    gender           TEXT,
    elements_json    JSONB,   -- 오행 원본 (엔진 캘리브레이션용)
    raw_survey_json  JSONB,   -- 문항별 원본 응답 (캘리브레이션용)
    survey_json      JSONB,   -- 9차원 계산값
    profile_json     JSONB,   -- blend된 최종 프로필
    results_json     JSONB,   -- 도메인별 추천 결과
    personality_json JSONB,   -- 취향 타입 (type/emoji/tagline/detail)
    profile_version  TEXT,    -- 가중치 버전 추적
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ──────────────────────────────────────────
-- A/B 바이너리 세션 (Vol.2+ A/B 포맷)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ab_sessions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id    UUID REFERENCES submissions(id) ON DELETE CASCADE,
    question_id      TEXT NOT NULL,      -- 'q1', 'q2', ...
    dimension        TEXT NOT NULL,      -- 매핑된 취향 차원
    choice           CHAR(1) NOT NULL,   -- 'A' or 'B'
    choice_value     FLOAT NOT NULL,     -- A=0.0~0.3, B=0.7~1.0 (dimension 방향)
    response_ms      INTEGER,            -- 응답 시간 (행동 데이터)
    changed          BOOLEAN DEFAULT FALSE, -- 처음 답 바꿨는지 (고민 신호)
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ──────────────────────────────────────────
-- 피드백 (도메인별 👍👎)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedbacks (
    id             SERIAL PRIMARY KEY,
    submission_id  UUID REFERENCES submissions(id) ON DELETE CASCADE,
    domain         TEXT NOT NULL,        -- 커피/향수/음악/...
    thumb          SMALLINT NOT NULL,    -- 1: 👍  -1: 👎
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ──────────────────────────────────────────
-- 단축 URL
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS short_urls (
    code          TEXT PRIMARY KEY,       -- 6자리 Base62
    submission_id UUID NOT NULL REFERENCES submissions(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ──────────────────────────────────────────
-- 마일스톤 알림 (50/200/500명 도달 기록)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS milestones (
    milestone  INTEGER PRIMARY KEY,
    reached_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ──────────────────────────────────────────
-- 인덱스
-- ──────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_submissions_user     ON submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_submissions_quiz     ON submissions(quiz_type);
CREATE INDEX IF NOT EXISTS idx_submissions_created  ON submissions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ab_sessions_sub      ON ab_sessions(submission_id);
CREATE INDEX IF NOT EXISTS idx_ab_sessions_dim      ON ab_sessions(dimension);
CREATE INDEX IF NOT EXISTS idx_feedbacks_sub        ON feedbacks(submission_id);
CREATE INDEX IF NOT EXISTS idx_feedbacks_domain     ON feedbacks(domain);

-- ──────────────────────────────────────────
-- 뷰: 튜닝 툴용
-- ──────────────────────────────────────────

-- 차원별 평균 분포 (가중치 검증용)
CREATE OR REPLACE VIEW v_profile_distribution AS
SELECT
    quiz_type,
    profile_version,
    COUNT(*) as n,
    AVG((profile_json->>'social')::float)       AS avg_social,
    AVG((profile_json->>'adventurous')::float)  AS avg_adventurous,
    AVG((profile_json->>'aesthetic')::float)    AS avg_aesthetic,
    AVG((profile_json->>'comfort')::float)      AS avg_comfort,
    AVG((profile_json->>'budget')::float)       AS avg_budget,
    AVG((profile_json->>'maximalist')::float)   AS avg_maximalist,
    AVG((profile_json->>'energetic')::float)    AS avg_energetic,
    AVG((profile_json->>'urban')::float)        AS avg_urban,
    AVG((profile_json->>'bitter')::float)       AS avg_bitter
FROM submissions
WHERE profile_json IS NOT NULL
GROUP BY quiz_type, profile_version;

-- 도메인별 피드백 정확도
CREATE OR REPLACE VIEW v_feedback_accuracy AS
SELECT
    domain,
    COUNT(*) FILTER (WHERE thumb = 1)  AS thumbs_up,
    COUNT(*) FILTER (WHERE thumb = -1) AS thumbs_down,
    ROUND(
        COUNT(*) FILTER (WHERE thumb = 1)::numeric /
        NULLIF(COUNT(*), 0) * 100, 1
    ) AS accuracy_pct
FROM feedbacks
GROUP BY domain
ORDER BY accuracy_pct DESC;

-- A/B 문항별 응답 분포 (질문 품질 지표)
CREATE OR REPLACE VIEW v_ab_question_stats AS
SELECT
    question_id,
    dimension,
    COUNT(*) AS total,
    AVG(choice_value) AS avg_value,      -- 0.5에 가까울수록 변별력 낮음
    STDDEV(choice_value) AS std_value,
    AVG(response_ms) AS avg_response_ms, -- 느릴수록 질문 애매함
    AVG(changed::int) * 100 AS change_rate_pct
FROM ab_sessions
GROUP BY question_id, dimension
ORDER BY question_id;
