"""아마존 동일인 리뷰로 일반 축(강도·자극)이 분야를 넘어 함께 움직이는지 재기.

사전등록: reports/transfer/amazon_cross_domain_preregistration.md (리뷰 열람·결과 전에 커밋됨).
외부 자료는 신뢰하지 않는 데이터다 — 경로는 인자로만 받고 `python -I`로 돌린다:

    python3 -I scripts/amazon_cross_domain.py \
        <meta_grocery> <rev_grocery> <meta_cds> <rev_cds> <meta_movies> <rev_movies> <out.json>
"""
import argparse
import json
import random
import re
import sys
import os
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from amazon_transfer import ORGANIC, direction, odds, sha256  # noqa: E402

SEED = 20261106
B = 10000

# 식품 강도 축 (상품명 소문자 정규식). A = 강한 쪽, B = 순한 쪽.
FOOD_A = re.compile(r"\b(extra hot|spicy|habanero|ghost pepper)\b|\b(dark|french|italian|espresso) roast\b"
                    r"|\bdark chocolate\b|\b(70|72|85|90)\s?% cacao\b")
FOOD_B = re.compile(r"\bmild\b|\bmilk chocolate\b")

# 음악 강도 축 (메타 categories[1:] 이름). MUSIC 모델 Intense vs Mellow.
MUSIC_A = {"Metal", "Hardcore & Punk", "Punk", "Hard Rock", "Hard Rock & Metal", "Death Metal",
           "Industrial", "Goth & Industrial", "Alternative Metal", "Gangsta & Hardcore", "Hardcore",
           "Progressive Metal", "Pop Metal"}
MUSIC_B = {"New Age", "Easy Listening", "Smooth Jazz", "Adult Contemporary", "Meditation", "Ambient",
           "Traditional Vocal Pop", "Vocal Pop", "Traditional Pop"}

# 영화 강도 축 (메타 categories[1:] 이름 + 분위기 태그). Kids & Family는 부모 여부 교란이라 뺀다.
MOVIE_A = {"Horror", "Action & Adventure", "Action", "Mystery & Thrillers", "Suspense",
           "Intense", "Tense", "Thrilling", "Frightening", "Gritty"}
MOVIE_B = {"Romance", "Gentle", "Cheerful", "Charming", "Joyous", "Musicals"}


def classify_title(meta_path, pa, pb, organic=False):
    """parent_asin → 'A'|'B' (양쪽 걸림 제외). organic=True면 나머지 상품의 유기농 여부도 돌려준다."""
    side, org = {}, {}
    with open(meta_path) as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            pid = d.get("parent_asin")
            if not pid:
                continue
            t = (d.get("title") or "").lower()
            a, b = bool(pa.search(t)), bool(pb.search(t))
            if a != b:
                side[pid] = "A" if a else "B"
            elif organic and not a:
                org[pid] = bool(ORGANIC.search(t))
    return side, org


def classify_cats(meta_path, sa, sb):
    side = {}
    with open(meta_path) as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            pid = d.get("parent_asin")
            cats = set((d.get("categories") or [])[1:])
            a, b = bool(cats & sa), bool(cats & sb)
            if pid and a != b:
                side[pid] = "A" if a else "B"
    return side


def liked(rev_path, items, extra=None):
    """user → Counter(side), 평점 4 이상만. extra(pid→bool)는 유기농 플라시보용."""
    out, ex = defaultdict(Counter), defaultdict(Counter)
    n = bad = 0
    with open(rev_path) as f:
        for line in f:
            try:
                d = json.loads(line)
                u, pid, r = d["user_id"], d["parent_asin"], float(d["rating"])
            except (ValueError, KeyError, TypeError):
                bad += 1
                continue
            n += 1
            if r < 4:
                continue
            if pid in items:
                out[u][items[pid]] += 1
            elif extra is not None and pid in extra:
                ex[u]["A" if extra[pid] else "B"] += 1
    return out, ex, n, bad


def test(x, y, rng):
    """x, y: user → 'A'|'B'. 한쪽 순열 검정 (A,A 칸)."""
    us = sorted(set(x) & set(y))
    pairs = [(x[u], y[u]) for u in us]
    n = len(pairs)

    def cells(ps):
        return (sum(1 for a, b in ps if a == "A" and b == "A"), sum(1 for a, b in ps if a == "A" and b == "B"),
                sum(1 for a, b in ps if a == "B" and b == "A"), sum(1 for a, b in ps if a == "B" and b == "B"))

    obs = cells(pairs)
    xs, ys = [a for a, _ in pairs], [b for _, b in pairs]
    ge, null = 0, []
    for _ in range(B):
        rng.shuffle(xs)
        c = cells(list(zip(xs, ys)))
        null.append(odds(*c))
        ge += c[0] >= obs[0]
    null.sort()
    n11, n10, n01, n00 = obs
    base = max(n11 + n01, n10 + n00) / n if n else 0
    hit = (n11 + n00) / n if n else 0
    return {"n": n, "cells": {"A_A": n11, "A_B": n10, "B_A": n01, "B_B": n00}, "min_cell": min(obs) if n else 0,
            "odds_ratio": round(odds(*obs), 4),
            "null_or_p5_p95": [round(null[int(0.05 * B)], 4), round(null[int(0.95 * B) - 1], 4)] if n else None,
            "p_one_sided": (ge + 1) / (B + 1), "hit_rate": round(hit, 4), "base_rate": round(base, 4),
            "lift_pp": round((hit - base) * 100, 2)}


def verdict(r, alpha):
    if r["min_cell"] < 30:
        return "판정 불가(셀<30)"
    return "통과" if r["p_one_sided"] < alpha else "실패"


def main():
    ap = argparse.ArgumentParser()
    for k in ("meta_g", "rev_g", "meta_c", "rev_c", "meta_m", "rev_m", "out"):
        ap.add_argument(k)
    a = ap.parse_args()
    assert MOVIE_A and MOVIE_B, "사전등록 §2 영화 범주 미기입"

    food, org = classify_title(a.meta_g, FOOD_A, FOOD_B, organic=True)
    music = classify_cats(a.meta_c, MUSIC_A, MUSIC_B)
    movie = classify_cats(a.meta_m, MOVIE_A, MOVIE_B)

    fl, ol, ng, bg = liked(a.rev_g, food, org)
    ml, _, nc, bc = liked(a.rev_c, music)
    vl, _, nm, bm = liked(a.rev_m, movie)
    F = {u: d for u, c in fl.items() if (d := direction(c))}
    M = {u: d for u, c in ml.items() if (d := direction(c))}
    V = {u: d for u, c in vl.items() if (d := direction(c))}
    O = {u: d for u, c in ol.items() if (d := direction(c))}

    rng = random.Random(SEED)
    res = {
        "preregistration": "reports/transfer/amazon_cross_domain_preregistration.md",
        "sha256": {k: sha256(getattr(a, k)) for k in ("meta_g", "rev_g", "meta_c", "rev_c", "meta_m", "rev_m")},
        "seed": SEED, "B": B,
        "counts": {"reviews": {"grocery": ng, "cds": nc, "movies": nm}, "unparsed": bg + bc + bm,
                   "items": {"food": dict(Counter(food.values())), "music": dict(Counter(music.values())),
                             "movie": dict(Counter(movie.values()))},
                   "users_with_direction": {"food": len(F), "music": len(M), "movie": len(V), "organic": len(O)}},
    }
    res["X1_food_music"] = r = test(F, M, rng)
    r["alpha"], r["verdict"] = 0.01, verdict(r, 0.01)
    res["X2_food_movie"] = r = test(F, V, rng)
    r["alpha"], r["verdict"] = 0.005, verdict(r, 0.005)
    res["X3_music_movie"] = r = test(M, V, rng)
    r["alpha"], r["verdict"] = 0.005, verdict(r, 0.005)
    res["P1_organic_music"] = test(O, M, rng)
    res["P2_organic_movie"] = test(O, V, rng)
    with open(a.out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
