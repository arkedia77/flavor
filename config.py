"""Flavor 설정 및 상수"""

import os

DB_PATH = os.environ.get("DB_PATH", "/tmp/saju_submissions.db")

PROFILE_VERSION = "1.2"

# 추천 경계값 상수 (데이터 축적 후 캘리브레이션으로 조정)
HIGH = 0.65
LOW = 0.35
MHI = 0.60
MLO = 0.40

# 임계점 알림
AGENT_COMM = os.environ.get("AGENT_COMM_PATH", os.path.expanduser("~/agent-comm"))
CALIBRATION_THRESHOLDS = {
    50:  "방향성 확인 — 오행-차원 상관관계 양/음 검증 가능",
    200: "1차 파라미터 보정 — blend 가중치 및 계수 재보정 가능",
    500: "레이어 구조 재설계 — 회귀분석 기반 파라미터 도출 가능",
}

DOMAIN_EMOJI = {
    "커피": "☕", "향수": "🌸", "음악": "🎵", "식당": "🍽️",
    "운동": "🏃", "여행": "✈️", "패션": "👗", "인테리어": "🏠"
}
