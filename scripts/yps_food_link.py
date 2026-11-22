"""Young People Survey로 음식 즐거움이 일반 축(폭·강도)과 함께 움직이는지 재기.

사전등록: reports/transfer/yps_food_link_preregistration.md (결과 전에 커밋됨).
외부 자료는 신뢰하지 않는 데이터다 — 경로는 인자로만 받고 `python -I`로 돌린다:

    python3 -I scripts/yps_food_link.py <responses.csv> <out.json>
"""
import argparse
import csv
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yps_general_axis import ADREN, MOVIE_A, MOVIE_B, MUSIC, corr, num, ranks, residualize, score, sha256  # noqa: E402
from yps_novelty_breadth import SIZE, acq, block, breadth  # noqa: E402

SEED = 20261122
B = 10000
FOOD = "Eating to survive"
ACQ_DROP = {FOOD, "Healthy eating"}


def partial_test(rows, kx, ky, rng, perm=True):
    data = [(r[kx], r[ky], r["_g"], r["_a"], r["_q"]) for r in rows]
    data = [d for d in data if None not in d]
    x, y, g, a, q = (list(t) for t in zip(*data))
    rx, ry, ra, rq = ranks(x), ranks(y), ranks(a), ranks(q)
    out = {"n": len(x), "spearman_raw": round(corr(rx, ry), 4),
           "partial_age_gender": round(corr(residualize(rx, [g, ra]), residualize(ry, [g, ra])), 4)}
    ex, ey = residualize(rx, [g, ra, rq]), residualize(ry, [g, ra, rq])
    part = corr(ex, ey)
    out["partial_age_gender_acq"] = round(part, 4)
    if perm:
        ge = 0
        for _ in range(B):
            rng.shuffle(ey)
            ge += corr(ex, ey) >= part
        out["p_one_sided"] = (ge + 1) / (B + 1)
    return out


def composite(rows, keys, name):
    idx = [i for i, r in enumerate(rows) if all(r[k] is not None for k in keys)]
    rk = [ranks([rows[i][k] for i in idx]) for k in keys]
    for r in rows:
        r[name] = None
    for j, i in enumerate(idx):
        rows[i][name] = sum(col[j] for col in rk) / len(keys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("responses")
    ap.add_argument("out")
    a = ap.parse_args()
    with open(a.responses, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        header = rd.fieldnames
        cols = {k: block(header, k) for k in ("music", "movie", "hobby", "fear", "acq")}
        for k, n in SIZE.items():
            assert len(cols[k]) == n, k
        assert FOOD in cols["acq"]  # Healthy eating은 ACQ 구간 바로 앞(75열)이라 원래 ACQ에 없다 — 리포트에 공개
        res_acq_dropped = sorted(ACQ_DROP & set(cols["acq"]))
        cols["acq"] = [c for c in cols["acq"] if c not in ACQ_DROP]
        assert not any(w in c.lower().split() for c in cols["hobby"] for w in ("cooking", "food", "eating"))  # 부분 문자열은 Theatre에 걸린다
        rows, dropped = [], 0
        for r in rd:
            g = {"female": 1.0, "male": 0.0}.get((r.get("Gender") or "").strip())
            age = num(r, "Age")
            if g is None or age is None:
                dropped += 1
                continue
            fe = num(r, FOOD)
            r["_g"], r["_a"], r["_q"] = g, age, acq(r, cols["acq"])
            r["FE"] = 6 - fe if fe is not None else None
            r["BM"], r["BV"], r["BH"] = (breadth(r, cols[k]) for k in ("music", "movie", "hobby"))
            r["BF"] = breadth(r, cols["fear"])
            r["M"], r["V"], r["A"] = score(r, MUSIC), score(r, MOVIE_A, MOVIE_B), score(r, ADREN)
            rows.append(r)
    composite(rows, ["BM", "BV", "BH"], "CB")
    composite(rows, ["M", "V", "A"], "CI")

    rng = random.Random(SEED)
    res = {"preregistration": "reports/transfer/yps_food_link_preregistration.md",
           "data_sha256": sha256(a.responses), "seed": SEED, "B": B,
           "acq_items": len(cols["acq"]), "acq_dropped": res_acq_dropped,
           "counts": {"rows_used": len(rows), "dropped_no_gender_or_age": dropped}}
    for key, ky in (("F1_food_breadth", "CB"), ("F2_food_intensity", "CI")):
        t = partial_test(rows, "FE", ky, rng)
        t["alpha"] = 0.01
        t["verdict"] = "통과" if t["p_one_sided"] < 0.01 and t["partial_age_gender_acq"] > 0 else "실패"
        res[key] = t
    res["placebo_food_fear"] = partial_test(rows, "FE", "BF", rng)
    res["exploratory"] = {k: partial_test(rows, "FE", k, rng, perm=False) for k in ("BM", "BV", "BH", "M", "V", "A")}
    with open(a.out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
