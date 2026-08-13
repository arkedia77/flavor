"""커피 자아 카드 표현층 검증 (2026-07-16, Leo 재미·공유 원칙)

coffee_persona(seed) → 캐릭터 카드. 측정 예측(predict_coffee_type)과 독립된 순수 표현 매핑.
키워드 우선순위(산미>디저트>블랙>스위트>무정보)·무정보 긍정 폴백·극(pole) 정합 검증.
노출 배치는 fableself 결정 대기 — 여기선 내용 결정성만 본다.
"""

import unittest

from engines.coldstart import coffee_persona, coffee_reveal, COFFEE_PERSONA


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


class TestCoffeeReveal(unittest.TestCase):
    """fableself 결정: 카드=피드백 산출물. 반응이 주재료, said와 어긋나면 반전."""

    def test_reaction_is_primary_agree(self):
        # seed=블랙, sweet 아이템 서빙했는데 👎 → 반대=black. said와 일치 → 블랙 스트레이트
        r = coffee_reveal("아메리카노", "카페라떼·바닐라라떼", -2)
        self.assertEqual(r["pole"], "black")
        self.assertFalse(r["twist"])
        self.assertEqual(r["basis"], "reaction")

    def test_twist_said_black_reacted_sweet(self):
        # seed=블랙(아메리카노), sweet 아이템 서빙 + 👍 → reacted=sweet ≠ said=black → 반전
        r = coffee_reveal("아메리카노 진하게", "카페라떼·바닐라라떼", 1)
        self.assertTrue(r["twist"])
        self.assertEqual(r["pole"], "sweet")
        self.assertIn("겉은 블랙", r["name"])
        self.assertIn("속은 스위트", r["name"])

    def test_twist_said_sweet_reacted_black(self):
        r = coffee_reveal("바닐라라떼", "따뜻한 아메리카노·단골 블렌드", 2)
        self.assertTrue(r["twist"])
        self.assertEqual(r["pole"], "black")
        self.assertIn("겉은 스위트", r["name"])

    def test_shrug_is_neutral_not_dislike(self):
        # 🤷(-1)는 meh — 극 반전 안 하고 미확정 → seed로 폴백
        r = coffee_reveal("아메리카노", "카페라떼·바닐라라떼", -1)
        self.assertEqual(r["basis"], "seed")
        self.assertEqual(r["pole"], "black")
        self.assertFalse(r["twist"])

    def test_dislike_flips_pole(self):
        # 👎(-2) 스위트 서빙 → 반대=black. said(블랙)와 일치
        r = coffee_reveal("아메리카노", "카페라떼·바닐라라떼", -2)
        self.assertEqual(r["basis"], "reaction")
        self.assertEqual(r["pole"], "black")

    def test_no_seed_no_reaction_is_sprout(self):
        r = coffee_reveal(None, None, None)
        self.assertEqual(r["key"], "sprout")
        self.assertEqual(r["basis"], "none")

    def test_mixed_served_item_reaction_inconclusive(self):
        # mixed 아이템은 반응 극 해석 불가 → seed로 폴백
        r = coffee_reveal("아메리카노", "아이스 라떼·아메리카노", 1)
        self.assertEqual(r["basis"], "seed")
        self.assertEqual(r["pole"], "black")

    def test_reveal_shape_and_snapshot_framing(self):
        r = coffee_reveal("바닐라라떼", "달달한 라떼·플랫화이트", 1)
        for k in ("key", "name", "emoji", "oneliner", "pole", "twist", "snapshot", "share", "basis",
                  "refined"):
            self.assertIn(k, r)
        self.assertEqual(r["snapshot"], "지금 이 순간의 커피 취향")  # 고정 정체성 아님


class CoffeeRevealRefinementTest(unittest.TestCase):
    """LEO 결정 2026-08-13 B안 ① — 산미🫐·디저트🎂를 리빌에 노출(표현층만).

    이전에는 `coffee_reveal()`이 pole을 black/sweet 둘로 접어서 정의된 5종 중
    acidity·dessert **2종이 최종 카드에 원리상 안 나왔다**. 이제 seed가 그 극의
    하위 유형을 말했으면 그 카드를 보여준다 — ★단 pole(측정 축)은 그대로다.
    """

    def test_산미_seed가_black_확인되면_산미헌터로_표시(self):
        r = coffee_reveal("핸드드립 산미 좋아", "따뜻한 아메리카노·단골 블렌드", 2)
        self.assertEqual(r["key"], "acidity")
        self.assertEqual(r["emoji"], "🫐")
        self.assertTrue(r["refined"])

    def test_디저트_seed가_sweet_확인되면_디저트겸용파로_표시(self):
        r = coffee_reveal("프라푸치노 휘핑 추가", "달달한 라떼·플랫화이트", 2)
        self.assertEqual(r["key"], "dessert")
        self.assertTrue(r["refined"])

    def test_세분화해도_측정축은_안_바뀐다(self):
        """이 테스트가 B안의 전제다 — 표현만 갈리고 pole은 두 축 그대로여야 한다."""
        acid = coffee_reveal("핸드드립 산미 좋아", "따뜻한 아메리카노·단골 블렌드", 2)
        plain = coffee_reveal("아메리카노 진하게", "따뜻한 아메리카노·단골 블렌드", 2)
        self.assertEqual(acid["pole"], "black")
        self.assertEqual(plain["pole"], "black")      # 같은 극
        self.assertNotEqual(acid["key"], plain["key"])  # 표시만 다름

    def test_반응_없이_seed만_있어도_세분화된다(self):
        r = coffee_reveal("핸드드립 산미 좋아", None, None)
        self.assertEqual(r["key"], "acidity")
        self.assertEqual(r["basis"], "seed")

    def test_일반_seed는_세분화_안_함(self):
        r = coffee_reveal("아메리카노 진하게", "따뜻한 아메리카노·단골 블렌드", 2)
        self.assertEqual(r["key"], "black")
        self.assertFalse(r["refined"])

    def test_반전_카드는_세분화하지_않는다(self):
        """극이 갈리면 반전 카드가 이미 그 대비를 표현한다 — 건드리지 않는다."""
        r = coffee_reveal("핸드드립 산미 좋아", "카페라떼·바닐라라떼", 2)
        self.assertTrue(r["twist"])
        self.assertEqual(r["name"], "겉은 블랙, 속은 스위트형")

    def test_무정보_seed는_새싹_유지(self):
        r = coffee_reveal(None, None, None)
        self.assertEqual(r["key"], "sprout")
        self.assertFalse(r["refined"])


class CoffeeShareTextTest(unittest.TestCase):
    """LEO 결정 2026-08-13 B안 ② — 공유 문구에 펀치라인(oneliner) 포함."""

    def test_공유문구에_펀치라인이_들어간다(self):
        r = coffee_reveal("아메리카노", "카페라떼·바닐라라떼", 2)
        self.assertTrue(r["share"].startswith("내 커피 자아 ="))
        self.assertIn(r["oneliner"], r["share"])       # ★핵심 가드
        self.assertIn(r["name"], r["share"])

    def test_페르소나_카드_공유문구도_같은_형식(self):
        p = coffee_persona("핸드드립 산미 좋아")
        self.assertIn(p["oneliner"], p["share"])

    def test_페르소나_5종_전건_펀치라인_포함(self):
        seeds = {"acidity": "핸드드립 산미 좋아", "black": "아메리카노 진하게",
                 "dessert": "프라푸치노 휘핑 추가", "sweet": "바닐라라떼", "sprout": ""}
        self.assertEqual(set(seeds), set(COFFEE_PERSONA))  # 페르소나 추가 시 이 테스트가 먼저 깨진다
        for key, seed in seeds.items():
            p = coffee_persona(seed)
            self.assertEqual(p["key"], key)
            self.assertIn(COFFEE_PERSONA[key]["oneliner"], p["share"])


if __name__ == "__main__":
    unittest.main()
