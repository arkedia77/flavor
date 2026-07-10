"""engines/saju_features.py 단위 테스트 (unittest — 의존성 무추가)

실행: .venv/bin/python -m unittest discover tests/
"""

import json
import random
import unittest

from engines.saju_features import (
    ELEMENTS, SIKSHIN_GROUPS, SIPSIN_FLAVOR_MAP_V2, HIDDEN_STEMS_KR,
    extract_features, extract_features_from_birth, extract_features_from_pillars,
    flatten, sipsin_prior_delta, saju_prior_9d, _rel_elements, _sipsin_of,
)
from engines.sipsin import calc_sipsin, STEM_ELEMENT, PRODUCES


class TestAnchor(unittest.TestCase):
    """검증된 앵커: 1977-04-11 16시(신시) — 외부 만세력 대조 완료 명식"""

    @classmethod
    def setUpClass(cls):
        cls.f = extract_features(1977, 4, 11, 16)

    def test_pillars(self):
        self.assertEqual(self.f["pillars"],
                         {"년주": "정사", "월주": "갑진", "일주": "무술", "시주": "경신"})

    def test_day_master(self):
        self.assertEqual(self.f["day_master"],
                         {"stem": "무", "element": "토", "polarity": "양"})

    def test_sipsin_spot_checks(self):
        # 일간 무(토양) 기준: 년간 정(화음)→정인, 월간 갑(목양)→편관, 시간 경(금양)→식신
        self.assertEqual(_sipsin_of("무", "정"), "정인")
        self.assertEqual(_sipsin_of("무", "갑"), "편관")
        self.assertEqual(_sipsin_of("무", "경"), "식신")

    def test_gyeokguk(self):
        # 월지 진 본기 무 = 일간과 비견, 지장간 [무,을,계] 중 천간 투출 없음
        self.assertEqual(self.f["gyeokguk"],
                         {"name": "비견격", "group": "비겁", "tugan": False})

    def test_yongsin_rule(self):
        # 신강(0.4348) → 용신 ∈ {식상,재성,관성 오행}, 명식 내 최유력 = 금
        self.assertEqual(self.f["strength"]["label"], "신강")
        self.assertEqual(self.f["yongsin"]["element"], "금")
        self.assertEqual(self.f["yongsin"]["희신"], "토")  # 토생금

    def test_distributions_sum_to_one(self):
        self.assertAlmostEqual(sum(self.f["sipsin"]["strength"].values()), 1.0, delta=1e-3)  # 4자리 반올림 저장값 허용오차
        self.assertAlmostEqual(sum(self.f["sipsin"]["groups"].values()), 1.0, delta=1e-3)  # 4자리 반올림 저장값 허용오차
        self.assertAlmostEqual(sum(self.f["elements"]["weighted"].values()), 1.0, delta=1e-3)  # 4자리 반올림 저장값 허용오차


class TestHourUnknown(unittest.TestCase):
    def test_no_hour_pillar_and_flags(self):
        g = extract_features(1977, 4, 11, None)
        self.assertNotIn("시주", g["pillars"])
        self.assertFalse(g["input"]["hour_known"])
        self.assertTrue(len(g["degraded_features"]) > 0)
        self.assertAlmostEqual(sum(g["sipsin"]["strength"].values()), 1.0, delta=1e-3)  # 4자리 반올림 저장값 허용오차
        self.assertAlmostEqual(sum(g["elements"]["weighted"].values()), 1.0, delta=1e-3)  # 4자리 반올림 저장값 허용오차

    def test_hour_none_differs_from_noon(self):
        """12시 가짜 주입 금지 회귀: hour=None ≠ hour=12"""
        a = extract_features(1977, 4, 11, None)
        b = extract_features(1977, 4, 11, 12)
        self.assertNotEqual(a["sipsin"]["strength"], b["sipsin"]["strength"])

    def test_gyeokguk_invariant_to_hour(self):
        a = extract_features(1977, 4, 11, None)
        b = extract_features(1977, 4, 11, 16)
        self.assertEqual(a["gyeokguk"], b["gyeokguk"])

    def test_from_birth_parsing(self):
        # 비사주 트랙의 "12"는 신뢰 안 함 → hour_known=False
        f = extract_features_from_birth("1977-04-11", "12", trust_default_noon=False)
        self.assertFalse(f["input"]["hour_known"])
        # 사주 트랙은 12를 실제 선택으로 신뢰
        f = extract_features_from_birth("1977-04-11", "12", trust_default_noon=True)
        self.assertTrue(f["input"]["hour_known"])
        for bt in ("unknown", None, ""):
            f = extract_features_from_birth("1977-04-11", bt)
            self.assertFalse(f["input"]["hour_known"])
        f = extract_features_from_birth("1977-04-11", "16")
        self.assertTrue(f["input"]["hour_known"])


class TestYajasi(unittest.TestCase):
    def test_pin_lunar_23h_behavior(self):
        """야자시: lunar_python 기본 동작 고정 — 23시는 당일 일주 유지 + 자시"""
        f = extract_features(2020, 1, 1, 23)
        self.assertEqual(f["pillars"],
                         {"년주": "기해", "월주": "병자", "일주": "계묘", "시주": "갑자"})
        self.assertEqual(extract_features(2020, 1, 1, 12)["pillars"]["일주"], "계묘")


class TestProperties(unittest.TestCase):
    """고정 시드 임의 명식 300개 — 결정성/불변식"""

    @classmethod
    def setUpClass(cls):
        rng = random.Random(42)
        cls.cases = []
        for _ in range(300):
            y = rng.randint(1940, 2010)
            m = rng.randint(1, 12)
            d = rng.randint(1, 28)
            h = rng.choice([None] + list(range(24)))
            cls.cases.append((y, m, d, h))

    def test_deterministic_and_serializable(self):
        for y, m, d, h in self.cases[:50]:
            a = extract_features(y, m, d, h)
            b = extract_features(y, m, d, h)
            self.assertEqual(a, b)
            json.dumps(a, ensure_ascii=False)

    def test_invariants(self):
        for y, m, d, h in self.cases:
            f = extract_features(y, m, d, h)
            self.assertAlmostEqual(sum(f["sipsin"]["strength"].values()), 1.0, delta=1e-3)  # 4자리 반올림 저장값 허용오차
            self.assertTrue(0.0 <= f["strength"]["score"] <= 1.0)
            self.assertTrue(0.0 <= f["yinyang"]["yang_ratio"] <= 1.0)
            self.assertIn(f["yongsin"]["element"], ELEMENTS)
            self.assertTrue(0.0 <= f["elements"]["entropy"] <= 1.0)
            for v in f["interactions"].values():
                self.assertTrue(0.0 <= v <= 1.0, f"interaction out of range: {v}")

    def test_yongsin_rule_consistency(self):
        for y, m, d, h in self.cases:
            f = extract_features(y, m, d, h)
            day_el = f["day_master"]["element"]
            rel = _rel_elements(day_el)
            helper_els = {rel["비겁"], rel["인성"]}
            if f["strength"]["score"] < 0.36:
                self.assertIn(f["yongsin"]["element"], helper_els)
            else:
                self.assertNotIn(f["yongsin"]["element"], helper_els)


class TestPriorAndFlatten(unittest.TestCase):
    def test_prior_in_unit_range(self):
        f = extract_features(1977, 4, 11, 16)
        prior = saju_prior_9d(f)
        self.assertEqual(len(prior), 9)
        for v in prior.values():
            self.assertTrue(0.0 <= v <= 1.0)

    def test_map_v2_dims_valid(self):
        from config import DIMENSIONS
        for name, spec in SIPSIN_FLAVOR_MAP_V2.items():
            for dim in spec["delta"]:
                self.assertIn(dim, DIMENSIONS, f"{name}: unknown dim {dim}")
            self.assertIn(spec["evidence"], ("MBTI-p05", "실무"))

    def test_flatten_ascii_and_numeric(self):
        f = extract_features(1977, 4, 11, None)
        flat = flatten(f)
        for k, v in flat.items():
            self.assertTrue(k.isascii(), f"non-ascii key: {k}")
            self.assertIsInstance(v, float)
        self.assertEqual(flat["hour_known"], 0.0)


class TestPillarsPath(unittest.TestCase):
    """간지 직접 입력 경로 — 고전 명식 정답지 검증용"""

    def test_pillars_path_matches_date_path(self):
        a = extract_features(1977, 4, 11, 16)
        b = extract_features_from_pillars(
            {"년주": "정사", "월주": "갑진", "일주": "무술", "시주": "경신"})
        for k in ("pillars", "day_master", "sipsin", "strength", "yongsin",
                  "gyeokguk", "yinyang", "elements", "interactions"):
            self.assertEqual(a[k], b[k], f"{k} mismatch")

    def test_pillars_without_hour(self):
        f = extract_features_from_pillars(
            {"년주": "정사", "월주": "갑진", "일주": "무술"})
        self.assertFalse(f["input"]["hour_known"])
        self.assertNotIn("시주", f["pillars"])

    def test_invalid_pillar_raises(self):
        with self.assertRaises(ValueError):
            extract_features_from_pillars(
                {"년주": "정", "월주": "갑진", "일주": "무술"})

    def test_hidden_table_covers_all_branches(self):
        # lunar와 동일한 정적 테이블: 12지지 전부, index 0 = 본기
        self.assertEqual(len(HIDDEN_STEMS_KR), 12)
        self.assertEqual(HIDDEN_STEMS_KR["진"][0], "무")
        self.assertEqual(HIDDEN_STEMS_KR["사"][0], "병")
        self.assertEqual(HIDDEN_STEMS_KR["자"], ["계"])


class TestParamsOverride(unittest.TestCase):
    """민감도 분석용 파라미터 훅"""

    def test_default_params_identity(self):
        a = extract_features(1977, 4, 11, 16)
        b = extract_features(1977, 4, 11, 16, params={})
        self.assertEqual(a, b)

    def test_override_changes_result(self):
        flat = {"년간": 1.0, "월간": 1.0, "시간": 1.0,
                "년지": 1.0, "월지": 1.0, "일지": 1.0, "시지": 1.0}
        a = extract_features(1977, 4, 11, 16)
        b = extract_features(1977, 4, 11, 16, params={"palace_weights": flat})
        self.assertNotEqual(a["sipsin"]["strength"], b["sipsin"]["strength"])


class TestSipsinBugfixRegression(unittest.TestCase):
    def test_calc_sipsin_uses_bongi(self):
        """sipsin.py:135 회귀 — 지지 십신은 본기(index 0) 기준이어야 한다.

        1977-04-11: 년지 사 본기 병(화양)→편인, 월지 진 본기 무→비견,
        일지 술 본기 무→비견 (여기 기준이면 각각 비견/정재/정인으로 어긋남)
        """
        r = calc_sipsin(1977, 4, 11)
        dist = r["distribution"]
        # 천간: 정→정인, 갑→편관 / 지지 본기: 병→편인, 무→비견, 무→비견
        self.assertEqual(dist["비견"], 2)
        self.assertEqual(dist["편인"], 1)
        self.assertEqual(dist["정인"], 1)
        self.assertEqual(dist["편관"], 1)


if __name__ == "__main__":
    unittest.main()
