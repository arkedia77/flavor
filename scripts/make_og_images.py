#!/usr/bin/env python3
"""공유 썸네일(OG 이미지) 생성 — static/og_dna.png, static/og_saju.png (1200x630).

카톡/트위터에 링크를 붙였을 때 뜨는 그 카드 이미지다. 지금은 자산이 아예 없어
미리보기가 비어 나온다(og_compare.png는 참조만 있고 파일이 없어 404).

브랜드 기준(quiz-base.css / hub.html):
  배경 #080612 · DNA 보라 #c084fc→#ec4899 · 사주 금색 #f59e0b→#d97706

실행: python3 scripts/make_og_images.py     (macOS 시스템 폰트 사용, 리포에 PNG 커밋)
"""

import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static")
W, H = 1200, 630
BG = (8, 6, 18)

FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

TRACKS = {
    "dna": {
        "accent": (192, 132, 252),   # #c084fc
        "accent2": (236, 72, 153),   # #ec4899
        "kicker": "생년월일 취향 테스트",
        "head": "야 너 취향이 뭐야",
        "sub": "타고난 나 vs 진짜 나, 까보자",
        "mark": "DNA",
    },
    "saju": {
        "accent": (245, 158, 11),    # #f59e0b
        "accent2": (217, 119, 6),    # #d97706
        "kicker": "사주 취향 테스트",
        "head": "팔자가 아는 내 취향",
        "sub": "맞는지 틀리는지 한번 보자",
        "mark": "四柱",
    },
}


def font(idx, size):
    """AppleSDGothicNeo.ttc의 웨이트 인덱스 — 2=Bold 근방, 0=Regular."""
    try:
        return ImageFont.truetype(FONT_PATH, size, index=idx)
    except Exception:
        return ImageFont.truetype(FONT_PATH, size)


def radial_glow(img, cx, cy, radius, color, peak=0.30):
    """중심에서 퍼지는 은은한 광원. 배경이 새카맣기만 하면 카드가 죽어 보인다."""
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    steps = 60
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(radius * t)
        a = peak * (1 - t) ** 1.6
        col = tuple(int(BG[k] + (color[k] - BG[k]) * a) for k in range(3))
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return Image.blend(img, glow, 1.0)


def draw_track(name, spec):
    img = Image.new("RGB", (W, H), BG)
    img = radial_glow(img, 250, 120, 900, spec["accent"], peak=0.26)
    img = radial_glow(Image.blend(img, img, 0), 250, 120, 900, spec["accent"], peak=0.0) if False else img
    d = ImageDraw.Draw(img)

    # 상단 액센트 바
    for x in range(W):
        t = x / W
        col = tuple(int(spec["accent"][k] + (spec["accent2"][k] - spec["accent"][k]) * t) for k in range(3))
        d.line([(x, 0), (x, 8)], fill=col)

    # 워드마크
    d.text((80, 74), "flavor", font=font(2, 46), fill=spec["accent"])

    # 키커
    d.text((80, 152), spec["kicker"], font=font(0, 30), fill=(150, 145, 175))

    # 헤드라인
    d.text((80, 228), spec["head"], font=font(2, 92), fill=(245, 243, 255))

    # 서브
    d.text((80, 372), spec["sub"], font=font(0, 40), fill=(186, 180, 210))

    # 하단 도메인 pill
    label = "flavor.arkedia.work"
    f = font(0, 30)
    tw = d.textlength(label, font=f)
    px, py = 80, 500
    d.rounded_rectangle([px, py, px + tw + 56, py + 62], radius=31,
                        fill=(20, 14, 40), outline=spec["accent"], width=2)
    d.text((px + 28, py + 14), label, font=f, fill=spec["accent"])

    # 우측 워터마크 — 트랙 식별용. 이모지는 플랫폼별 렌더가 깨져서 글자로 둔다.
    mf = font(2, 150)
    mark = spec["mark"]
    mw = d.textlength(mark, font=mf)
    faint = tuple(int(BG[k] + (spec["accent"][k] - BG[k]) * 0.14) for k in range(3))
    d.text((W - 80 - mw, 330), mark, font=mf, fill=faint)

    path = os.path.join(OUT, f"og_{name}.png")
    img.save(path, "PNG", optimize=True)
    print(f"{path}  {os.path.getsize(path)//1024}KB")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, spec in TRACKS.items():
        draw_track(name, spec)
