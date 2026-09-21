"""유입 출처 계측 테스트 (2026-09-21, LEO 승인)

- parse_source: 순수 파싱(Flask 무의존) — 화이트리스트·상한·fail-safe
- /api/submit 배선: Referer의 utm이 source_json에 저장되고, 없으면 **NULL**(항등)
★핵심 계약 = **출처가 없을 때 기존 동작과 완전히 같아야 한다.** 「{}」를 남기면
  「출처 없음(직접 유입)」과 「계측 전(옛 행)」이 구분 안 된다.
"""

import json
import os

import unittest

from engines.source import parse_source, UTM_KEYS, _MAX_VALUE


class TestParseSource(unittest.TestCase):
    def test_none_and_empty_are_empty_dict(self):
        self.assertEqual(parse_source(None), {})
        self.assertEqual(parse_source(""), {})

    def test_no_query_is_empty(self):
        """utm 없는 평범한 진입 = 직접 유입 → 빈 dict(→ 호출 측이 NULL로)."""
        self.assertEqual(parse_source("https://flavor.arkedia.work/cafe-saju"), {})

    def test_extracts_utm_and_landing_path(self):
        u = "https://flavor.arkedia.work/cafe-saju?utm_source=instagram&utm_medium=story"
        out = parse_source(u)
        self.assertEqual(out["utm_source"], "instagram")
        self.assertEqual(out["utm_medium"], "story")
        self.assertEqual(out["landing_path"], "/cafe-saju")

    def test_all_five_utm_keys(self):
        q = "&".join(f"{k}=v{i}" for i, k in enumerate(UTM_KEYS))
        out = parse_source(f"https://x/y?{q}")
        for i, k in enumerate(UTM_KEYS):
            self.assertEqual(out[k], f"v{i}")

    def test_non_whitelisted_params_dropped(self):
        """⛔화이트리스트 — utm 외 파라미터는 «버린다»(raw URL 저장 안 함)."""
        out = parse_source("https://x/y?utm_source=a&token=SECRET&email=me@x.com")
        self.assertEqual(out["utm_source"], "a")
        self.assertNotIn("token", out)
        self.assertNotIn("email", out)
        self.assertNotIn("SECRET", json.dumps(out))

    def test_landing_path_only_when_utm_present(self):
        """utm이 하나도 없으면 경로도 안 남긴다 — 직접 유입은 완전히 빈 값."""
        self.assertEqual(parse_source("https://x/cafe?foo=bar"), {})

    def test_value_length_capped(self):
        out = parse_source("https://x/y?utm_source=" + "A" * 500)
        self.assertEqual(len(out["utm_source"]), _MAX_VALUE)

    def test_blank_value_ignored(self):
        self.assertEqual(parse_source("https://x/y?utm_source=&utm_medium=ig"),
                         {"utm_medium": "ig", "landing_path": "/y"})

    def test_garbage_url_is_failsafe(self):
        """⛔파싱 실패가 제출을 막으면 안 된다 — 조용히 빈 dict."""
        for bad in ("::::", "http://[", 12345, object()):
            self.assertIsInstance(parse_source(bad), dict)

    def test_extra_whitelist(self):
        out = parse_source(None, {"ref_host": "t.co", "ip": "1.2.3.4"})
        self.assertEqual(out, {"ref_host": "t.co"})
        self.assertNotIn("ip", out)


class TestSubmitStoresSource(unittest.TestCase):
    """서버 배선 — Referer만으로 잡히는지(프론트 무변경 설계의 핵심 주장)."""

    _SURVEY = {d: 0.5 for d in
               ["social", "adventurous", "aesthetic", "comfort",
                "budget", "maximalist", "energetic", "urban", "bitter"]}

    @classmethod
    def setUpClass(cls):
        # ⛔`config.DB_PATH`는 **import 시점에 고정**된다(`config.py:6`). 그래서 여기서 env를
        # 바꿔도 앱은 이미 잡힌 경로를 쓴다 ⇒ ★**테스트가 파일을 «직접» 열면 안 된다.**
        # 읽기도 앱과 «같은» `get_db_connection()`으로 한다(기존 테스트들이 무사했던 이유).
        from db.connection import init_db
        init_db()

    def setUp(self):
        from app import create_app
        self.client = create_app().test_client()

    def _submit(self, referer=None):
        p = {"name": "t", "birth_date": "1990-05-05", "birth_time": "12",
             "gender": "M", "quiz_type": "vol4_travel", "survey": self._SURVEY}
        headers = {"Referer": referer} if referer else {}
        return self.client.post("/api/submit", json=p, headers=headers).get_json()["id"]

    def _source_of(self, rid):
        from db.connection import get_db_connection
        conn = get_db_connection()
        try:
            row = conn.execute(
                "select source_json from submissions where id=?", (rid,)).fetchone()
        finally:
            conn.close()
        return row[0]

    def test_utm_from_referer_is_stored(self):
        rid = self._submit("https://flavor.arkedia.work/travel?utm_source=kakao&utm_medium=chat")
        stored = json.loads(self._source_of(rid))
        self.assertEqual(stored["utm_source"], "kakao")
        self.assertEqual(stored["utm_medium"], "chat")
        self.assertEqual(stored["landing_path"], "/travel")

    def test_no_referer_stores_null(self):
        """★항등 계약 — 직접 유입은 NULL이어야 한다(빈 dict '{}'가 아니라)."""
        self.assertIsNone(self._source_of(self._submit()))

    def test_referer_without_utm_stores_null(self):
        self.assertIsNone(self._source_of(self._submit("https://flavor.arkedia.work/travel")))


class TestWalMode(unittest.TestCase):
    """WAL 전환 (2026-09-21, LEO 승인 · admin 찬성)."""

    def test_init_db_sets_wal(self):
        """init_db 후 실 DB의 journal_mode가 wal이어야 한다.

        ⛔`importlib.reload(config)`로 임시 DB를 끼우지 «않는다» — 그 reload는 모듈 전역을
        갈아서 **같은 프로세스의 뒤 테스트들을 깨뜨린다**(실제로 3건 깨뜨렸다). 앱이 실제로
        쓰는 연결을 그대로 재는 것이 계약에도 더 가깝다.
        """
        from db.connection import init_db, get_db_connection
        init_db()
        conn = get_db_connection()
        try:
            mode = conn.execute("pragma journal_mode").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(str(mode).lower(), "wal")


if __name__ == "__main__":
    unittest.main()
