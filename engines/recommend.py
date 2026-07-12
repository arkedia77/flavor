"""피드백 학습 기반 추천 엔진 (Leoflavor v0.1)

추천 흐름:
1. 규칙 기반 추천 (cold-start, domains.py)
2. 유사 유저의 피드백으로 보정 (데이터 축적 시)

핵심 아이디어:
- 9차원 벡터 간 centered cosine 유사도로 "유사 유저" 탐색
- 유사 유저들의 👍👎 패턴을 가중 투표
- 규칙 기반 추천 + 피드백 보정 = 하이브리드 추천
"""

import json
import math
from config import DIMENSIONS
from engines.domains import run_all_domains, pool_item

# 4단계 리액션 → 투표 가중치 (🎯소름 2 / 👍맞아 1 / 🤷글쎄 -1 / 👎완전아닌데 -2)
THUMB_VALUE = {2: 1.0, 1: 0.5, -1: -0.5, -2: -1.0}


def centered_cosine(a: dict, b: dict) -> float:
    """9차원 프로필 간 centered cosine 유사도 (-1 ~ +1)

    일반 cosine은 양수 벡터에서 0.85+ 집중 → 변별력 부족.
    각 벡터를 mean-shift(평균 빼기) 후 cosine 계산하면
    Pearson 상관계수와 동등 → 변별력 확보.
    """
    vals_a = [a.get(d, 0.5) for d in DIMENSIONS]
    vals_b = [b.get(d, 0.5) for d in DIMENSIONS]

    mean_a = sum(vals_a) / len(vals_a)
    mean_b = sum(vals_b) / len(vals_b)

    shifted_a = [v - mean_a for v in vals_a]
    shifted_b = [v - mean_b for v in vals_b]

    dot = sum(sa * sb for sa, sb in zip(shifted_a, shifted_b))
    mag_a = math.sqrt(sum(v ** 2 for v in shifted_a))
    mag_b = math.sqrt(sum(v ** 2 for v in shifted_b))

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
        sim = centered_cosine(target_profile, user["profile"])
        scored.append((sim, user))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def feedback_boost(rule_results: dict, similar_users: list, min_sim: float = 0.3,
                   min_contributors: int = 3) -> dict:
    """유사 유저 피드백으로 규칙 기반 추천 보정

    - centered cosine 기준 min_sim 이상인 유저만 참고
      (0.5 → 0.3 완화: 소규모 데이터에서 0.5는 기아 상태)
    - 4단계 리액션을 THUMB_VALUE로 가중 투표 (구버전은 thumb==1만 up으로
      세어 🎯(2)가 down 집계되는 버그가 있었음)
    - 기여 유저가 min_contributors 미만이면 confidence=None (소표본 과신 방지)

    Returns:
        dict: 도메인별 {item, reason, description, confidence, feedback_signal}
    """
    boosted = {}

    for domain, rec in rule_results.items():
        thumbs_up = 0.0
        thumbs_down = 0.0
        total_weight = 0.0
        contributors = set()

        for sim, user in similar_users:
            if sim < min_sim:
                continue
            for fb in user.get("feedbacks", []):
                if fb["domain"] == domain:
                    v = THUMB_VALUE.get(fb["thumb"], 0.0)
                    if v == 0.0:
                        continue  # 알 수 없는 thumb값은 무시
                    w = sim  # 유사도가 곧 가중치
                    if v > 0:
                        thumbs_up += w * v
                    else:
                        thumbs_down += w * (-v)
                    total_weight += w * abs(v)
                    contributors.add(user["id"])

        result = dict(rec)

        if total_weight > 0 and len(contributors) >= min_contributors:
            confidence = thumbs_up / total_weight
            result["confidence"] = round(confidence, 2)
            result["feedback_signal"] = {
                "up": round(thumbs_up, 2),
                "down": round(thumbs_down, 2),
                "sample_size": len(contributors),
            }
        else:
            result["confidence"] = None
            result["feedback_signal"] = None

        boosted[domain] = result

    return boosted


def learned_rerank(rule_results: dict, similar_users: list, gate: dict) -> dict:
    """학습 게이트 — 유사 유저의 아이템 단위 피드백으로 추천 아이템 승격.

    게이트 OFF(enabled=False)면 rule_results를 **그대로** 반환 (v0.1 동작 보존,
    테스트 보증). 사주 게이트와 동일 철학 — 검증·승인 전엔 추천을 바꾸지 않는다.

    ON일 때: 도메인별로 유사 유저(sim>=min_sim)가 '그때 본 아이템'에 준 thumb를
    유사도 가중 평균해 아이템 점수를 낸다. 후보(기여자>=min_contributors) 중 최고가
    규칙 픽보다 min_advantage 이상 우수하고 순양수면 풀에서 그 아이템으로 교체.
    규칙 픽에 데이터가 없으면(유사 유저가 안 봤으면) 순양수 최고 후보를 승격.
    """
    if not gate or not gate.get("enabled"):
        return rule_results

    min_sim = gate.get("min_sim", 0.3)
    min_contrib = gate.get("min_contributors", 3)
    min_adv = gate.get("min_advantage", 0.5)

    out = {}
    for domain, rec in rule_results.items():
        # 아이템 단위 신호 집계: item -> [가중합, 가중치합, 기여자 set]
        stats = {}
        for sim, user in similar_users:
            if sim < min_sim:
                continue
            for fb in user.get("feedbacks", []):
                if fb.get("domain") != domain:
                    continue
                item = fb.get("item")
                v = THUMB_VALUE.get(fb.get("thumb"), 0.0)
                if not item or v == 0.0:
                    continue
                st = stats.setdefault(item, [0.0, 0.0, set()])
                st[0] += sim * v
                st[1] += sim
                st[2].add(user["id"])

        def score(item):
            st = stats.get(item)
            return st[0] / st[1] if st and st[1] > 0 else None

        rule_item = rec["item"]
        candidates = {it: score(it) for it, st in stats.items()
                      if len(st[2]) >= min_contrib and score(it) is not None}

        result = dict(rec)
        if candidates:
            best = max(candidates, key=candidates.get)
            rule_score = candidates.get(rule_item)  # None = 규칙 픽 데이터 없음
            if (best != rule_item and candidates[best] > 0
                    and (rule_score is None or candidates[best] - rule_score >= min_adv)):
                swapped = pool_item(domain, best)
                if swapped:
                    result = dict(swapped)
                    result["rule_item"] = rule_item      # 감사: 원래 규칙 픽
                    result["learned"] = True
                    result["learned_score"] = round(candidates[best], 3)
        out[domain] = result
    return out


def recommend(profile: dict, all_profiles: list = None,
              learning_gate: dict = None) -> dict:
    """통합 추천 함수

    - all_profiles가 없거나 비어있으면: 규칙 기반만 (cold-start)
    - all_profiles가 있으면: 규칙 → 학습 재랭킹(게이트) → 피드백 confidence 주석
    - learning_gate=None이면 config.LEARNING_GATE 로드 (기본 OFF = 규칙 top 불변)
    """
    rule_results = run_all_domains(profile)

    if not all_profiles:
        return rule_results

    if learning_gate is None:
        from config import LEARNING_GATE
        learning_gate = LEARNING_GATE

    similar = find_similar_users(profile, all_profiles)
    reranked = learned_rerank(rule_results, similar, learning_gate)
    return feedback_boost(reranked, similar)
