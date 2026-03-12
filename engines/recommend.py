"""피드백 학습 기반 추천 엔진 (Leoflavor v0.1)

추천 흐름:
1. 규칙 기반 추천 (cold-start, domains.py)
2. 유사 유저의 피드백으로 보정 (데이터 축적 시)

핵심 아이디어:
- 9차원 벡터 간 코사인 유사도로 "유사 유저" 탐색
- 유사 유저들의 👍👎 패턴을 가중 투표
- 규칙 기반 추천 + 피드백 보정 = 하이브리드 추천
"""

import json
import math
from config import DIMENSIONS
from engines.domains import run_all_domains


def cosine_similarity(a: dict, b: dict) -> float:
    """9차원 프로필 간 코사인 유사도 (0~1)"""
    dot = sum(a.get(d, 0.5) * b.get(d, 0.5) for d in DIMENSIONS)
    mag_a = math.sqrt(sum(a.get(d, 0.5) ** 2 for d in DIMENSIONS))
    mag_b = math.sqrt(sum(b.get(d, 0.5) ** 2 for d in DIMENSIONS))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def find_similar_users(target_profile: dict, all_profiles: list, top_k: int = 10) -> list:
    """유사 유저 top-k 탐색

    Args:
        target_profile: 현재 유저의 9차원 프로필
        all_profiles: [{"id": ..., "profile": {...}, "feedbacks": [...]}, ...]
        top_k: 반환할 유사 유저 수

    Returns:
        [(similarity, user_data), ...] 유사도 내림차순
    """
    scored = []
    for user in all_profiles:
        sim = cosine_similarity(target_profile, user["profile"])
        scored.append((sim, user))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def feedback_boost(rule_results: dict, similar_users: list, min_sim: float = 0.85) -> dict:
    """유사 유저 피드백으로 규칙 기반 추천 보정

    - 유사도 min_sim 이상인 유저만 참고
    - 도메인별로 👍가 압도적이면 신뢰도 ↑, 👎 많으면 대안 표시

    Returns:
        dict: 도메인별 {item, reason, description, confidence, feedback_signal}
    """
    boosted = {}

    for domain, rec in rule_results.items():
        thumbs_up = 0
        thumbs_down = 0
        total_weight = 0

        for sim, user in similar_users:
            if sim < min_sim:
                continue
            for fb in user.get("feedbacks", []):
                if fb["domain"] == domain:
                    weight = sim  # 유사도가 곧 가중치
                    if fb["thumb"] == 1:
                        thumbs_up += weight
                    else:
                        thumbs_down += weight
                    total_weight += weight

        result = dict(rec)

        if total_weight > 0:
            confidence = thumbs_up / total_weight
            result["confidence"] = round(confidence, 2)
            result["feedback_signal"] = {
                "up": round(thumbs_up, 2),
                "down": round(thumbs_down, 2),
                "sample_size": len([s for s, u in similar_users if s >= min_sim]),
            }
        else:
            result["confidence"] = None
            result["feedback_signal"] = None

        boosted[domain] = result

    return boosted


def recommend(profile: dict, all_profiles: list = None) -> dict:
    """통합 추천 함수

    - all_profiles가 없거나 비어있으면: 규칙 기반만 (cold-start)
    - all_profiles가 있으면: 규칙 + 피드백 보정 (하이브리드)
    """
    rule_results = run_all_domains(profile)

    if not all_profiles:
        return rule_results

    similar = find_similar_users(profile, all_profiles)
    return feedback_boost(rule_results, similar)
