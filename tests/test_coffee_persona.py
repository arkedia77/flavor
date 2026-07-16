"""커피 자아 카드 표현층 검증 (2026-07-16, Leo 재미·공유 원칙)

coffee_persona(seed) → 캐릭터 카드. 측정 예측(predict_coffee_type)과 독립된 순수 표현 매핑.
키워드 우선순위(산미>디저트>블랙>스위트>무정보)·무정보 긍정 폴백·극(pole) 정합 검증.
노출 배치는 fableself 결정 대기 — 여기선 내용 결정성만 본다.
"""

import unittest

from engines.coldstart import coffee_persona, COFFEE_PERSONA


class TestCoffeePersona(unittest.TestCase):
    def test_black_americano(self):
        r = coffee_persona("아메리카노 진하게")
        self.assertEqual(r["key"], "black")
        self.assertEqual(r["pole"], "black")

    def test_acidity_beats_black(self):
        # 핸드드립=산미(축 b) 어휘가 블랙보다 우선
        r = coffee_persona("핸드드립 산미 좋아")
        self.assertEqual(r["key"], "acidity")
        self.assertEqual(r["pole"], "black")

    def test_sweet_latte(self):
        r = coffee_persona("바닐라라떼")
        self.assertEqual(r["key"], "sweet")
        self.assertEqual(r["pole"], "sweet")

    def test_dessert_beats_sweet(self):
        r = coffee_persona("프라푸치노 휘핑 추가")
        self.assertEqual(r["key"], "dessert")
        self.assertEqual(r["pole"], "sweet")

    def test_unknown_seed_is_sprout(self):
        for s in ["커피 잘 몰라요", "아무거나", "", None]:
            self.assertEqual(coffee_persona(s)["key"], "sprout")

    def test_no_keyword_match_falls_back_sprout(self):
        self.assertEqual(coffee_persona("음악 좋아함")["key"], "sprout")

    def test_shape_complete(self):
        r = coffee_persona("에스프레소")
        for k in ("key", "name", "emoji", "oneliner", "pole", "share"):
            self.assertIn(k, r)
        self.assertTrue(r["share"].startswith("내 커피 자아 ="))

    def test_all_personas_have_fields(self):
        for key, p in COFFEE_PERSONA.items():
            for f in ("name", "emoji", "pole", "oneliner"):
                self.assertIn(f, p, f"{key} missing {f}")


if __name__ == "__main__":
    unittest.main()
