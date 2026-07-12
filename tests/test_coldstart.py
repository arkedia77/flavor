"""콜드스타트 예측기 + lift 하네스 테스트 — 파일럿 A (2026-07-12)

문헌 방향성 prior의 결정성·단조성과, lift 하네스의 신호 감지력/null 무반응을
합성 데이터로 검증. 서버·실데이터 불필요.
"""

import unittest

from engines.coldstart import (
    predict_coffee_type, cohort_bitter_prior, coffee_item_type,
    COFFEE_ITEM_TYPE, _P_MIN, _P_MAX,
)
from scripts.measure_coldstart_lift import (
    compute_lift, records_from_stored, _synthetic_records,
)


class TestCohortPrior(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(cohort_bitter_prior(50, "male"),
                         cohort_bitter_prior(50, "male"))

    def test_age_monotonic_increasing_bitter(self):
        vals = [cohort_bitter_prior(a, "male") for a in (20, 40, 60, 80)]
        self.assertEqual(vals, sorted(vals))
        self.assertLess(vals[0], vals[-1])

    def test_gender_effect_direction(self):
        # 남성이 여성보다 쓴맛 선호 사전확률 높음 (문헌)
        self.assertGreater(cohort_bitter_prior(40, "male"),
                           cohort_bitter_prior(40, "female"))
        self.assertAlmostEqual(cohort_bitter_prior(40, "unknown"), 0.5, places=3)

    def test_gender_token_normalization(self):
        for m in ("male", "M", "남", "남성"):
            self.assertGreater(cohort_bitter_prior(40, m), 0.5)
        for f in ("female", "F", "여", "여성"):
            self.assertLess(cohort_bitter_prior(40, f), 0.5)

    def test_clamped_bounds(self):
        self.assertGreaterEqual(cohort_bitter_prior(200, "male"), _P_MIN)
        self.assertLessEqual(cohort_bitter_prior(200, "male"), _P_MAX)
        self.assertGreaterEqual(cohort_bitter_prior(-100, "female"), _P_MIN)

    def test_none_age_neutral(self):
        self.assertAlmostEqual(cohort_bitter_prior(None, "unknown"), 0.5, places=3)


class TestPredict(unittest.TestCase):
    def test_cohort_only_matches_prior(self):
        p = predict_coffee_type(60, "male")
        self.assertEqual(p["method"], "cohort")
        self.assertEqual(p["p_bitter"], p["prior_bitter"])
        self.assertEqual(p["type"], "bitter")

    def test_seed_shifts_toward_bitter(self):
        base = predict_coffee_type(30, "female")["p_bitter"]
        seeded = predict_coffee_type(30, "female", ["에스프레소 진하게 블랙"])["p_bitter"]
        self.assertGreater(seeded, base)

    def test_seed_shifts_toward_acidic(self):
        base = predict_coffee_type(70, "male")["p_bitter"]
        seeded = predict_coffee_type(70, "male", ["바닐라라떼 달달하게"])["p_bitter"]
        self.assertLess(seeded, base)

    def test_strong_seed_can_flip_type(self):
        # 노년 남성(쓴맛 prior) + 강한 산미 seed → 산미형으로 뒤집힘
        self.assertEqual(
            predict_coffee_type(70, "male", ["바닐라 카라멜 라떼 달콤하게"])["type"],
            "acidic")

    def test_llm_infer_injection(self):
        # 주입된 LLM 우도가 키워드 대신 쓰임
        def fake_llm(_seed):
            return {"bitter": 10.0, "acidic": 1.0}
        p = predict_coffee_type(30, "female", ["뭐든"], llm_infer=fake_llm)
        self.assertEqual(p["type"], "bitter")

    def test_item_type_labels(self):
        self.assertEqual(coffee_item_type("스페셜티 싱글오리진 핸드드립"), "bitter")
        self.assertEqual(coffee_item_type("카페라떼·바닐라라떼"), "acidic")
        self.assertEqual(coffee_item_type("아이스 라떼·아메리카노"), "mixed")
        self.assertEqual(coffee_item_type("존재안함"), "unknown")

    def test_item_types_cover_pool(self):
        from engines.domains import DOMAIN_POOL
        pool_items = {r["item"] for r in DOMAIN_POOL["커피"]}
        self.assertEqual(pool_items, set(COFFEE_ITEM_TYPE.keys()),
                         "커피 풀 아이템과 타입 라벨 목록 불일치 (아이템 추가 시 갱신)")


class TestLiftHarness(unittest.TestCase):
    def test_signal_gives_positive_lift(self):
        r = compute_lift(_synthetic_records(4000, signal=True))
        self.assertGreater(r["concordance_lift"], 0.08)
        self.assertGreater(r["p_pos_match"], r["p_pos_mismatch"])

    def test_null_gives_near_zero_lift(self):
        r = compute_lift(_synthetic_records(4000, signal=False))
        self.assertLess(abs(r["concordance_lift"]), 0.06)

    def test_mixed_items_excluded(self):
        recs = [{"age": 60, "gender": "male", "shown_type": "mixed", "positive": True},
                {"age": 60, "gender": "male", "shown_type": "unknown", "positive": True}]
        r = compute_lift(recs)
        self.assertEqual(r["n_used"], 0)

    def test_records_from_stored_reconstruction(self):
        submissions = [{
            "id": "s1", "birth_date": "1960-03-03", "gender": "male",
            "results": {"커피": {"item": "스페셜티 싱글오리진 핸드드립"}},
        }]
        feedbacks = [{"submission_id": "s1", "domain": "커피", "thumb": 2},
                     {"submission_id": "s1", "domain": "음악", "thumb": 1}]  # 커피만 집계
        recs = records_from_stored(submissions, feedbacks, reference_year=2026)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["age"], 66)
        self.assertEqual(recs[0]["shown_type"], "bitter")
        self.assertTrue(recs[0]["positive"])


if __name__ == "__main__":
    unittest.main()
