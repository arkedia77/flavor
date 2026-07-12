"""어휘 분리 가드 — EVIDENCE_AUDIT 완화책 3 (2026-07-12)

사주 파생 표시 카피(생년월일만으로 결정되어 유저에게 노출되는 문구)가
9차원 설문 도구 어휘(config/dimension_lexicon.json)를 포함하면 실패한다.

목적: 자기귀인 오염 차단. 유저가 사주 카피에서 차원 서술어를 읽으면
이후 설문 자기보고가 그 방향으로 이동해 (Fichten & Sunerton 1983)
십신→취향 상관이 인공 생성될 수 있다 — 검증 게이트 무효화 리스크.

검사 대상:
  1. engines/persona.py DAY_MASTER_PERSONA (name + vibe)
  2. static/shared/saju-engine.js DAY_MASTER_PERSONA — 서버와 패리티 + 어휘
새 사주 카피 표면이 생기면 이 테스트에 추가할 것.
"""

import json
import os
import re
import unittest

from engines.persona import DAY_MASTER_PERSONA

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEXICON_PATH = os.path.join(ROOT, "config", "dimension_lexicon.json")
SAJU_ENGINE_JS = os.path.join(ROOT, "static", "shared", "saju-engine.js")


def load_lexicon():
    with open(LEXICON_PATH, encoding="utf-8") as fp:
        return json.load(fp)["dimensions"]


def banned_hits(text, lexicon):
    """text에 포함된 (차원, 어간) 목록"""
    return [(dim, stem) for dim, stems in lexicon.items()
            for stem in stems if stem in text]


def parse_js_personas():
    """saju-engine.js의 DAY_MASTER_PERSONA 블록 파싱"""
    with open(SAJU_ENGINE_JS, encoding="utf-8") as fp:
        src = fp.read()
    block = re.search(r"DAY_MASTER_PERSONA\s*=\s*\{(.*?)\n\};", src, re.S)
    assert block, "saju-engine.js에서 DAY_MASTER_PERSONA 블록을 찾지 못함"
    out = {}
    pat = re.compile(
        r'"(?P<stem>[가-힣])":\s*\{name:"(?P<name>[^"]+)",\s*emoji:"(?P<emoji>[^"]+)",'
        r'\s*element:"(?P<element>[^"]+)",\s*vibe:"(?P<vibe>[^"]+)"\}')
    for m in pat.finditer(block.group(1)):
        out[m.group("stem")] = {"name": m.group("name"), "emoji": m.group("emoji"),
                                "element": m.group("element"), "vibe": m.group("vibe")}
    return out


class TestLexiconFile(unittest.TestCase):
    def test_lexicon_covers_9_dimensions(self):
        from config import DIMENSIONS
        lexicon = load_lexicon()
        self.assertEqual(set(lexicon.keys()), set(DIMENSIONS))
        for dim, stems in lexicon.items():
            self.assertTrue(stems, f"{dim} 어휘 목록이 비어 있음")


class TestPersonaLexiconSeparation(unittest.TestCase):
    def test_server_persona_clean(self):
        lexicon = load_lexicon()
        for stem, p in DAY_MASTER_PERSONA.items():
            for field in ("name", "vibe"):
                hits = banned_hits(p[field], lexicon)
                self.assertFalse(
                    hits,
                    f"persona[{stem}].{field}={p[field]!r}에 설문 어휘 {hits} — "
                    "사주 카피는 차원 서술어 사용 금지 (완화책 3)")

    def test_client_persona_clean_and_parity(self):
        js = parse_js_personas()
        self.assertEqual(set(js.keys()), set(DAY_MASTER_PERSONA.keys()),
                         "클라이언트 페르소나 천간 목록 불일치")
        lexicon = load_lexicon()
        for stem, sp in DAY_MASTER_PERSONA.items():
            jp = js[stem]
            for field in ("name", "element", "vibe"):
                self.assertEqual(jp[field], sp[field],
                                 f"[{stem}].{field} 서버/클라이언트 불일치")
            for field in ("name", "vibe"):
                hits = banned_hits(jp[field], lexicon)
                self.assertFalse(hits,
                                 f"클라이언트 persona[{stem}].{field}에 설문 어휘 {hits}")


if __name__ == "__main__":
    unittest.main()
