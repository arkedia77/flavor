#!/usr/bin/env python3
"""손으로 써둔 OG가 있는 페이지에 빠진 항목만 보충 — og:image / og:url / favicon 등.

inject_og_tags.py는 기존 카피를 존중해 이 페이지들을 건드리지 않는다. 여기서는
**이미 있는 og:title/og:description은 그대로 두고** 누락분만 채운다.
compare.html의 og_compare.png는 파일이 없어 404 → 실존 이미지로 교체.

멱등: 이미 채워진 파일은 스킵.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://flavor.arkedia.work"
MARKER = "<!-- og:manual-patch -->"

# (파일, 라우트, 트랙)
TARGETS = [
    ("quizzes/hub/hub.html", "/", "dna"),
    ("quizzes/hub/hub_saju.html", "/saju", "saju"),
    ("quizzes/compare/compare.html", "/compare", "dna"),
    ("quizzes/vol3_swipe/swipe.html", "/swipe", "dna"),
    ("static/my-report.html", "/my-report", "dna"),
    ("static/my-report-saju.html", "/my-report-saju", "saju"),
]


def main():
    for rel, route, track in TARGETS:
        path = os.path.join(ROOT, rel)
        html = open(path, encoding="utf-8").read()
        if MARKER in html:
            print(f"  skip (이미 적용) {rel}")
            continue

        img = f"{SITE}/static/og_{track}.png"

        # 존재하지 않는 og_compare.png 참조 교체
        html = html.replace(f"{SITE}/static/og_compare.png", img)

        desc = ""
        m = re.search(r'<meta property="og:description" content="([^"]*)"', html)
        if m:
            desc = m.group(1)
        title = ""
        m2 = re.search(r'<meta property="og:title" content="([^"]*)"', html)
        if m2:
            title = m2.group(1)

        add = [MARKER]
        if 'property="og:type"' not in html:
            add.append('<meta property="og:type" content="website">')
        if 'property="og:site_name"' not in html:
            add.append('<meta property="og:site_name" content="flavor">')
        if 'property="og:locale"' not in html:
            add.append('<meta property="og:locale" content="ko_KR">')
        if 'property="og:url"' not in html:
            add.append(f'<meta property="og:url" content="{SITE}{route}">')
        if 'property="og:image"' not in html:
            add.append(f'<meta property="og:image" content="{img}">')
            add.append('<meta property="og:image:width" content="1200">')
            add.append('<meta property="og:image:height" content="630">')
        if 'name="twitter:card"' not in html:
            add.append('<meta name="twitter:card" content="summary_large_image">')
            add.append(f'<meta name="twitter:title" content="{title}">')
            add.append(f'<meta name="twitter:description" content="{desc}">')
            add.append(f'<meta name="twitter:image" content="{img}">')
        if 'name="description"' not in html and desc:
            add.append(f'<meta name="description" content="{desc}">')
        if 'rel="icon"' not in html:
            add.append('<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">')
            add.append('<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">')

        anchor = re.search(r"</title>", html)
        if not anchor:
            print(f"  ⚠️  <title> 없음: {rel}")
            continue
        html = html.replace("</title>", "</title>\n" + "\n".join(add), 1)
        open(path, "w", encoding="utf-8").write(html)
        print(f"  {rel:38} [{track}] +{len(add) - 1}개")


if __name__ == "__main__":
    main()
