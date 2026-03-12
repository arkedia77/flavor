"""Leoflavor Engine v0.1 설정"""

import os

DB_PATH = os.environ.get("DB_PATH", "/tmp/saju_submissions.db")

ENGINE_VERSION = "0.1"

# 추천 경계값 상수
HIGH = 0.65
LOW = 0.35
MHI = 0.60
MLO = 0.40

# 9차원
DIMENSIONS = [
    "social", "adventurous", "aesthetic", "comfort",
    "budget", "maximalist", "energetic", "urban", "bitter",
]

DOMAIN_EMOJI = {
    "커피": "☕", "향수": "🌸", "음악": "🎵", "식당": "🍽️",
    "운동": "🏃", "여행": "✈️", "패션": "👗", "인테리어": "🏠",
}
