"""검증 하네스 v1.1 단위 테스트 — EVIDENCE_AUDIT 완화책 4 (2026-07-12)

합성 데이터로 노출 전 서브셋 / 네거티브 컨트롤 / 신봉도 층화 / 메타 추출 검증.
서버·실데이터 불필요 (Leo 지침: 이론적 토대 검증 우선).
"""

import unittest

from config import DIMENSIONS
from scripts.data_io import dedupe_persons, extract_meta_answers
from scripts.validate_saju_signal import (
    confirmatory, negative_control, belief_stratified, first_measured_dims,
    innate_agreement,
)


def make_sub(sid, name="유저", created="2026-08-01T10:00:00", dims_measured=None,
             survey=None, with_meta=True, belief=1.0, nc=1.0):
    """신형 A/B 퀴즈 제출 합성"""
    dims_measured = dims_measured or ["social", "adventurous"]
    answers = [{"id": f"q{i}", "dimension": d, "choice": "A", "value": 0.8,
                "innate_value": 0.6, "agreed_with_innate": True,
                "response_ms": 900, "ux": "nv1"}
               for i, d in enumerate(dims_measured)]
    if with_meta:
        answers.append({"id": "nc_noodle", "dimension": "nc_noodle", "meta": True,
                        "choice": "A", "value": nc, "response_ms": 700, "ux": "nv1"})
        answers.append({"id": "meta_belief", "dimension": "meta_belief", "meta": True,
                        "choice": "A", "value": belief, "response_ms": 700, "ux": "nv1"})
    return {
        "id": sid, "name": name, "birth_date": "1990-05-05", "birth_time": "12",
        "gender": "F", "raw_answers": answers,
        "survey": survey or {d: 0.5 for d in DIMENSIONS},
        "profile_version": "v0.2_vol4_travel", "created_at": created,
    }


def make_person(i, prior, survey, belief=None, nc=None):
    """confirmatory/nc/belief 함수 직접 입력용 person 합성"""
    meta = {}
    if belief is not None:
        meta["meta_belief"] = belief
    if nc is not None:
        meta["nc_noodle"] = nc
    return {"key": (f"p{i}", "1990-01-01", "F"), "prior": prior, "survey": survey,
            "survey_first": survey, "meta": meta,
            "_first_dims": set(DIMENSIONS), "hour_known": False}


def spread(i, n):
    """[0.1, 0.9] 균등 분포 값"""
    return 0.1 + 0.8 * i / max(1, n - 1)


class TestMetaExtraction(unittest.TestCase):
    def test_extract_meta_answers(self):
        sub = make_sub("s1", belief=1.0, nc=0.0)
        meta = extract_meta_answers(sub)
        self.assertEqual(meta, {"nc_noodle": 0.0, "meta_belief": 1.0})

    def test_extract_meta_absent_in_legacy(self):
        sub = make_sub("s1", with_meta=False)
        self.assertEqual(extract_meta_answers(sub), {})
        # vol1 구형 dict 포맷도 빈 dict
        self.assertEqual(extract_meta_answers({"raw_answers": {"q1": 0.5}}), {})

    def test_dedupe_carries_meta_and_first_survey(self):
        s1 = make_sub("s1", created="2026-08-01T10:00:00", belief=1.0, nc=1.0,
                      survey={**{d: 0.5 for d in DIMENSIONS}, "social": 0.9})
        s2 = make_sub("s2", created="2026-08-02T10:00:00", belief=0.0, nc=1.0,
                      survey={**{d: 0.5 for d in DIMENSIONS}, "social": 0.1})
        persons = dedupe_persons([s2, s1])  # 순서 뒤집어 넣어도 시간순 첫 제출
        self.assertEqual(len(persons), 1)
        p = persons[0]
        self.assertAlmostEqual(p["survey"]["social"], 0.5)        # 평균
        self.assertAlmostEqual(p["survey_first"]["social"], 0.9)  # 첫 제출
        self.assertAlmostEqual(p["meta"]["meta_belief"], 0.5)     # 평균
        self.assertAlmostEqual(p["meta"]["nc_noodle"], 1.0)
        self.assertEqual(len(p["submissions"]), 2)  # innate_agreement용 원본

    def test_first_measured_dims(self):
        s1 = make_sub("s1", dims_measured=["social", "bitter"])
        p = dedupe_persons([s1])[0]
        self.assertEqual(first_measured_dims(p), {"social", "bitter"})

    def test_first_measured_dims_vol1_dict_format(self):
        sub = make_sub("s1")
        sub["raw_answers"] = {"q1": 0.5, "q2": 0.7}  # 27문항 구형 포맷
        p = dedupe_persons([sub])[0]
        self.assertEqual(first_measured_dims(p), set(DIMENSIONS))

    def test_innate_agreement_counts_after_fix(self):
        # 종전엔 dedupe 출력에 submissions가 없어 항상 0건이던 버그 회귀 가드
        persons = dedupe_persons([make_sub("s1")])
        ia = innate_agreement(persons)
        self.assertGreater(ia["n_items"], 0)
        # 메타 문항(agreed_with_innate 없음)은 집계에 안 섞임
        self.assertEqual(ia["n_items"], 2)


class TestConfirmatoryV11(unittest.TestCase):
    def test_dim_filter_and_survey_key(self):
        n = 12
        persons = []
        for i in range(n):
            v = spread(i, n)
            prior = {d: v for d in DIMENSIONS}
            survey = {d: 1 - v for d in DIMENSIONS}       # 평균 응답: 음의 상관
            p = make_person(i, prior, survey)
            p["survey_first"] = {d: v for d in DIMENSIONS}  # 첫 응답: 양의 상관
            p["_first_dims"] = {"social"}                   # social만 실측
            persons.append(p)
        res = confirmatory(persons, "t", survey_key="survey_first",
                           dim_filter=lambda p, d: d in p["_first_dims"])
        self.assertEqual(res["per_dim"]["social"]["n"], n)
        self.assertEqual(res["per_dim"]["adventurous"]["n"], 0)  # 필터로 전원 제외
        self.assertGreater(res["per_dim"]["social"]["rho"], 0.99)  # first 기준 양의 상관


class TestNegativeControl(unittest.TestCase):
    def test_no_meta_no_flag(self):
        persons = [make_person(i, {d: 0.5 for d in DIMENSIONS},
                               {d: 0.5 for d in DIMENSIONS}) for i in range(15)]
        nc = negative_control(persons)
        self.assertFalse(nc["flag"])
        self.assertEqual(nc["n_tests"], 0)

    def test_planted_signal_raises_flag(self):
        # nc가 prior social과 완전 상관 → CONFIRMED 동등 기준 충족 → flag
        n = 40
        persons = []
        for i in range(n):
            v = spread(i, n)
            prior = {d: (v if d == "social" else 0.5 + 0.01 * (i % 3)) for d in DIMENSIONS}
            persons.append(make_person(i, prior, {d: 0.5 for d in DIMENSIONS},
                                       nc=1.0 if v >= 0.5 else 0.0))
        nc = negative_control(persons)
        self.assertTrue(nc["flag"])
        self.assertTrue(any(r["prior_dim"] == "social" for r in nc["flagged"]))

    def test_noise_no_flag(self):
        n = 40
        persons = []
        for i in range(n):
            v = spread(i, n)
            prior = {d: v for d in DIMENSIONS}
            persons.append(make_person(i, prior, {d: 0.5 for d in DIMENSIONS},
                                       nc=float(i % 2)))  # prior와 무관한 교대값
        nc = negative_control(persons)
        self.assertFalse(nc["flag"])


class TestBeliefStratified(unittest.TestCase):
    def test_insufficient_stratum(self):
        persons = [make_person(i, {d: 0.5 for d in DIMENSIONS},
                               {d: 0.5 for d in DIMENSIONS}, belief=1.0)
                   for i in range(30)]  # 비신봉군 0명
        out = belief_stratified(persons, {"per_dim": {}})
        self.assertIn("note", out)
        self.assertEqual(out["self_attribution_suspect"], [])

    def test_believer_only_signal_flagged(self):
        # 신봉군에서만 prior↔survey 상관, 비신봉군은 무상관 → suspect
        persons = []
        n = 25
        for i in range(n):  # 신봉군: 강한 양의 상관
            v = spread(i, n)
            persons.append(make_person(i, {d: v for d in DIMENSIONS},
                                       {d: v for d in DIMENSIONS}, belief=1.0))
        for i in range(n):  # 비신봉군: survey가 교대값 (상관 없음)
            v = spread(i, n)
            persons.append(make_person(100 + i, {d: v for d in DIMENSIONS},
                                       {d: 0.4 + 0.2 * (i % 2) for d in DIMENSIONS},
                                       belief=0.0))
        conf_primary = {"per_dim": {"social": {"verdict": "CONFIRMED", "rho": 0.5}}}
        out = belief_stratified(persons, conf_primary)
        self.assertIn("social", out["self_attribution_suspect"])


if __name__ == "__main__":
    unittest.main()
