#!/usr/bin/env python3
"""퀴즈 HTML에 공유 메타(OG/Twitter) 주입 — 유통 준비.

문제: 퀴즈 40여 페이지에 OG 태그가 전혀 없어 카카오톡/트위터에 링크를 붙이면
      미리보기(제목·설명·썸네일)가 아무것도 안 뜬다. 바이럴의 첫 관문이 비어 있음.

설계:
- **문구는 새로 짓지 않는다.** 각 파일의 <title>이 이미 Leo가 쓴 카피이므로
  " — " 기준으로 앞=og:title(훅), 뒤=og:description(부제)으로 그대로 재사용한다.
- 라우트 경로는 api/public.py에서 파싱해 og:url을 절대 URL로 박는다(카톡은 상대경로 무시).
- 트랙(DNA 보라 / 사주 금색)에 따라 og:image를 나눈다.
- **멱등**: 이미 주입된 파일은 마커로 스킵. 재실행 안전.

실행: python3 scripts/inject_og_tags.py [--check]
      --check = 변경 없이 현황만 출력
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://flavor.arkedia.work"
MARKER = "<!-- og:auto -->"

# 트랙 판별: 사주 트랙은 금색 primary(#f59e0b)를 쓴다
SAJU_PRIMARY = "#f59e0b"

DEFAULT_DESC = {
    "dna": "생년월일이 말해주는 내 취향, 진짜 맞는지 까보는 테스트",
    "saju": "팔자가 아는 내 취향, 진짜 맞는지 까보는 테스트",
}

# 어드민/내부 페이지 — 공유 대상 아님
EXCLUDE = {"/dashboard"}

# 설명으로 쓰기엔 의미 없는 브랜드 토막 (이럴 땐 트랙 기본 문구로 대체)
BRAND_ONLY = re.compile(r"^\s*(flavor|flavor 사주|플레이버)\s*$", re.I)


def route_map():
    """api/public.py에서 라우트 → HTML 파일 절대경로 매핑을 뽑는다."""
    src = open(os.path.join(ROOT, "api", "public.py"), encoding="utf-8").read().splitlines()
    out = {}
    pending = None
    for line in src:
        m = re.match(r'@public\.route\("([^"]+)"\)', line.strip())
        if m:
            pending = m.group(1)
            continue
        if pending and "os.path.join(" in line and '.html"' in line:
            # os.path.join(..., "quizzes", "vol4_travel", "travel.html") — 문자열 인자만 추출
            parts = [p for p in re.findall(r'"([^"]+)"', line)]
            if parts:
                out[pending] = os.path.join(ROOT, *parts)
            pending = None
        elif pending and line.strip().startswith("return"):
            pending = None            # 파일 안 여는 라우트(/health 등)
    return out


def split_title(title):
    """<title>을 훅(og:title) / 부제(og:description)로 가른다.

    브랜드 토막('flavor')이 어느 쪽에 붙어 있든 설명으로는 쓰지 않는다 —
    카톡 미리보기 두 번째 줄이 'flavor' 한 단어면 아무 정보도 못 준다.
    """
    for sep in (" — ", " – ", " - ", " | "):
        if sep in title:
            head, tail = [s.strip() for s in title.split(sep, 1)]
            if BRAND_ONLY.match(tail):
                return head, ""
            if BRAND_ONLY.match(head):
                return tail, ""
            return head, tail
    return title.strip(), ""


def build_block(og_title, og_desc, url, track):
    img = f"{SITE}/static/og_{track}.png"
    esc = lambda s: s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    return f"""{MARKER}
<meta name="description" content="{esc(og_desc)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="flavor">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{esc(og_title)}">
<meta property="og:description" content="{esc(og_desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(og_title)}">
<meta name="twitter:description" content="{esc(og_desc)}">
<meta name="twitter:image" content="{img}">
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">"""


def main():
    check = "--check" in sys.argv
    routes = route_map()
    seen, done, skipped, missing = set(), [], [], []

    for route, path in sorted(routes.items()):
        if route in EXCLUDE:
            skipped.append(route + "(내부)")
            continue
        if not os.path.exists(path):
            missing.append((route, path))
            continue
        if path in seen:
            continue
        seen.add(path)
        html = open(path, encoding="utf-8").read()

        if MARKER in html:
            skipped.append(route)
            continue
        if "og:title" in html:
            # 손으로 넣어둔 OG가 있는 페이지(hub 등)는 건드리지 않는다 — 수동 확인 대상
            skipped.append(route + "(수동OG)")
            continue

        m = re.search(r"<title>(.*?)</title>", html, re.S)
        if not m:
            missing.append((route, "no <title>"))
            continue
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        head, tail = split_title(title)
        track = "saju" if SAJU_PRIMARY in html[:4000] else "dna"
        desc = tail or DEFAULT_DESC[track]
        block = build_block(head, desc, SITE + route, track)

        if not check:
            new = html.replace(m.group(0), m.group(0) + "\n" + block, 1)
            open(path, "w", encoding="utf-8").write(new)
        done.append((route, track, head, desc))

    print(f"{'[check] ' if check else ''}주입 대상 {len(done)}건 / 이미 있음 {len(skipped)}건 / 문제 {len(missing)}건")
    for route, track, h, d in done:
        print(f"  {route:22} [{track}] {h}  |  {d}")
    if skipped:
        print("  (스킵) " + ", ".join(skipped))
    for route, why in missing:
        print(f"  ⚠️  {route}: {why}")


if __name__ == "__main__":
    main()
