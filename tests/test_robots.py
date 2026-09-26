"""/robots.txt — 검색 차단 + 미리보기 허용 (LEO 결정 2026-09-26 · kee A-222)

★게이트가 아니라 «계약» 테스트다: 이 라우트가 지켜야 하는 것은 두 가지가 동시에 참인 것 —
  ⑴검색 엔진이 막힌다(`User-agent: *` 그룹에 `Disallow: /`)
  ⑵미리보기 크롤러는 막히지 «않는다»(각자 자기 그룹에 `Allow: /`)
⛔robots.txt 의미론상 **자기 그룹이 있는 UA는 `*` 그룹을 «안» 따른다.** 그래서 두 조건이
  한 파일에서 동시에 성립한다 — 그 성질이 깨지면 이 테스트가 잡는다.

⚠creev 검증(`grep -qE '^[[:space:]]*Disallow:[[:space:]]*/[[:space:]]*$'`)과 같은 축을
  일부러 한 줄 넣었다 — 저쪽이 보는 것과 내가 보는 것이 어긋나면 서로 틀린 줄 알게 된다.
"""

import re
import unittest

from api.public import ROBOTS_TXT
from app import create_app

# 미리보기(공유 카드) 크롤러 — 막히면 «공유 카드가 조용히 깨진다»
PREVIEW_AGENTS = [
    "kakaotalk-scrap",          # 카카오톡 — 우리 주 공유 경로
    "facebookexternalhit",      # Facebook/Instagram
    "Facebot",                  # ★Facebook 두 번째 UA — kee 원안에 없었다
    "Twitterbot",
    "Slackbot-LinkExpanding",   # ★우리가 #flavor 로 링크를 실제로 뿌린다(8/18 실증)
    "Slackbot",
    "Discordbot",
    "TelegramBot",
]


def _groups(text):
    """robots.txt → {user-agent 소문자: [지시어, ...]}. 빈 줄로 그룹이 갈린다."""
    groups, cur_agents = {}, []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            cur_agents = []
            continue
        if line.startswith("#"):
            continue
        key, _, val = line.partition(":")
        key, val = key.strip().lower(), val.strip()
        if key == "user-agent":
            cur_agents.append(val.lower())
            groups.setdefault(val.lower(), [])
        elif cur_agents:
            for a in cur_agents:
                groups[a].append(f"{key}: {val}")
    return groups


class TestRobotsContent(unittest.TestCase):
    def setUp(self):
        self.g = _groups(ROBOTS_TXT)

    def test_wildcard_group_blocks_everything(self):
        """검색 엔진 차단 — LEO 결정의 «전면 차단» 쪽."""
        self.assertIn("*", self.g, "`User-agent: *` 그룹이 없으면 검색이 안 막힌다")
        self.assertIn("disallow: /", self.g["*"])

    def test_creev_verify_regex_matches(self):
        """creev가 실제로 돌리는 정규식과 «같은 축»을 여기서도 본다."""
        self.assertTrue(
            any(re.match(r"^[ \t]*Disallow:[ \t]*/[ \t]*$", l) for l in ROBOTS_TXT.splitlines()),
            "creev 검증이 rc 1을 낸다 = 저쪽 대장에 내가 미이행으로 남는다")

    def test_every_preview_agent_has_its_own_allow_group(self):
        """★미리보기 크롤러는 각자 그룹에서 허용 — 그래야 `*`의 Disallow를 안 따른다."""
        for ua in PREVIEW_AGENTS:
            with self.subTest(ua=ua):
                self.assertIn(ua.lower(), self.g, f"{ua} 그룹이 없으면 그 앱에서 공유 카드가 깨진다")
                self.assertIn("allow: /", self.g[ua.lower()])

    def test_preview_agents_are_not_disallowed(self):
        """⛔허용 그룹에 Disallow가 섞이면 의도가 뒤집힌다(조용히)."""
        for ua in PREVIEW_AGENTS:
            with self.subTest(ua=ua):
                self.assertNotIn("disallow: /", self.g[ua.lower()])

    def test_residual_risk_is_documented_in_the_file(self):
        """★이 방식은 허용 목록이 «완전할 수 없다» — 그 사실이 파일 안에 남아 있어야 한다.

        공유가 OS 공유 시트를 타므로 목적지 앱을 열거할 수 없다. 주석을 지우면 다음 사람이
        「목록에 없는 앱에서 카드가 깨진다」는 것을 모른 채 유지보수한다.
        """
        self.assertIn("완전할 수 없다", ROBOTS_TXT)


class TestRobotsRoute(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_served_as_plain_text_200(self):
        r = self.client.get("/robots.txt")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.mimetype.startswith("text/plain"),
                        f"text/plain이 아니면 크롤러가 무시할 수 있다: {r.mimetype}")

    def test_body_matches_constant(self):
        """라우트와 상수가 갈리면 테스트는 통과하고 실물은 다르다."""
        self.assertEqual(self.client.get("/robots.txt").get_data(as_text=True), ROBOTS_TXT)

    def test_other_routes_unaffected(self):
        """⛔다른 라우트·동작 변경 0 (kee 조건)."""
        self.assertEqual(self.client.get("/health").status_code, 200)


if __name__ == "__main__":
    unittest.main()
