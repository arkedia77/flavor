"""v0.2 게이트 블렌드 + 피드백 경로 테스트"""

import json
import os
import tempfile
import unittest

from config import load_saju_gate, DIMENSIONS
from engines.gated_blend import apply_gated_blend, any_weight_open
from engines.recommend import feedback_boost, THUMB_VALUE


SURVEY = {"social": 0.7, "adventurous": 0.31, "aesthetic": 0.55, "comfort": 0.42,
          "budget": 0.9, "maximalist": 0.13, "energetic": 0.66, "urban": 0.5,
          "bitter": 0.777}
PRIOR = {d: 0.5 for d in DIMENSIONS}


class TestGatedBlend(unittest.TestCase):
    def test_zero_weights_identity(self):
        """핵심 보증: 가중치 전부 0 → profile == survey 비트 단위 일치"""
        gate = {"weights": {d: 0.0 for d in DIMENSIONS}, "require_hour_known": True}
        profile, applied = apply_gated_blend(SURVEY, PRIOR, gate, hour_known=True)
        self.assertEqual(profile, SURVEY)
        self.assertFalse(any_weight_open(applied))

    def test_open_weight_blends(self):
        gate = {"weights": {**{d: 0.0 for d in DIMENSIONS}, "social": 0.2},
                "require_hour_known": True}
        profile, applied = apply_gated_blend(SURVEY, PRIOR, gate, hour_known=True)
        self.assertAlmostEqual(profile["social"], 0.8 * 0.7 + 0.2 * 0.5, places=3)
        self.assertEqual(profile["budget"], SURVEY["budget"])  # 닫힌 차원은 불변
        self.assertTrue(any_weight_open(applied))

    def test_hour_unknown_closes_gate(self):
        gate = {"weights": {**{d: 0.0 for d in DIMENSIONS}, "social": 0.2},
                "require_hour_known": True}
        profile, applied = apply_gated_blend(SURVEY, PRIOR, gate, hour_known=False)
        self.assertEqual(profile, SURVEY)
        self.assertFalse(any_weight_open(applied))

    def test_missing_prior_closes_gate(self):
        gate = {"weights": {**{d: 0.0 for d in DIMENSIONS}, "social": 0.2}}
        profile, applied = apply_gated_blend(SURVEY, None, gate, hour_known=True)
        self.assertEqual(profile, SURVEY)


class TestGateLoader(unittest.TestCase):
    def test_current_gate_file_all_zero(self):
        """리포에 커밋된 게이트는 전부 0이어야 한다 (개방은 Leo 승인 커밋으로만)"""
        gate = load_saju_gate()
        self.assertNotEqual(gate["gate_version"], "fail-safe-zero")  # 파일은 정상 로드
        self.assertTrue(all(w == 0.0 for w in gate["weights"].values()))

    def _load_tmp(self, content: str) -> dict:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fp:
            fp.write(content)
            path = fp.name
        try:
            return load_saju_gate(path)
        finally:
            os.unlink(path)

    def test_failsafe_on_garbage(self):
        gate = self._load_tmp("{not json")
        self.assertEqual(gate["gate_version"], "fail-safe-zero")

    def test_failsafe_on_negative_weight(self):
        bad = {"max_weight": 0.3, "weights": {**{d: 0.0 for d in DIMENSIONS}, "social": -0.1}}
        gate = self._load_tmp(json.dumps(bad))
        self.assertEqual(gate["gate_version"], "fail-safe-zero")

    def test_failsafe_on_exceeding_max(self):
        bad = {"max_weight": 0.3, "weights": {**{d: 0.0 for d in DIMENSIONS}, "social": 0.5}}
        gate = self._load_tmp(json.dumps(bad))
        self.assertEqual(gate["gate_version"], "fail-safe-zero")

    def test_failsafe_on_missing_file(self):
        gate = load_saju_gate("/nonexistent/gate.json")
        self.assertEqual(gate["gate_version"], "fail-safe-zero")


class TestFeedbackBoost(unittest.TestCase):
    RULES = {"커피": {"item": "아메리카노", "reason": "r", "description": "d"}}

    def _user(self, uid, thumb):
        return (0.8, {"id": uid, "profile": {}, "feedbacks": [{"domain": "커피", "thumb": thumb}]})

    def test_strong_like_counts_as_up(self):
        """구버전 버그 회귀: 🎯(thumb=2)는 up이어야 한다"""
        similar = [self._user(f"u{i}", 2) for i in range(3)]
        out = feedback_boost(self.RULES, similar)
        self.assertEqual(out["커피"]["confidence"], 1.0)
        self.assertEqual(out["커피"]["feedback_signal"]["down"], 0)

    def test_weighted_votes(self):
        # 🎯(+1.0), 👍(+0.5), 👎(-1.0) → up=0.8*1.5=1.2, down=0.8, total=1.6
        similar = [self._user("a", 2), self._user("b", 1), self._user("c", -2)]
        out = feedback_boost(self.RULES, similar)
        sig = out["커피"]["feedback_signal"]
        self.assertAlmostEqual(sig["up"], 1.2, places=2)
        self.assertAlmostEqual(sig["down"], 0.8, places=2)
        self.assertAlmostEqual(out["커피"]["confidence"], 0.6, places=2)

    def test_min_contributors(self):
        similar = [self._user("a", 2), self._user("b", 2)]  # 2명 < 3명
        out = feedback_boost(self.RULES, similar)
        self.assertIsNone(out["커피"]["confidence"])

    def test_item_never_changes(self):
        similar = [self._user(f"u{i}", -2) for i in range(5)]
        out = feedback_boost(self.RULES, similar)
        self.assertEqual(out["커피"]["item"], "아메리카노")


if __name__ == "__main__":
    unittest.main()
