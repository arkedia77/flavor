# -*- coding: utf-8 -*-
"""PII 엔드포인트 인증 게이트 고정 (2026-09-27).

배경: `/api/results`가 **무인증 200**으로 참가자 `name`·`birth_date`·`gender`를
내보내고 있었다(09-24 발견). 당시 DB가 0행이라 `[]`만 나와 «무해하게 보였을» 뿐이고,
***유통을 여는 순간 실제 참가자 데이터가 공개 URL로 다운로드되는*** 자리였다.
`/api/calibration-data`(생년월일+시+성별+원답안)와 `/dashboard`도 같은 자리였다.

★이 파일의 설계 원칙 — **닫힘만 재지 않는다.**
「403이 난다」만 고정하면 **모든 경로가 403인 서비스**도 초록으로 읽힌다(=무출력을
초록으로 읽는 그 오류). 그래서 ⑴정토큰 200 ⑵공개 경로 200을 **양성통제**로 같이 박는다.
"""

import json
import os
import unittest


PII_FIELDS = (b"name", b"birth_date", b"gender")
GATED_JSON = ("/api/results", "/api/calibration-data")


class _AppCase(unittest.TestCase):
    """ADMIN_TOKEN을 setUp에서 주입 — env 상태가 게이트 판정의 유일한 입력이다."""

    TOKEN = "test-admin-token"

    def setUp(self):
        self._saved = os.environ.get("ADMIN_TOKEN")
        os.environ["ADMIN_TOKEN"] = self.TOKEN
        from app import create_app
        self.client = create_app().test_client()
        self.auth = {"Authorization": f"Bearer {self.TOKEN}"}

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("ADMIN_TOKEN", None)
        else:
            os.environ["ADMIN_TOKEN"] = self._saved


class GatedJsonEndpointTest(_AppCase):
    def test_무토큰이면_403(self):
        for path in GATED_JSON:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_틀린_토큰이면_403(self):
        for path in GATED_JSON:
            with self.subTest(path=path):
                resp = self.client.get(path, headers={"Authorization": "Bearer wrong"})
                self.assertEqual(resp.status_code, 403)

    def test_403_본문에_PII_필드명이_없다(self):
        """거절 응답이 스키마를 흘리지 않는지 — 0행이라 안 보이는 것과 구분한다."""
        for path in GATED_JSON:
            with self.subTest(path=path):
                body = self.client.get(path).data
                for field in PII_FIELDS:
                    self.assertNotIn(field, body)

    def test_정토큰이면_200이고_실제_데이터_모양이다(self):
        """★양성통제 — 게이트가 「전부 막기」가 아니라 「토큰으로 연다」임을 고정."""
        resp = self.client.get("/api/results", headers=self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), list)

        resp = self.client.get("/api/calibration-data", headers=self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("engine_version", resp.get_json())

    def test_X_Admin_Token_헤더도_받는다(self):
        resp = self.client.get("/api/results", headers={"X-Admin-Token": self.TOKEN})
        self.assertEqual(resp.status_code, 200)

    def test_JSON_API는_쿼리스트링_토큰을_받지_않는다(self):
        """⚠쿼리스트링은 액세스 로그·리퍼러에 남는다 — 기계용 API에는 열지 않는다."""
        for path in GATED_JSON:
            with self.subTest(path=path):
                resp = self.client.get(f"{path}?token={self.TOKEN}")
                self.assertEqual(resp.status_code, 403)

    def test_비ASCII_토큰을_보내도_500이_아니라_403(self):
        """compare_digest에 str을 넘기면 TypeError=500이 됐을 자리(bytes로 넘긴다)."""
        resp = self.client.get("/api/results", headers={"X-Admin-Token": "한글토큰"})
        self.assertEqual(resp.status_code, 403)


class FailClosedTest(unittest.TestCase):
    """★ADMIN_TOKEN 미설정 = 사고의 다른 얼굴. 「깜박했다」로도 열리면 안 된다."""

    def setUp(self):
        self._saved = os.environ.pop("ADMIN_TOKEN", None)
        from app import create_app
        self.client = create_app().test_client()

    def tearDown(self):
        if self._saved is not None:
            os.environ["ADMIN_TOKEN"] = self._saved

    def test_토큰_미설정이면_어떤_헤더로도_안_열린다(self):
        for path in GATED_JSON + ("/api/admin/export", "/dashboard"):
            with self.subTest(path=path):
                for headers in ({}, {"Authorization": "Bearer "}, {"X-Admin-Token": ""}):
                    self.assertEqual(self.client.get(path, headers=headers).status_code, 403)


class DashboardPageTest(_AppCase):
    def test_무토큰이면_403(self):
        self.assertEqual(self.client.get("/dashboard").status_code, 403)

    def test_쿼리_토큰으로_열린다(self):
        """브라우저 주소창은 헤더를 못 붙인다 — 페이지에만 `?token=`을 허용한다."""
        resp = self.client.get(f"/dashboard?token={self.TOKEN}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"<html", resp.data.lower())

    def test_거절_응답은_색인_거부_헤더를_붙인다(self):
        self.assertIn("noindex", self.client.get("/dashboard").headers.get("X-Robots-Tag", ""))


class PublicSurfaceStillOpenTest(_AppCase):
    """★양성통제 — 과잉 차단 회귀 가드. 유입 경로를 같이 닫으면 제품이 죽는다."""

    OPEN_PATHS = ("/", "/health", "/robots.txt", "/api/coldstart-config",
                  "/cafe-saju", "/survey")

    def test_공개_경로는_무토큰_200이다(self):
        for path in self.OPEN_PATHS:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_제출_경로는_토큰_없이_동작한다(self):
        """참가자 흐름(/api/submit)은 공개다 — 여길 닫으면 수집이 0이 된다."""
        payload = {"name": "GATE_TEST", "birth_year": 1990, "birth_month": 5,
                   "birth_day": 15, "birth_hour": 14, "gender": "male",
                   "answers": {}, "quiz_type": "cafe_saju"}
        resp = self.client.post("/api/submit", data=json.dumps(payload),
                                content_type="application/json")
        self.assertNotEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
