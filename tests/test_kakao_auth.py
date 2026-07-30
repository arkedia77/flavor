"""카카오 로그인 배선 검증 (2026-07-30)

fail-safe 원칙: 키/시크릿 미설정 = 로그인 OFF → /api/me enabled=false, 라우트 503,
                submit은 user_id=None(익명 흐름 항등). = 사주/학습/콜드스타트 게이트와 동일.
ON 경로: 카카오 HTTP 두 함수(_exchange_code_for_token/_fetch_kakao_user)를 주입(monkeypatch)해
         네트워크 없이 콜백 → upsert → 세션 → submit user_id 부착까지 검증.
"""

import os
import sqlite3
import tempfile
import unittest
from unittest import mock

import api.auth
import api.submit
from app import create_app


_SURVEY = {d: 0.5 for d in
           ["social", "adventurous", "aesthetic", "comfort",
            "budget", "maximalist", "energetic", "urban", "bitter"]}


class _DBTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._fd, cls._db = tempfile.mkstemp(suffix=".db")
        os.close(cls._fd)
        cls._prev = os.environ.get("DB_PATH")
        os.environ["DB_PATH"] = cls._db
        # DB_PATH는 import 시점 값으로 db.connection/config에 박혀 있으므로 직접 패치해야
        # init_db·submit·직접 sqlite 읽기가 모두 동일 tempfile을 가리킨다.
        import config
        import db.connection as dbconn
        cls._prev_cfg, cls._prev_conn = config.DB_PATH, dbconn.DB_PATH
        config.DB_PATH = cls._db
        dbconn.DB_PATH = cls._db
        dbconn.init_db()

    @classmethod
    def tearDownClass(cls):
        import config
        import db.connection as dbconn
        config.DB_PATH = cls._prev_cfg
        dbconn.DB_PATH = cls._prev_conn
        if cls._prev is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = cls._prev
        os.unlink(cls._db)

    def setUp(self):
        self.client = create_app().test_client()


class TestLoginOff(_DBTest):
    """기본 OFF — 로그인 기능이 익명 흐름을 전혀 바꾸지 않음."""

    def test_api_me_disabled(self):
        m = self.client.get("/api/me").get_json()
        self.assertFalse(m["enabled"])
        self.assertFalse(m["logged_in"])

    def test_login_route_503(self):
        self.assertEqual(self.client.get("/auth/kakao/login").status_code, 503)

    def test_callback_route_503(self):
        self.assertEqual(
            self.client.get("/auth/kakao/callback?code=x&state=y").status_code, 503)

    def test_submit_anonymous_user_id_null(self):
        rid = self.client.post("/api/submit", json={
            "name": "익명", "birth_date": "1990-05-05", "birth_time": "12",
            "gender": "M", "quiz_type": "vol4_travel", "survey": _SURVEY,
        }).get_json()["id"]
        conn = sqlite3.connect(self._db)
        uid = conn.execute("SELECT user_id FROM submissions WHERE id=?", (rid,)).fetchone()[0]
        conn.close()
        self.assertIsNone(uid)


class TestUserUpsert(_DBTest):
    """kakao_id 안정 키 — 같은 카카오 유저는 재로그인해도 동일 user_id(dedup)."""

    def test_upsert_idempotent_and_updates(self):
        from db.repository import upsert_user_by_kakao, get_user
        uid1 = upsert_user_by_kakao(77777, "닉A", "a@e.com")
        uid2 = upsert_user_by_kakao(77777, "닉B", "b@e.com")   # 재로그인 = 같은 id
        self.assertEqual(uid1, uid2)
        u = get_user(uid1)
        self.assertEqual(u["kakao_id"], "77777")
        self.assertEqual(u["nickname"], "닉B")                 # 최신값으로 갱신
        self.assertEqual(u["email"], "b@e.com")

    def test_get_user_none(self):
        from db.repository import get_user
        self.assertIsNone(get_user(None))
        self.assertIsNone(get_user("nonexistent"))


class TestLoginOn(_DBTest):
    """ON — 네트워크 함수 주입으로 콜백 전 과정 검증."""

    def _on(self):
        return mock.patch.object(api.auth, "KAKAO_LOGIN_ENABLED", True)

    def test_login_redirects_to_kakao(self):
        with self._on(), \
             mock.patch.object(api.auth, "KAKAO_REST_API_KEY", "testkey"):
            resp = self.client.get("/auth/kakao/login?next=/food")
            self.assertEqual(resp.status_code, 302)
            self.assertTrue(resp.headers["Location"].startswith(api.auth.KAKAO_AUTHORIZE_URL))

    def test_callback_invalid_state_rejected(self):
        with self._on():
            with self.client.session_transaction() as s:
                s["kakao_oauth_state"] = "expected"
            resp = self.client.get("/auth/kakao/callback?code=c&state=WRONG")
            self.assertEqual(resp.status_code, 400)

    def test_callback_full_flow_sets_session_and_user(self):
        fake_token = {"access_token": "tok"}
        fake_user = {"id": 314159,
                     "kakao_account": {"profile": {"nickname": "테스터"}, "email": "t@e.com"}}
        with self._on(), \
             mock.patch.object(api.auth, "_exchange_code_for_token", return_value=fake_token), \
             mock.patch.object(api.auth, "_fetch_kakao_user", return_value=fake_user):
            with self.client.session_transaction() as s:
                s["kakao_oauth_state"] = "st1"
                s["kakao_next"] = "/food"
            resp = self.client.get("/auth/kakao/callback?code=c&state=st1")
            self.assertEqual(resp.status_code, 302)
            self.assertTrue(resp.headers["Location"].endswith("/food"))

            # 세션 확립 확인
            me = self.client.get("/api/me").get_json()
            self.assertTrue(me["logged_in"])
            self.assertEqual(me["nickname"], "테스터")

            # 로그인 상태 제출 → submission.user_id 부착
            rid = self.client.post("/api/submit", json={
                "name": "테스터", "birth_date": "1988-08-08", "birth_time": "12",
                "gender": "M", "quiz_type": "vol4_travel", "survey": _SURVEY,
            }).get_json()["id"]
            conn = sqlite3.connect(self._db)
            uid = conn.execute("SELECT user_id FROM submissions WHERE id=?", (rid,)).fetchone()[0]
            kakao = conn.execute("SELECT kakao_id FROM users WHERE id=?", (uid,)).fetchone()[0]
            conn.close()
            self.assertIsNotNone(uid)
            self.assertEqual(kakao, "314159")

    def test_logout_clears_session(self):
        with self._on():
            with self.client.session_transaction() as s:
                s["user_id"] = "u1"
                s["nickname"] = "n"
            resp = self.client.get("/auth/logout?next=/")
            self.assertEqual(resp.status_code, 302)
            me = self.client.get("/api/me").get_json()
            self.assertFalse(me["logged_in"])

    def test_callback_open_redirect_blocked(self):
        """next에 외부 URL 넣어도 내부 '/'로 강제(오픈 리다이렉트 방지)."""
        fake_token = {"access_token": "tok"}
        fake_user = {"id": 1, "kakao_account": {"profile": {"nickname": "x"}}}
        with self._on(), \
             mock.patch.object(api.auth, "_exchange_code_for_token", return_value=fake_token), \
             mock.patch.object(api.auth, "_fetch_kakao_user", return_value=fake_user):
            with self.client.session_transaction() as s:
                s["kakao_oauth_state"] = "st2"
                s["kakao_next"] = "//evil.com"
            resp = self.client.get("/auth/kakao/callback?code=c&state=st2")
            self.assertTrue(resp.headers["Location"].endswith("/"))
            self.assertNotIn("evil.com", resp.headers["Location"])


class TestSessionCookieFlags(_DBTest):
    """세션 쿠키 보안 플래그 — 로그인 개방 전 고정.

    Secure는 시크릿이 주입된 운영(=로그인 ON)에서만 켜진다. 로컬 http 개발에서
    켜지면 세션이 아예 안 붙어 콜백이 깨지므로 조건부여야 한다.
    """

    def test_flags_off_when_no_secret(self):
        with mock.patch("app.FLASK_SECRET_KEY", ""):
            app = create_app()
        self.assertTrue(app.config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual(app.config["SESSION_COOKIE_SAMESITE"], "Lax")
        self.assertFalse(app.config["SESSION_COOKIE_SECURE"])

    def test_secure_on_when_secret_present(self):
        with mock.patch("app.FLASK_SECRET_KEY", "fixed-secret"):
            app = create_app()
        self.assertTrue(app.config["SESSION_COOKIE_SECURE"])
        self.assertEqual(app.secret_key, "fixed-secret")


if __name__ == "__main__":
    unittest.main()
