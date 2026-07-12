"""학습 루프(게이트) 테스트 — 유사유저 피드백 기반 아이템 재랭킹 (2026-07-12)

핵심 보증: 게이트 OFF → recommend 출력이 규칙 결과와 **완전 동일** (v0.1 동작).
게이트 ON → 유사 유저가 강하게 선호한 풀 아이템으로 승격, 약신호/소표본은 미변경.
서버·실데이터 불필요.
"""

import copy
import unittest

from config import DIMENSIONS
from engines.domains import run_all_domains, DOMAIN_POOL, pool_item, _DOMAIN_FUNCS
from engines.recommend import recommend, learned_rerank, find_similar_users

GATE_OFF = {"enabled": False, "min_sim": 0.3, "min_contributors": 3, "min_advantage": 0.5}
GATE_ON = {"enabled": True, "min_sim": 0.3, "min_contributors": 3, "min_advantage": 0.5}


def prof(**kw):
    p = {d: 0.5 for d in DIMENSIONS}
    p.update(kw)
    return p


class TestDomainPool(unittest.TestCase):
    EXPECTED = {"커피": 8, "향수": 5, "음악": 6, "식당": 5,
                "운동": 6, "여행": 6, "패션": 6, "인테리어": 6}

    def test_pool_counts(self):
        for domain, n in self.EXPECTED.items():
            self.assertEqual(len(DOMAIN_POOL[domain]), n,
                             f"{domain} 풀 크기 {len(DOMAIN_POOL[domain])} != {n} "
                             "(아이템 추가/삭제 시 이 기대값 갱신)")

    def test_pool_covers_rule_outputs(self):
        # 독립 랜덤 그리드에서 규칙이 산출하는 모든 아이템이 풀에 있어야 함
        import random
        rng = random.Random(999)
        for _ in range(3000):
            p = {d: rng.random() for d in DIMENSIONS}
            for domain, fn in _DOMAIN_FUNCS.items():
                item = fn(p)["item"]
                self.assertIsNotNone(pool_item(domain, item),
                                     f"{domain} 아이템 {item!r}가 풀에 없음")

    def test_pool_items_have_full_shape(self):
        for domain, items in DOMAIN_POOL.items():
            for rec in items:
                self.assertTrue(rec.get("item") and rec.get("reason"))


class TestGateOffIdentity(unittest.TestCase):
    """게이트 OFF → 규칙 결과와 항등 (피드백 있어도 아이템 불변)"""

    def _fake_profiles(self, target):
        # 타깃과 유사한 유저들이 규칙 픽과 다른 아이템에 강한 👍를 준 상황
        users = []
        for i in range(5):
            users.append({
                "id": f"u{i}", "profile": dict(target),
                "feedbacks": [{"domain": "커피", "thumb": 2,
                               "item": "달달한 라떼·플랫화이트"}],
            })
        return users

    def test_gate_off_matches_rule_items(self):
        target = prof(bitter=0.9, budget=0.7)  # 규칙상 핸드드립
        rule = run_all_domains(target)
        out = recommend(target, self._fake_profiles(target), learning_gate=GATE_OFF)
        for domain in rule:
            self.assertEqual(out[domain]["item"], rule[domain]["item"],
                             f"게이트 OFF인데 {domain} 아이템이 바뀜")
            self.assertNotIn("learned", out[domain])

    def test_gate_off_equals_no_gate_default(self):
        # 기본 config.LEARNING_GATE(=OFF)와 명시적 GATE_OFF 결과 동일
        target = prof(energetic=0.8, social=0.7)
        a = recommend(target, self._fake_profiles(target))  # config 기본(OFF)
        b = recommend(target, self._fake_profiles(target), learning_gate=GATE_OFF)
        self.assertEqual({d: a[d]["item"] for d in a},
                         {d: b[d]["item"] for d in b})


class TestGateOnRerank(unittest.TestCase):
    def _rule_results(self, target):
        return run_all_domains(target)

    def test_strong_signal_swaps_item(self):
        target = prof(bitter=0.9, budget=0.7)
        rule = self._rule_results(target)
        rule_coffee = rule["커피"]["item"]
        # 규칙 픽과 다른, 풀에 존재하는 아이템
        alt = next(r["item"] for r in DOMAIN_POOL["커피"] if r["item"] != rule_coffee)
        similar = [(0.9, {"id": f"u{i}", "profile": dict(target),
                          "feedbacks": [{"domain": "커피", "thumb": 2, "item": alt}]})
                   for i in range(4)]
        out = learned_rerank(rule, similar, GATE_ON)
        self.assertEqual(out["커피"]["item"], alt)
        self.assertTrue(out["커피"]["learned"])
        self.assertEqual(out["커피"]["rule_item"], rule_coffee)
        # reason/description이 풀에서 정확히 따라옴
        self.assertEqual(out["커피"]["reason"], pool_item("커피", alt)["reason"])

    def test_insufficient_contributors_no_swap(self):
        target = prof(bitter=0.9, budget=0.7)
        rule = self._rule_results(target)
        alt = next(r["item"] for r in DOMAIN_POOL["커피"] if r["item"] != rule["커피"]["item"])
        # 기여자 2명 < min_contributors 3
        similar = [(0.9, {"id": f"u{i}", "profile": dict(target),
                          "feedbacks": [{"domain": "커피", "thumb": 2, "item": alt}]})
                   for i in range(2)]
        out = learned_rerank(rule, similar, GATE_ON)
        self.assertEqual(out["커피"]["item"], rule["커피"]["item"])

    def test_negative_signal_no_swap(self):
        # 대안 아이템이 순부정(👎)이면 승격하지 않음
        target = prof(bitter=0.9, budget=0.7)
        rule = self._rule_results(target)
        alt = next(r["item"] for r in DOMAIN_POOL["커피"] if r["item"] != rule["커피"]["item"])
        similar = [(0.9, {"id": f"u{i}", "profile": dict(target),
                          "feedbacks": [{"domain": "커피", "thumb": -2, "item": alt}]})
                   for i in range(4)]
        out = learned_rerank(rule, similar, GATE_ON)
        self.assertEqual(out["커피"]["item"], rule["커피"]["item"])

    def test_advantage_margin_respected(self):
        # 규칙 픽도 대안도 👍지만 우열 margin이 min_advantage 미만이면 미변경
        target = prof(bitter=0.9, budget=0.7)
        rule = self._rule_results(target)
        rule_item = rule["커피"]["item"]
        alt = next(r["item"] for r in DOMAIN_POOL["커피"] if r["item"] != rule_item)
        # 둘 다 thumb=1(0.5). margin 0 < 0.5 → 미변경
        similar = []
        for i in range(4):
            similar.append((0.9, {"id": f"a{i}", "profile": dict(target),
                                  "feedbacks": [{"domain": "커피", "thumb": 1, "item": rule_item}]}))
            similar.append((0.9, {"id": f"b{i}", "profile": dict(target),
                                  "feedbacks": [{"domain": "커피", "thumb": 1, "item": alt}]}))
        out = learned_rerank(rule, similar, GATE_ON)
        self.assertEqual(out["커피"]["item"], rule_item)

    def test_only_target_domain_affected(self):
        target = prof(bitter=0.9, budget=0.7)
        rule = self._rule_results(target)
        alt = next(r["item"] for r in DOMAIN_POOL["커피"] if r["item"] != rule["커피"]["item"])
        similar = [(0.9, {"id": f"u{i}", "profile": dict(target),
                          "feedbacks": [{"domain": "커피", "thumb": 2, "item": alt}]})
                   for i in range(4)]
        out = learned_rerank(rule, similar, GATE_ON)
        for domain in rule:
            if domain != "커피":
                self.assertEqual(out[domain]["item"], rule[domain]["item"])

    def test_rerank_does_not_mutate_input(self):
        target = prof(bitter=0.9, budget=0.7)
        rule = self._rule_results(target)
        snapshot = copy.deepcopy(rule)
        alt = next(r["item"] for r in DOMAIN_POOL["커피"] if r["item"] != rule["커피"]["item"])
        similar = [(0.9, {"id": f"u{i}", "profile": dict(target),
                          "feedbacks": [{"domain": "커피", "thumb": 2, "item": alt}]})
                   for i in range(4)]
        learned_rerank(rule, similar, GATE_ON)
        self.assertEqual(rule, snapshot)  # 원본 불변


if __name__ == "__main__":
    unittest.main()
