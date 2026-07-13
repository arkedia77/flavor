"""콜드스타트 예측기 + lift 하네스 테스트 — 파일럿 A (2026-07-12, 축 정직화 2026-07-13)

축 a: 진한 블랙형(black) vs 부드러운 스위트형(sweet). 문헌 방향성 prior의 결정성·단조성,
seed 우도의 패밀리 계상·총 LR 캡, lift 하네스의 신호 감지력/null 무반응을 합성 데이터로
검증. 서버·실데이터 불필요.
"""

import unittest

from engines.coldstart import (
    predict_coffee_type, cohort_black_prior, coffee_item_type,
    COFFEE_ITEM_TYPE, _P_MIN, _P_MAX, _SEED_TOTAL_LR_CAP,
)
from scripts.measure_coldstart_lift import (
    compute_lift, records_from_stored, _synthetic_records,
)


class TestCohortPrior(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(cohort_black_prior(50, "male"),
                         cohort_black_prior(50, "male"))

    def test_age_monotonic_increasing_black(self):
        vals = [cohort_black_prior(a, "male") for a in (20, 40, 60, 80)]
        self.assertEqual(vals, sorted(vals))
        self.assertLess(vals[0], vals[-1])

    def test_gender_effect_direction(self):
        # 남성이 여성보다 블랙 선호 사전확률 높음 (쓴맛 내성 문헌)
        self.assertGreater(cohort_black_prior(40, "male"),
                           cohort_black_prior(40, "female"))
        self.assertAlmostEqual(cohort_black_prior(40, "unknown"), 0.5, places=3)

    def test_gender_token_normalization(self):
        for m in ("male", "M", "남", "남성"):
            self.assertGreater(cohort_black_prior(40, m), 0.5)
        for f in ("female", "F", "여", "여성"):
            self.assertLess(cohort_black_prior(40, f), 0.5)

    def test_clamped_bounds(self):
        self.assertGreaterEqual(cohort_black_prior(200, "male"), _P_MIN)
        self.assertLessEqual(cohort_black_prior(200, "male"), _P_MAX)
        self.assertGreaterEqual(cohort_black_prior(-100, "female"), _P_MIN)

    def test_none_age_neutral(self):
        self.assertAlmostEqual(cohort_black_prior(None, "unknown"), 0.5, places=3)

    def test_age_pivot_override(self):
        # pivot을 유저 평균 연령으로 올리면 같은 연령의 블랙 prior가 내려간다(계통편향 교정)
        self.assertLess(cohort_black_prior(30, "unknown", age_pivot=50),
                        cohort_black_prior(30, "unknown", age_pivot=40))


class TestPredict(unittest.TestCase):
    def test_cohort_only_matches_prior(self):
        p = predict_coffee_type(60, "male")
        self.assertEqual(p["method"], "cohort")
        self.assertEqual(p["p_black"], p["prior_black"])
        self.assertEqual(p["type"], "black")

    def test_seed_shifts_toward_black(self):
        base = predict_coffee_type(30, "female")["p_black"]
        seeded = predict_coffee_type(30, "female", ["에스프레소 진하게 블랙"])["p_black"]
        self.assertGreater(seeded, base)

    def test_seed_shifts_toward_sweet(self):
        base = predict_coffee_type(70, "male")["p_black"]
        seeded = predict_coffee_type(70, "male", ["바닐라라떼 달달하게"])["p_black"]
        self.assertLess(seeded, base)

    def test_strong_seed_flips_neutral_prior(self):
        # 중립 prior(40 unknown) + 강한 스위트 seed → 스위트형으로 뒤집힘
        self.assertEqual(
            predict_coffee_type(40, "unknown", ["바닐라 카라멜 라떼 달콤하게"])["type"],
            "sweet")

    def test_total_lr_cap_saturates(self):
        # fableself Q3: 총 우도비 캡. 스위트 패밀리 3개면 이미 1.6^3>cap → 더 쌓아도 동일
        p3 = predict_coffee_type(70, "male", ["바닐라 라떼 달달"])["p_black"]
        p_many = predict_coffee_type(
            70, "male", ["바닐라 카라멜 시럽 라떼 플랫화이트 달달 달콤 오트 연하"])["p_black"]
        self.assertAlmostEqual(p3, p_many, places=6)

    def test_cap_prevents_full_override(self):
        # 강한 prior(70 male, 0.76)는 캡된 seed로 완전히 뒤집히지 않음
        p = predict_coffee_type(70, "male", ["바닐라 카라멜 라떼 달콤"])["p_black"]
        self.assertGreater(p, 0.45)  # 0.5 근처까지만 밀림, 극단 방지

    def test_family_dedup_no_double_count(self):
        # 같은 패밀리 키워드 반복은 1회만 계상 (아메리카노+룽고=블랙 패밀리 1개)
        one = predict_coffee_type(40, "unknown", ["아메리카노"])["p_black"]
        same_fam = predict_coffee_type(40, "unknown", ["아메리카노 룽고"])["p_black"]
        self.assertAlmostEqual(one, same_fam, places=6)

    def test_reserved_acidity_kw_inert(self):
        # 축 b 예약어(핸드드립·산미)는 현재 우도에 영향 없음 → 코호트와 동일
        base = predict_coffee_type(40, "unknown")["p_black"]
        seeded = predict_coffee_type(40, "unknown", ["산미 있는 핸드드립"])["p_black"]
        self.assertAlmostEqual(base, seeded, places=6)

    def test_llm_infer_injection(self):
        # 주입된 LLM 우도가 키워드 대신 쓰임 (총 LR 캡 적용)
        def fake_llm(_seed):
            return {"black": 10.0, "sweet": 1.0}
        p = predict_coffee_type(30, "female", ["뭐든"], llm_infer=fake_llm)
        self.assertEqual(p["type"], "black")

    def test_item_type_labels(self):
        self.assertEqual(coffee_item_type("스페셜티 싱글오리진 핸드드립"), "black")
        self.assertEqual(coffee_item_type("카페라떼·바닐라라떼"), "sweet")
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
        self.assertEqual(recs[0]["shown_type"], "black")
        self.assertTrue(recs[0]["positive"])


if __name__ == "__main__":
    unittest.main()
