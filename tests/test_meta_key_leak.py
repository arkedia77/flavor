"""개방 체크리스트 3번 — `_` 접두 메타키가 사용자 화면에 새지 않는다.

배경(2026-08-14, 콜드스타트 게이트 개방 직전 발견):
  `results`에는 도메인 카드 외에 분석용 `_coldstart`(seed 수집분)가 섞인다.
  도메인 렌더러는 **프론트 9곳·서버 1곳 어디에도 `_` 필터가 없어서**,
  게이트를 켜는 순간 라벨이 `_coldstart`인 빈 카드가 9번째로 렌더됐다.
  게이트 OFF 동안엔 메타키가 안 붙어 드러나지 않던 결함이다.

  ★렌더러 10곳을 각각 고치는 대신 **서버 경계 두 곳**에서 막았다
  (제출 응답 · /result). 새 퀴즈 페이지가 추가돼도 자동으로 안전하다.
  ⇒ 그래서 이 테스트는 **경계 두 곳**을 고정한다. 렌더러를 고정하지 않는다.
"""

import json
import re
import unittest
from unittest import mock

from config import public_results


class PublicResultsTest(unittest.TestCase):
    def test_밑줄_접두키만_제거된다(self):
        r = public_results({"커피": {"item": "라떼"}, "_coldstart": {"seeds": ["x"]}})
        self.assertEqual(list(r), ["커피"])

    def test_원본을_변형하지_않는다(self):
        src = {"커피": {"item": "라떼"}, "_coldstart": {"seeds": ["x"]}}
        public_results(src)
        self.assertIn("_coldstart", src)  # 저장·분석 경로는 무영향이어야 한다

    def test_메타키가_없으면_항등(self):
        src = {"커피": {"item": "라떼"}}
        self.assertEqual(public_results(src), src)

    def test_dict가_아니면_그대로(self):
        self.assertEqual(public_results(None), None)


class MetaKeyLeakEndToEndTest(unittest.TestCase):
    """게이트 ON 상태에서 실제 응답·페이지에 메타키가 새는지."""

    def setUp(self):
        from db.connection import init_db
        init_db()  # DB 경로는 db.connection이 소유한다 — 테스트가 따로 정하지 않는다
        from app import create_app
        self.client = create_app().test_client()

    def _submit_with_gate_on(self):
        import api.submit as S
        with mock.patch.dict(S.COLDSTART_ARM,
                             {"enabled": True, "seed_collection": True, "random_frac": 0.15},
                             clear=False):
            return self.client.post("/api/submit", json={
                "name": "게이트", "birth_date": "1990-05-15", "birth_time": "14:00",
                "gender": "male", "survey": {"q1": 3, "q2": 4},
                "seeds": ["핸드드립 산미 좋아"],
            }).get_json()

    def test_제출_응답에_메타키가_없다(self):
        r = self._submit_with_gate_on()
        leaked = [k for k in r["results"] if k.startswith("_")]
        self.assertEqual(leaked, [], f"응답에 메타키 누출: {leaked}")

    def test_result_페이지에_메타키_카드가_없다(self):
        """★핵심 회귀 가드 — 고치기 전엔 여기서 '_coldstart' 카드가 나왔다."""
        sid = self._submit_with_gate_on()["id"]
        html = self.client.get(f"/result/{sid}").get_data(as_text=True)
        labels = re.findall(r'<span class="d-label">([^<]*)</span>', html)
        self.assertTrue(labels, "도메인 카드가 하나도 렌더되지 않음 — 테스트 전제 붕괴")
        self.assertNotIn("_coldstart", labels)
        self.assertFalse([l for l in labels if l.startswith("_")])

    def test_DB에는_메타키가_보존된다(self):
        """새지 않는 것과 버리는 것은 다르다 — lift 분석이 이 값을 읽는다."""
        sid = self._submit_with_gate_on()["id"]
        from db.connection import get_db_connection
        conn = get_db_connection()
        row = conn.execute(
            "SELECT results_json FROM submissions WHERE id=?", (sid,)).fetchone()
        conn.close()
        stored = json.loads(row[0])
        self.assertIn("_coldstart", stored)
        self.assertEqual(stored["_coldstart"]["seeds"], ["핸드드립 산미 좋아"])


if __name__ == "__main__":
    unittest.main()
