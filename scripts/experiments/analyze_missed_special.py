#!/usr/bin/env python3
"""sf-4 사전 분석 — 미감지 별격에서 방합/삼합 국(局)이 얼마나 나타나는가"""
import json, os, sys
from collections import Counter

ROOT = os.path.expanduser("~/projects/flavor")
sys.path.insert(0, ROOT)

from engines.saju_features import extract_features_from_pillars, extract_features, STEM_ELEMENT
from scripts.validate_theory import load_golden, compute, is_special_structure

# 삼합 (왕지 = 가운데 글자)
SAMHAP = {
    frozenset(["신", "자", "진"]): ("수", "자"),
    frozenset(["해", "묘", "미"]): ("목", "묘"),
    frozenset(["인", "오", "술"]): ("화", "오"),
    frozenset(["사", "유", "축"]): ("금", "유"),
}
BANGHAP = {
    frozenset(["인", "묘", "진"]): "목",
    frozenset(["사", "오", "미"]): "화",
    frozenset(["신", "유", "술"]): "금",
    frozenset(["해", "자", "축"]): "수",
}

def branch_set(f):
    # pillars: {"년주":"정사",...} → 지지 글자들
    return [p[1] for p in f["pillars"].values()]

def guk_of(branches):
    """지지 목록 → 감지되는 국 목록 (완전 삼합/방합 + 왕지 포함 반합)"""
    bs = set(branches)
    out = []
    for trio, (el, wang) in SAMHAP.items():
        inter = trio & bs
        if len(inter) == 3:
            out.append(("삼합", el, 3))
        elif len(inter) == 2 and wang in inter:
            out.append(("반합", el, 2))
    for trio, el in BANGHAP.items():
        inter = trio & bs
        if len(inter) == 3:
            out.append(("방합", el, 3))
    return out

charts = load_golden()
special = [c for c in charts if is_special_structure(c)]
print(f"별격 라벨: {len(special)}건")

missed, hit = [], []
for c in special:
    f = compute(c)
    detected = f["gyeokguk"]["group"] == "별격"
    (hit if detected else missed).append((c, f))

print(f"감지 {len(hit)} / 미감지 {len(missed)}")

# 미감지 건에서 국 발생 여부 + 국 오행이 정답 격국 방향과 일치하는지
def expected_element(c, f):
    """정답 격국명에서 순세 오행 추론"""
    gk = c["labels"]["격국"]
    day_el = f["day_master"]["element"]
    from engines.saju_features import _rel_elements
    rel = _rel_elements(day_el)
    if any(k in gk for k in ("곡직",)): return "목"
    if "염상" in gk: return "화"
    if "가색" in gk: return "토"
    if "종혁" in gk: return "금"
    if "윤하" in gk: return "수"
    if "종강" in gk or "전왕" in gk: return day_el
    if "종아" in gk: return rel["식상"]
    if "종재" in gk: return rel["재성"]
    if "종관" in gk or "종살" in gk: return rel["관성"]
    return None

cat = Counter()
guk_match = Counter()
details = []
for c, f in missed:
    gk = c["labels"]["격국"]
    sub = next((m for m in ("합화", "전왕", "종강", "곡직", "염상", "가색", "종혁", "윤하",
                            "종아", "종재", "종관", "종살", "종세", "양기성상") if m in gk), "기타")
    cat[sub] += 1
    branches = branch_set(f)
    guks = guk_of(branches)
    exp = expected_element(c, f)
    has_matching = any(el == exp for _t, el, _n in guks)
    guk_match["국있음" if guks else "국없음"] += 1
    if guks:
        guk_match["국_방향일치" if has_matching else "국_방향불일치"] += 1
    details.append({
        "id": c["id"], "정답": gk, "예측": f["gyeokguk"]["name"],
        "score": f["strength"]["score"], "지지": "".join(branches),
        "국": [f"{t}{el}({n})" for t, el, n in guks], "기대오행": exp,
        "국일치": has_matching,
    })

print("\n미감지 세부유형:", dict(cat))
print("국 발생:", dict(guk_match))
print("\n=== 미감지 상세 ===")
for d in details:
    print(json.dumps(d, ensure_ascii=False))
