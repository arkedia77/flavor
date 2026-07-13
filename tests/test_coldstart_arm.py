"""콜드스타트 랜덤 노출 arm + LLM 우도 인터페이스 테스트 (2026-07-13)

fableself 점검 Q2/Q3 대응 구현 검증:
- 랜덤 arm 게이트 OFF = 완전 항등(노출·태그 무변경)
- ON = random_frac 비율만큼 풀 무작위 노출 + _arm 태그(random/rule)
- lift 하네스가 _arm 태그로 랜덤 arm만 필터해 무교란 추정
- LLM 우도 어댑터: 파싱·클램프·폴백
서버·실데이터 불필요.
"""

import random
import unittest

from engines.coldstart import apply_random_arm, build_llm_infer, _LLM_LR_CAP
from engines.domains import DOMAIN_POOL, run_all_domains
from config import load_coldstart_arm, _ARM_OFF
from scripts.measure_coldstart_lift import records_from_stored, compute_lift


def _sample_results():
    prof = {d: 0.5 for d in
            ["social", "adventurous", "aesthetic", "comfort",
             "budget", "maximalist", "energetic", "urban", "bitter"]}
    return run_all_domains(prof)


class TestArmGateOff(unittest.TestCase):
    def test_none_config_identity(self):
        r = _sample_results()
        self.assertIs(apply_random_arm(r, None, random.Random(1)), r)

    def test_disabled_identity(self):
        r = _sample_results()
        cfg = {"enabled": False, "random_frac": 0.5, "domains": ["커피"]}
        out = apply_random_arm(r, cfg, random.Random(1))
        self.assertIs(out, r)
        self.assertNotIn("_arm", out["커피"])  # 태그 없음

    def test_zero_frac_identity(self):
        r = _sample_results()
        cfg = {"enabled": True, "random_frac": 0.0, "domains": ["커피"]}
        self.assertIs(apply_random_arm(r, cfg, random.Random(1)), r)

    def test_default_config_is_off(self):
        cfg = load_coldstart_arm()  # config/coldstart_arm.json
        self.assertFalse(cfg["enabled"])
        self.assertEqual(cfg["random_frac"], 0.0)


class TestArmGateOn(unittest.TestCase):
    def test_does_not_mutate_input(self):
        r = _sample_results()
        before = r["커피"]["item"]
        cfg = {"enabled": True, "random_frac": 1.0, "domains": ["커피"]}
        apply_random_arm(r, cfg, random.Random(1))
        self.assertEqual(r["커피"]["item"], before)  # 원본 불변
        self.assertNotIn("_arm", r["커피"])

    def test_frac_one_always_random_tag(self):
        r = _sample_results()
        cfg = {"enabled": True, "random_frac": 1.0, "domains": ["커피"]}
        out = apply_random_arm(r, cfg, random.Random(7))
        self.assertEqual(out["커피"]["_arm"], "random")
        self.assertIn("_rule_item", out["커피"])
        # 랜덤 픽은 반드시 풀 안의 아이템
        pool_items = {x["item"] for x in DOMAIN_POOL["커피"]}
        self.assertIn(out["커피"]["item"], pool_items)

    def test_frac_zero_effective_all_rule(self):
        r = _sample_results()
        cfg = {"enabled": True, "random_frac": 0.0001, "domains": ["커피"]}
        # frac>0이라 게이트는 켜지고 태그는 붙되, 거의 항상 rule
        out = apply_random_arm(r, cfg, random.Random(1))
        self.assertIn(out["커피"]["_arm"], ("rule", "random"))

    def test_untargeted_domain_untouched(self):
        r = _sample_results()
        cfg = {"enabled": True, "random_frac": 1.0, "domains": ["커피"]}
        out = apply_random_arm(r, cfg, random.Random(1))
        self.assertNotIn("_arm", out["음악"])  # 대상 아닌 도메인은 무변경

    def test_frac_split_approximately(self):
        # 많은 시행에서 random 비율이 frac에 근접
        cfg = {"enabled": True, "random_frac": 0.3, "domains": ["커피"]}
        rng = random.Random(20260713)
        n = 4000
        n_random = 0
        base = _sample_results()
        for _ in range(n):
            out = apply_random_arm(base, cfg, rng)
            if out["커피"]["_arm"] == "random":
                n_random += 1
        self.assertAlmostEqual(n_random / n, 0.3, delta=0.03)


class TestArmFilterInHarness(unittest.TestCase):
    def _subs(self):
        # 랜덤 arm 아이템(bitter) + 규칙 arm 아이템(acidic) 혼재
        return [
            {"id": "r1", "birth_date": "1980-01-01", "gender": "male",
             "results": {"커피": {"item": "에스프레소·아이스 아메리카노", "_arm": "random"}}},
            {"id": "u1", "birth_date": "1980-01-01", "gender": "male",
             "results": {"커피": {"item": "카페라떼·바닐라라떼", "_arm": "rule"}}},
            {"id": "old", "birth_date": "1980-01-01", "gender": "male",
             "results": {"커피": {"item": "에스프레소·아이스 아메리카노"}}},  # 태그 없음=rule
        ]

    def _fbs(self):
        return [
            {"submission_id": "r1", "domain": "커피", "thumb": 1},
            {"submission_id": "u1", "domain": "커피", "thumb": 1},
            {"submission_id": "old", "domain": "커피", "thumb": 1},
        ]

    def test_random_arm_filter(self):
        recs = records_from_stored(self._subs(), self._fbs(), 2026, arm="random")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["arm"], "random")

    def test_rule_arm_includes_untagged(self):
        recs = records_from_stored(self._subs(), self._fbs(), 2026, arm="rule")
        self.assertEqual(len(recs), 2)  # u1 + 태그없는 old

    def test_all_arm(self):
        recs = records_from_stored(self._subs(), self._fbs(), 2026, arm="all")
        self.assertEqual(len(recs), 3)

    def test_seeds_read_from_meta(self):
        subs = [{"id": "s1", "birth_date": "1980-01-01", "gender": "male",
                 "results": {"커피": {"item": "에스프레소·아이스 아메리카노", "_arm": "random"},
                             "_coldstart": {"seeds": ["아메리카노 진하게"]}}}]
        fbs = [{"submission_id": "s1", "domain": "커피", "thumb": 1}]
        recs = records_from_stored(subs, fbs, 2026, arm="all")
        self.assertEqual(recs[0]["seeds"], ["아메리카노 진하게"])


class TestLLMInfer(unittest.TestCase):
    def test_parse_valid(self):
        infer = build_llm_infer(lambda p: '{"bitter": 2.0, "acidic": 0.6}')
        out = infer("아메리카노만")
        self.assertEqual(out["bitter"], 2.0)
        self.assertEqual(out["acidic"], 0.6)

    def test_clamp_to_cap(self):
        infer = build_llm_infer(lambda p: '{"bitter": 99, "acidic": 0.001}')
        out = infer("x")
        self.assertEqual(out["bitter"], _LLM_LR_CAP)
        self.assertEqual(out["acidic"], 1.0 / _LLM_LR_CAP)

    def test_garbage_falls_back_neutral(self):
        infer = build_llm_infer(lambda p: "모르겠어요")
        self.assertEqual(infer("x"), {"bitter": 1.0, "acidic": 1.0})

    def test_exception_falls_back_neutral(self):
        def boom(p):
            raise RuntimeError("api down")
        infer = build_llm_infer(boom)
        self.assertEqual(infer("x"), {"bitter": 1.0, "acidic": 1.0})

    def test_prose_wrapped_json(self):
        infer = build_llm_infer(lambda p: 'JSON: {"bitter": 1.5, "acidic": 0.8} 입니다')
        out = infer("x")
        self.assertEqual(out["bitter"], 1.5)


class TestLoaderFailSafe(unittest.TestCase):
    def test_bad_frac_falls_back(self):
        import json
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix=".json")
        os.write(fd, json.dumps({"enabled": True, "random_frac": 5.0}).encode())
        os.close(fd)
        try:
            cfg = load_coldstart_arm(path)
            self.assertEqual(cfg["random_frac"], 0.0)  # 범위 초과 → 0 폴백
        finally:
            os.unlink(path)

    def test_missing_file_off(self):
        cfg = load_coldstart_arm("/nonexistent/path.json")
        self.assertEqual(cfg, dict(_ARM_OFF))


if __name__ == "__main__":
    unittest.main()
