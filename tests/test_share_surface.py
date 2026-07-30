"""공유 표면(OG/메타·결과 페이지 이스케이프) 회귀 테스트 — 유통 준비.

배경: 퀴즈 40여 페이지에 OG 태그가 없어 카톡/트위터 미리보기가 비어 나왔다.
      scripts/inject_og_tags.py로 주입했고, 여기서 그 상태가 유지되는지 지킨다.
      아울러 /result는 유저 입력 닉네임을 템플릿에 박으므로 이스케이프를 고정한다.
"""

import os
import re
import sqlite3
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_SURVEY = {f"q{i}": 3 for i in range(1, 28)}


class TestQuizPageOG(unittest.TestCase):
    """퀴즈 HTML이 공유 메타를 갖추고 있는가."""

    REQUIRED = ["og:title", "og:description", "og:url", "og:image", "twitter:card"]

    def _quiz_files(self):
        out = []
        for base in ("quizzes",):
            for dirpath, _, files in os.walk(os.path.join(ROOT, base)):
                for f in files:
                    if f.endswith(".html"):
                        out.append(os.path.join(dirpath, f))
        return out

    def test_every_quiz_page_has_share_meta(self):
        missing = []
        for path in self._quiz_files():
            html = open(path, encoding="utf-8").read()
            lack = [k for k in self.REQUIRED if k not in html]
            if lack:
                missing.append((os.path.relpath(path, ROOT), lack))
        self.assertEqual(missing, [], f"공유 메타 누락: {missing}")

    def test_og_images_exist_on_disk(self):
        """og:image가 가리키는 파일이 실제로 있어야 한다.

        (과거 og_compare.png가 참조만 있고 파일이 없어 크롤러가 404를 받았다 —
         access.log에 기록됨. 같은 사고 재발 방지.)"""
        refs = set()
        for path in self._quiz_files() + [
            os.path.join(ROOT, "static", "my-report.html"),
            os.path.join(ROOT, "static", "my-report-saju.html"),
        ]:
            html = open(path, encoding="utf-8").read()
            refs |= set(re.findall(r'content="https://flavor\.arkedia\.work(/static/[^"]+)"', html))
        self.assertTrue(refs, "og:image 참조를 하나도 못 찾음")
        for ref in sorted(refs):
            self.assertTrue(os.path.exists(os.path.join(ROOT, ref.lstrip("/"))),
                            f"참조는 있는데 파일이 없음: {ref}")

    def test_favicon_assets_exist(self):
        for f in ("favicon.svg", "favicon.ico", "apple-touch-icon.png"):
            self.assertTrue(os.path.exists(os.path.join(ROOT, "static", f)), f)


class TestResultPageEscaping(unittest.TestCase):
    """/result는 유저 닉네임을 HTML·JS 양쪽 문맥에 넣는다 — 둘 다 막혀 있어야 한다."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()
        cls._db = os.path.join(cls._tmp, "share.db")
        cls._prev = os.environ.get("DB_PATH")
        os.environ["DB_PATH"] = cls._db
        import config
        import db.connection as dbconn
        config.DB_PATH = cls._db
        dbconn.DB_PATH = cls._db

    @classmethod
    def tearDownClass(cls):
        import config
        import db.connection as dbconn
        if cls._prev is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = cls._prev
            config.DB_PATH = cls._prev
            dbconn.DB_PATH = cls._prev

    def setUp(self):
        from app import create_app
        self.client = create_app().test_client()

    def test_malicious_nickname_is_escaped(self):
        evil = '<script>alert(1)</script>"\''
        rid = self.client.post("/api/submit", json={
            "name": evil, "birth_date": "1990-01-01", "birth_time": "12",
            "gender": "F", "quiz_type": "vol4_travel", "survey": _SURVEY,
        }).get_json()["id"]

        page = self.client.get(f"/result/{rid}").get_data(as_text=True)
        self.assertEqual(page.count("<script>alert(1)</script>"), 0,
                         "닉네임의 raw <script>가 페이지에 그대로 출력됨")
        self.assertIn("&lt;script&gt;", page)          # HTML 문맥은 escape
        self.assertIn("\\u003cscript", page.replace("\\u003C", "\\u003c"))  # JS 문맥은 json.dumps

    def test_result_page_has_og_image(self):
        rid = self.client.post("/api/submit", json={
            "name": "정상닉", "birth_date": "1990-01-01", "birth_time": "12",
            "gender": "F", "quiz_type": "vol4_travel", "survey": _SURVEY,
        }).get_json()["id"]
        page = self.client.get(f"/result/{rid}").get_data(as_text=True)
        for k in ("og:image", "twitter:card", "og:type", 'rel="icon"'):
            self.assertIn(k, page)

    def test_favicon_route_redirects(self):
        resp = self.client.get("/favicon.ico")
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn("/static/favicon.ico", resp.headers["Location"])


if __name__ == "__main__":
    unittest.main()
