"""Young People Survey로 새것 추구(취향의 폭)가 나이·성별·응답 성향을 빼고도 분야를 넘어 함께 움직이는지 재기.

사전등록: reports/transfer/yps_novelty_breadth_preregistration.md (결과 전에 커밋됨).
외부 자료는 신뢰하지 않는 데이터다 — 경로는 인자로만 받고 `python -I`로 돌린다:

    python3 -I scripts/yps_novelty_breadth.py <responses.csv> <out.json>
"""
import argparse
import csv
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yps_general_axis import corr, num, ranks, residualize, sha256  # noqa: E402

SEED = 20261116
B = 10000

# 묶음 = 응답 헤더에서 [첫 문항, 끝 문항] 구간 (columns.csv 순서)
BLOCKS = {"music": ("Dance", "Opera"), "movie": ("Horror", "Action"), "hobby": ("History", "Pets"),
          "fear": ("Flying", "Fear of public speaking"), "acq": ("Daily events", "Spending on healthy eating")}
SIZE = {"music": 17, "movie": 11, "hobby": 32, "fear": 10}


def block(header, name):
    a, b = BLOCKS[name]
    i, j = header.index(a), header.index(b)
    return header[i:j + 1]


def breadth(row, cols):
    v = [num(row, k) for k in cols]
    v = [x for x in v if x is not None]
    if len(v) < 0.8 * len(cols):
        return None
    return sum(1 for x in v if x >= 4) / len(v)


def acq(row, cols):
    v = [num(row, k) for k in cols]
    v = [x for x in v if x is not None and 1 <= x <= 5]
    return sum(v) / len(v) if len(v) >= 40 else None


def test(rows, kx, ky, rng):
    data = [(r[kx], r[ky], r["_g"], r["_a"], r["_q"]) for r in rows]
    data = [d for d in data if None not in d]
    x, y, g, a, q = (list(t) for t in zip(*data))
    rx, ry, ra, rq = ranks(x), ranks(y), ranks(a), ranks(q)
    raw = corr(rx, ry)
    p_ag = corr(residualize(rx, [g, ra]), residualize(ry, [g, ra]))
    ex, ey = residualize(rx, [g, ra, rq]), residualize(ry, [g, ra, rq])
    part = corr(ex, ey)
    ge = 0
    for _ in range(B):
        rng.shuffle(ey)
        ge += corr(ex, ey) >= part
    return {"n": len(x), "spearman_raw": round(raw, 4), "partial_age_gender": round(p_ag, 4),
            "partial_age_gender_acq": round(part, 4), "p_one_sided": (ge + 1) / (B + 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("responses")
    ap.add_argument("out")
    a = ap.parse_args()
    with open(a.responses, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        header = rd.fieldnames
        cols = {k: block(header, k) for k in BLOCKS}
        for k, n in SIZE.items():
            assert len(cols[k]) == n, (k, cols[k])
        rows, dropped = [], 0
        for r in rd:
            g = {"female": 1.0, "male": 0.0}.get((r.get("Gender") or "").strip())
            age = num(r, "Age")
            if g is None or age is None:
                dropped += 1
                continue
            r["_g"], r["_a"], r["_q"] = g, age, acq(r, cols["acq"])
            for k in SIZE:
                r["_" + k] = breadth(r, cols[k])
            rows.append(r)

    rng = random.Random(SEED)
    res = {"preregistration": "reports/transfer/yps_novelty_breadth_preregistration.md",
           "data_sha256": sha256(a.responses), "seed": SEED, "B": B,
           "blocks": {k: [v[0], v[-1], len(v)] for k, v in cols.items()},
           "counts": {"rows_used": len(rows), "dropped_no_gender_or_age": dropped}}
    for key, kx, ky, alpha in (("N1_music_movie", "_music", "_movie", 0.01),
                               ("N2_music_hobby", "_music", "_hobby", 0.005),
                               ("N3_movie_hobby", "_movie", "_hobby", 0.005)):
        r = test(rows, kx, ky, rng)
        r["alpha"] = alpha
        r["verdict"] = "통과" if r["p_one_sided"] < alpha and r["partial_age_gender_acq"] > 0 else "실패"
        res[key] = r
    res["P1_fear_music"] = test(rows, "_fear", "_music", rng)
    res["P2_fear_movie"] = test(rows, "_fear", "_movie", rng)
    with open(a.out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
