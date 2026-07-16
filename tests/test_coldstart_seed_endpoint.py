"""콜드스타트 seed 온보딩 프론트 배선 검증 (2026-07-16)

- /api/coldstart-config 게이트 노출: 기본 OFF → seed_collection=false(프론트 문항 미노출),
  ON 패치 시 true. 프론트는 이 플래그로만 seed 문항을 띄운다 = OFF면 현 흐름 항등.
- submit이 payload seeds[]를 results._coldstart.seeds에 저장하는지(프론트가 보내는 필드).
서버 기동만 필요, 실데이터 불필요.
"""

import unittest
from unittest import mock

import api.public
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


if __name__ == "__main__":
    unittest.main()
