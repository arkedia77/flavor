"""콜드스타트 seed 온보딩 프론트 배선 검증 (2026-07-16)

- /api/coldstart-config 게이트 노출: 기본 OFF → seed_collection=false(프론트 문항 미노출),
  ON 패치 시 true. 프론트는 이 플래그로만 seed 문항을 띄운다 = OFF면 현 흐름 항등.
- submit이 payload seeds[]를 results._coldstart.seeds에 저장하는지(프론트가 보내는 필드).
서버 기동만 필요, 실데이터 불필요.
"""

import os
import tempfile
import unittest
from unittest import mock

import api.public
import api.submit
from app import create_app


class TestColdstartConfigEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_default_off(self):
        """기본 config(coldstart_arm.json)는 seed_collection=false → 프론트 문항 미노출."""
        resp = self.client.get("/api/coldstart-config")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"seed_collection": False})

    def test_gate_on_exposes_true(self):
        """게이트 개방 시 true 노출(리셋 시점 Leo 승인 커밋 시나리오)."""
        patched = dict(api.public.COLDSTART_ARM)
        patched["seed_collection"] = True
        with mock.patch.object(api.public, "COLDSTART_ARM", patched):
            resp = self.client.get("/api/coldstart-config")
            self.assertTrue(resp.get_json()["seed_collection"])

    def test_no_arm_assignment_leaked(self):
        """프론트엔 배정 규칙(랜덤 arm) 미노출 — seed 수집만 담당."""
        resp = self.client.get("/api/coldstart-config")
        self.assertEqual(set(resp.get_json().keys()), {"seed_collection"})


class TestFeedbackReveal(unittest.TestCase):
    """피드백 응답의 커피 자아 리빌 (fableself 결정: lock 후 산출물). 게이트로 게이팅."""

    _SURVEY = {d: 0.5 for d in
               ["social", "adventurous", "aesthetic", "comfort",
                "budget", "maximalist", "energetic", "urban", "bitter"]}

    @classmethod
    def setUpClass(cls):
        cls._fd, cls._db = tempfile.mkstemp(suffix=".db")
        os.close(cls._fd)
        cls._prev = os.environ.get("DB_PATH")
        os.environ["DB_PATH"] = cls._db
        from db.connection import init_db
        init_db()

    @classmethod
    def tearDownClass(cls):
        if cls._prev is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = cls._prev
        os.unlink(cls._db)

    def setUp(self):
        self.client = create_app().test_client()

    def _submit(self, seeds):
        p = {"name": "t", "birth_date": "1990-05-05", "birth_time": "12",
             "gender": "M", "quiz_type": "vol4_travel", "survey": self._SURVEY, "seeds": seeds}
        return self.client.post("/api/submit", json=p).get_json()["id"]

    def _on(self):
        patched = dict(api.submit.COLDSTART_ARM)
        patched["seed_collection"] = True
        return mock.patch.object(api.submit, "COLDSTART_ARM", patched)

    def test_gate_off_no_reveal_identity(self):
        rid = self._submit(["아메리카노 진하게"])
        fb = self.client.post("/api/feedback",
                              json={"submission_id": rid, "domain": "커피", "thumb": 1}).get_json()
        self.assertEqual(set(fb.keys()), {"status"})

    def test_gate_on_coffee_returns_reveal(self):
        with self._on():
            rid = self._submit(["아메리카노 진하게"])
            fb = self.client.post("/api/feedback",
                                  json={"submission_id": rid, "domain": "커피", "thumb": 1}).get_json()
            self.assertIn("reveal", fb)
            self.assertIn("name", fb["reveal"])
            self.assertEqual(fb["reveal"]["snapshot"], "지금 이 순간의 커피 취향")

    def test_gate_on_noncoffee_no_reveal(self):
        with self._on():
            rid = self._submit(["아메리카노 진하게"])
            fb = self.client.post("/api/feedback",
                                  json={"submission_id": rid, "domain": "향수", "thumb": 1}).get_json()
            self.assertNotIn("reveal", fb)


if __name__ == "__main__":
    unittest.main()
