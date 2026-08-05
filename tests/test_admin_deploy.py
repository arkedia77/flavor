"""자가배포 엔드포인트(/api/admin/deploy) 리로드 경로 고정.

배경: leoserver 실측에서 `logs/gunicorn.pid`가 stale(31344=사망, 실제 마스터=1758506)이었다.
옛 구현은 그 PID에 SIGHUP을 쏘고 실패를 삼킨 뒤 **HTTP 200**을 돌려줬다 —
git pull만 되고 구코드가 계속 도는 '조용한 실패'. 아래 테스트가 그 회귀를 막는다.
"""

import os
import unittest
from unittest import mock

from api import admin


class ResolveGunicornMasterTest(unittest.TestCase):
    def test_부모가_gunicorn이면_그_PID를_돌려준다(self):
        with mock.patch.object(admin.os, "getppid", return_value=4242), \
             mock.patch.object(admin, "_cmdline", return_value="/venv/bin/python /venv/bin/gunicorn app:app"):
            pid, cmd, err = admin.resolve_gunicorn_master()
        self.assertEqual(pid, 4242)
        self.assertIsNone(err)

    def test_부모가_gunicorn이_아니면_시그널_대상을_주지_않는다(self):
        """무관한 프로세스에 SIGHUP(기본 동작=종료)을 쏘는 사고를 막는 가드."""
        with mock.patch.object(admin.os, "getppid", return_value=4242), \
             mock.patch.object(admin, "_cmdline", return_value="/bin/zsh"):
            pid, cmd, err = admin.resolve_gunicorn_master()
        self.assertIsNone(pid)
        self.assertIn("gunicorn", err)

    def test_고아_프로세스면_거부한다(self):
        with mock.patch.object(admin.os, "getppid", return_value=1):
            pid, _, err = admin.resolve_gunicorn_master()
        self.assertIsNone(pid)

    def test_PID_파일은_더_이상_참조하지_않는다(self):
        """stale PID 파일이 버그의 근원이었다 — 모듈에서 제거됐는지 고정."""
        self.assertFalse(hasattr(admin, "PID_FILE"))


class DeployEndpointTest(unittest.TestCase):
    def setUp(self):
        os.environ["ADMIN_TOKEN"] = "test-token"
        from app import create_app
        self.app = create_app()
        self.client = self.app.test_client()
        self.headers = {"Authorization": "Bearer test-token"}

    def tearDown(self):
        os.environ.pop("ADMIN_TOKEN", None)

    def _fake_pull_ok(self, *a, **k):
        return mock.Mock(returncode=0, stdout="Already up to date.", stderr="")

    def test_무토큰은_403(self):
        self.assertEqual(self.client.post("/api/admin/deploy").status_code, 403)

    def test_리로드_실패는_200이_아니라_500(self):
        """★핵심 회귀 가드 — 옛 구현은 여기서 200을 돌려줬다."""
        with mock.patch.object(admin.subprocess, "run", side_effect=self._fake_pull_ok), \
             mock.patch.object(admin, "resolve_gunicorn_master", return_value=(None, "/bin/zsh", "부모가 gunicorn이 아님")):
            resp = self.client.post("/api/admin/deploy", headers=self.headers)
        self.assertEqual(resp.status_code, 500)
        body = resp.get_json()
        self.assertEqual(body["status"], "error")
        self.assertEqual(body["step"], "reload")
        self.assertIn("systemctl restart", body["hint"])

    def test_리로드_성공시_ok와_master_pid(self):
        killed = []
        with mock.patch.object(admin.subprocess, "run", side_effect=self._fake_pull_ok), \
             mock.patch.object(admin, "resolve_gunicorn_master", return_value=(4242, "gunicorn app:app", None)), \
             mock.patch.object(admin.os, "kill", side_effect=lambda p, s: killed.append((p, s))):
            resp = self.client.post("/api/admin/deploy", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["reload"], "ok")
        self.assertEqual(body["master_pid"], 4242)
        self.assertEqual(killed, [(4242, admin.signal.SIGHUP)])

    def test_SIGHUP이_던지면_500(self):
        with mock.patch.object(admin.subprocess, "run", side_effect=self._fake_pull_ok), \
             mock.patch.object(admin, "resolve_gunicorn_master", return_value=(4242, "gunicorn app:app", None)), \
             mock.patch.object(admin.os, "kill", side_effect=ProcessLookupError("No such process")):
            resp = self.client.post("/api/admin/deploy", headers=self.headers)
        self.assertEqual(resp.status_code, 500)
        self.assertIn("SIGHUP", resp.get_json()["reload"])


if __name__ == "__main__":
    unittest.main()
