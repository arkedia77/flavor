"""Leoflavor Engine v0.2 설정"""

import json
import os

DB_PATH = os.environ.get("DB_PATH", "/tmp/saju_submissions.db")

ENGINE_VERSION = "0.2"

# ── 사주 검증 게이트 ──
# 가중치 전부 0 = v0.1과 동일 동작. 개방은 검증 게이트 통과 + Leo 승인 커밋으로만.
SAJU_GATE_PATH = os.path.join(os.path.dirname(__file__), "config", "saju_gate.json")
_GATE_DIMENSIONS = ["social", "adventurous", "aesthetic", "comfort",
                    "budget", "maximalist", "energetic", "urban", "bitter"]
_ZERO_GATE = {
    "gate_version": "fail-safe-zero",
    "max_weight": 0.0,
    "require_hour_known": True,
    "weights": {d: 0.0 for d in _GATE_DIMENSIONS},
}


def load_saju_gate(path: str = None) -> dict:
    """게이트 로드. 파일 없음/파싱 실패/음수/max_weight 초과 → 전부 0 폴백 (fail-safe)"""
    try:
        with open(path or SAJU_GATE_PATH, encoding="utf-8") as fp:
            gate = json.load(fp)
        max_w = float(gate.get("max_weight", 0.0))
        weights = gate.get("weights", {})
        for d in _GATE_DIMENSIONS:
            w = float(weights.get(d, 0.0))
            if w < 0.0 or w > max_w:
                return dict(_ZERO_GATE)
        gate["weights"] = {d: float(weights.get(d, 0.0)) for d in _GATE_DIMENSIONS}
        return gate
    except Exception:
        return dict(_ZERO_GATE)


SAJU_GATE = load_saju_gate()

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
