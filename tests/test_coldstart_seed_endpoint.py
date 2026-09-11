"""콜드스타트 seed 온보딩 프론트 배선 검증 (2026-07-16)

- /api/coldstart-config 게이트 노출: OFF 패치 → seed_collection=false(프론트 문항 미노출),
  ON 패치 → true. 프론트는 이 플래그로만 seed 문항을 띄운다 = OFF면 현 흐름 항등.
  ★2026-09-11: ON/OFF **둘 다 명시 패치**로 잰다. 실 config 파일의 개방 여부는
  Leo 승인 사항이라 테스트가 못박지 않는다(못박았던 탓에 8/14 개방 후 28일 적색).
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

    def test_gate_off_hides_seed(self):
        """게이트 OFF면 false 노출 → 프론트 문항 미노출(현 흐름 항등).

        ★2026-09-11 교체: 종전엔 **실 config 파일이 OFF라는 전제**로 패치 없이 쟀다.
        8/14 LEO 승인 개방(e4ff290) 후 그 전제가 깨져 28일간 적색 ⇒ OFF 경로는
        ON 경로(test_gate_on_exposes_true)와 **대칭으로 명시 패치**해서 잰다.
        """
        patched = dict(api.public.COLDSTART_ARM)
        patched["seed_collection"] = False
        with mock.patch.object(api.public, "COLDSTART_ARM", patched):
            resp = self.client.get("/api/coldstart-config")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json(), {"seed_collection": False})

    def test_live_config_is_reflected(self):
        """엔드포인트가 **실 config를 그대로** 비추는지 — 값 자체는 고정하지 않는다.

        실 파일의 개방 여부는 Leo 승인 사항이라 여기서 못박지 않는다(그걸 못박았던 것이
        28일 적색의 원인). 여기서 보증하는 계약은 「서버가 제 config를 반영한다」 하나다.
        실 파일의 버전 고정은 test_coldstart_arm.LIVE_GATE_VERSION이 담당한다.
        """
        resp = self.client.get("/api/coldstart-config")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["seed_collection"],
                         bool(api.public.COLDSTART_ARM.get("seed_collection")))

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

    def _off(self):
        """★2026-09-11 신설 — OFF 경로도 _on()과 대칭으로 명시 패치한다.
        종전엔 실 config가 OFF라는 전제로 패치 없이 쟀고, 8/14 개방 후 깨졌다."""
        patched = dict(api.submit.COLDSTART_ARM)
        patched["seed_collection"] = False
        return mock.patch.object(api.submit, "COLDSTART_ARM", patched)

    def test_gate_off_no_reveal_identity(self):
        with self._off():
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
