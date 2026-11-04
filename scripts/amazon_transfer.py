"""아마존 식품 리뷰로 제품군 간 전이(커피 로스트 → 다른 식품 맛 축) 재기.

사전등록: reports/transfer/amazon_grocery_preregistration.md (리뷰 열람·결과 전에 커밋됨).
외부 자료는 신뢰하지 않는 데이터다 — 경로는 인자로만 받고 `python -I`로 돌린다:

    python3 -I scripts/amazon_transfer.py <meta.jsonl> <reviews.jsonl> <out.json>
"""
import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict

SEED = 20261103
B = 10000
AXES = {
    "coffee": (r"\b(light|blonde|cinnamon) roast\b", r"\b(dark|french|italian|espresso) roast\b"),
    "T1_chocolate": (r"\bdark chocolate\b|\b(70|72|85|90)\s?% cacao\b", r"\bmilk chocolate\b"),
    "T2_tea": (r"\bgreen tea\b", r"\bblack tea\b|\bearl grey\b|\bbreakfast tea\b"),
    "T3_spicy": (r"\b(extra hot|spicy|habanero|ghost pepper)\b", r"\bmild\b"),
}
# 사전등록 §4 방향: 커피의 어느 쪽이 축의 A쪽과 짝인가
PAIRING = {"T1_chocolate": "dark", "T2_tea": "light", "T3_spicy": "dark"}
ALPHA = {"T1_chocolate": 0.01, "T2_tea": 0.01 / 3, "T3_spicy": 0.01 / 3}
ORGANIC = re.compile(r"\borganic\b")
COMPILED = {k: (re.compile(a), re.compile(b)) for k, (a, b) in AXES.items()}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(meta_path):
    """parent_asin → (축, 'A'|'B') 또는 ('other', organic여부). 축 둘 이상·양쪽 걸림은 제외."""
    item_axis, organic, excluded = {}, {}, 0
    with open(meta_path) as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            t = (d.get("title") or "").lower()
            pid = d.get("parent_asin")
            if not pid:
                continue
            hits = []
            for axis, (pa, pb) in COMPILED.items():
                a, b = bool(pa.search(t)), bool(pb.search(t))
                if a or b:
                    hits.append((axis, a, b))
            if len(hits) > 1 or (hits and hits[0][1] and hits[0][2]):
                excluded += 1
                continue
            if hits:
                axis, a, _ = hits[0]
                item_axis[pid] = (axis, "A" if a else "B")
            else:
                organic[pid] = bool(ORGANIC.search(t))
    return item_axis, organic, excluded


def direction(counter):
    a, b = counter["A"], counter["B"]
    return "A" if a > b else "B" if b > a else None


def table(pairs, coffee_side):
    """pairs: [(coffee 'light'|'dark', axis 'A'|'B')] → 2×2 + 지표."""
    n11 = sum(1 for c, t in pairs if c == coffee_side and t == "A")
    n10 = sum(1 for c, t in pairs if c == coffee_side and t == "B")
    n01 = sum(1 for c, t in pairs if c != coffee_side and t == "A")
    n00 = sum(1 for c, t in pairs if c != coffee_side and t == "B")
    return n11, n10, n01, n00


def odds(n11, n10, n01, n00):
    return ((n11 + 0.5) * (n00 + 0.5)) / ((n10 + 0.5) * (n01 + 0.5))


def perm(pairs, coffee_side, rng):
    obs = table(pairs, coffee_side)
    cs = [c for c, _ in pairs]
    ts = [t for _, t in pairs]
    ge, null_or = 0, []
    for _ in range(B):
        rng.shuffle(cs)
        tb = table(list(zip(cs, ts)), coffee_side)
        null_or.append(odds(*tb))
        if tb[0] >= obs[0]:
            ge += 1
    null_or.sort()
    n = len(pairs)
    n11, n10, n01, n00 = obs
    base = max(n11 + n01, n10 + n00) / n if n else 0
    # 커피 방향으로 축 방향을 맞히는 규칙: 짝 방향이면 A, 아니면 B
    hit = (n11 + n00) / n if n else 0
    return {
        "n": n, "cells": {"pair_A": n11, "pair_B": n10, "other_A": n01, "other_B": n00},
        "min_cell": min(obs), "odds_ratio": round(odds(*obs), 4),
        "null_or_p5_p95": [round(null_or[int(0.05 * B)], 4), round(null_or[int(0.95 * B) - 1], 4)],
        "p_one_sided": (ge + 1) / (B + 1),
        "hit_rate": round(hit, 4), "base_rate": round(base, 4), "lift_pp": round((hit - base) * 100, 2),
    }


def run(users, organic_users, rng):
    coffee = {u: {"A": "light", "B": "dark"}[d] for u, ax in users.items()
              if (d := direction(ax["coffee"]))}
    out = {"n_users_coffee_direction": len(coffee)}
    for axis, side in PAIRING.items():
        pairs = [(coffee[u], d) for u in coffee if (d := direction(users[u][axis]))]
        r = perm(pairs, side, rng)
        r["alpha"] = ALPHA[axis]
        r["verdict"] = ("판정 불가(셀<30)" if r["min_cell"] < 30
                        else "통과" if r["p_one_sided"] < ALPHA[axis] else "실패")
        out[axis] = r
    pairs = [(coffee[u], "A" if organic_users[u]["A"] > organic_users[u]["B"] else "B")
             for u in coffee if organic_users[u]["A"] != organic_users[u]["B"]]
    out["S2_placebo_organic"] = perm(pairs, "light", rng)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meta")
    ap.add_argument("reviews")
    ap.add_argument("out")
    a = ap.parse_args()

    item_axis, organic, excluded = classify(a.meta)
    liked = defaultdict(lambda: defaultdict(Counter))
    allrev = defaultdict(lambda: defaultdict(Counter))
    org_liked = defaultdict(Counter)
    org_all = defaultdict(Counter)
    n_rev = bad = 0
    with open(a.reviews) as f:
        for line in f:
            try:
                d = json.loads(line)
                u, pid, rating = d["user_id"], d["parent_asin"], float(d["rating"])
            except (ValueError, KeyError, TypeError):
                bad += 1
                continue
            n_rev += 1
            if pid in item_axis:
                axis, side = item_axis[pid]
                allrev[u][axis][side] += 1
                if rating >= 4:
                    liked[u][axis][side] += 1
            elif pid in organic:
                s = "A" if organic[pid] else "B"
                org_all[u][s] += 1
                if rating >= 4:
                    org_liked[u][s] += 1

    res = {
        "preregistration": "reports/transfer/amazon_grocery_preregistration.md",
        "meta_sha256": sha256(a.meta), "reviews_sha256": sha256(a.reviews), "seed": SEED, "B": B,
        "counts": {"reviews": n_rev, "unparsed": bad, "axis_items": len(item_axis),
                   "axis_items_by_side": dict(Counter(f"{ax}:{s}" for ax, s in item_axis.values())),
                   "excluded_multi_axis_items": excluded},
        "main_liked": run(liked, org_liked, random.Random(SEED)),
        "S1_all_reviews": run(allrev, org_all, random.Random(SEED + 1)),
    }
    with open(a.out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
