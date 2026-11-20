"""Young People Survey로 일반 축 2개(폭·강도)가 서로 다른 축인지 재기.

사전등록: reports/transfer/yps_axis_distinct_preregistration.md (결과 전에 커밋됨).
외부 자료는 신뢰하지 않는 데이터다 — 경로는 인자로만 받고 `python -I`로 돌린다:

    python3 -I scripts/yps_axis_distinct.py <responses.csv> <out.json>
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

SEED = 20261120
B = 1000
INTENSE = {"music": MUSIC, "movie": MOVIE_A + MOVIE_B, "hobby": ADREN}
WITHIN = [("BM", "BV"), ("BM", "BH"), ("BV", "BH"), ("M", "V"), ("M", "A"), ("V", "A")]
CROSS = [("BM", "V"), ("BM", "A"), ("BV", "M"), ("BV", "A"), ("BH", "M"), ("BH", "V")]
KEYS = ["BM", "BV", "BH", "M", "V", "A"]


def partials(data):
    """data: list of tuples (g, age, acq, *scores) → 잔차 dict."""
    g, a, q = [d[0] for d in data], ranks([d[1] for d in data]), ranks([d[2] for d in data])
    res = {}
    for i, k in enumerate(KEYS):
        res[k] = residualize(ranks([d[3 + i] for d in data]), [g, a, q])
    comp_b = [sum(t) / 3 for t in zip(*(ranks([d[3 + i] for d in data]) for i in range(3)))]
    comp_i = [sum(t) / 3 for t in zip(*(ranks([d[3 + i] for d in data]) for i in range(3, 6)))]
    res["CB"] = residualize(ranks(comp_b), [g, a, q])
    res["CI"] = residualize(ranks(comp_i), [g, a, q])
    return res


def summarize(data):
    e = partials(data)
    w = {f"{x}-{y}": corr(e[x], e[y]) for x, y in WITHIN}
    c = {f"{x}-{y}": corr(e[x], e[y]) for x, y in CROSS}
    delta = sum(w.values()) / 6 - sum(c.values()) / 6
    return w, c, delta, corr(e["CB"], e["CI"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("responses")
    ap.add_argument("out")
    a = ap.parse_args()
    with open(a.responses, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        header = rd.fieldnames
        cols = {k: block(header, k) for k in ("music", "movie", "hobby", "acq")}
        for k in ("music", "movie", "hobby"):
            assert len(cols[k]) == SIZE[k], k
            for item in INTENSE[k]:
                assert item in cols[k], item
            cols[k] = [c for c in cols[k] if c not in INTENSE[k]]
        assert [len(cols[k]) for k in ("music", "movie", "hobby")] == [15, 7, 31]
        data, dropped = [], 0
        for r in rd:
            g = {"female": 1.0, "male": 0.0}.get((r.get("Gender") or "").strip())
            d = (g, num(r, "Age"), acq(r, cols["acq"]),
                 breadth(r, cols["music"]), breadth(r, cols["movie"]), breadth(r, cols["hobby"]),
                 score(r, MUSIC), score(r, MOVIE_A, MOVIE_B), score(r, ADREN))
            if None in d:
                dropped += 1
                continue
            data.append(d)

    w, c, delta, comp = summarize(data)
    rng = random.Random(SEED)
    boots = []
    for _ in range(B):
        s = [data[rng.randrange(len(data))] for _ in data]
        boots.append(summarize(s)[2])
    boots.sort()
    lo, hi = boots[int(0.025 * B)], boots[int(0.975 * B) - 1]
    d1 = delta > 0.10 and lo > 0
    d2 = abs(comp) < 0.5
    verdict = ("두 축은 구별된다" if d1 and d2 else "구별되나 많이 겹친다" if d1 else "한 축으로 합쳐 읽는다")
    res = {"preregistration": "reports/transfer/yps_axis_distinct_preregistration.md",
           "data_sha256": sha256(a.responses), "seed": SEED, "B": B,
           "items": {k: len(cols[k]) for k in ("music", "movie", "hobby")},
           "counts": {"rows_used": len(data), "dropped_any_missing": dropped},
           "within_axis": {k: round(v, 4) for k, v in w.items()},
           "cross_axis": {k: round(v, 4) for k, v in c.items()},
           "D1": {"delta": round(delta, 4), "ci95": [round(lo, 4), round(hi, 4)], "pass": d1},
           "D2": {"composite_partial": round(comp, 4), "pass": d2},
           "verdict": verdict}
    with open(a.out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
