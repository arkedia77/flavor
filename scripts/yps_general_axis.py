"""Young People Survey(슬로바키아 15–30세 1,010명)로 강도·자극 일반 축이 나이·성별을 빼고도 분야를 넘어 함께 움직이는지 재기.

사전등록: reports/transfer/yps_general_axis_preregistration.md (응답 열람·결과 전에 커밋됨).
외부 자료는 신뢰하지 않는 데이터다 — 경로는 인자로만 받고 `python -I`로 돌린다:

    python3 -I scripts/yps_general_axis.py <responses.csv> <out.json>
"""
import argparse
import csv
import hashlib
import json
import random

SEED = 20261107
B = 10000

MUSIC = ["Metal or Hardrock", "Punk"]
MOVIE_A = ["Horror", "Thriller", "Action"]
MOVIE_B = ["Romantic"]
ADREN = ["Adrenaline sports"]
PLACEBO = ["Spending on healthy eating"]


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def num(row, k):
    try:
        return float(row[k])
    except (KeyError, ValueError, TypeError):
        return None


def score(row, pos, neg=()):
    a = [num(row, k) for k in pos]
    b = [num(row, k) for k in neg]
    if None in a or None in b:
        return None
    s = sum(a) / len(a)
    return s - sum(b) / len(b) if b else s


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def residualize(y, covs):
    """y를 [1, covs...]에 최소제곱 회귀한 잔차 (가우스 소거)."""
    X = [[1.0] + [c[i] for c in covs] for i in range(len(y))]
    p = len(X[0])
    A = [[sum(X[n][i] * X[n][j] for n in range(len(y))) for j in range(p)] for i in range(p)]
    v = [sum(X[n][i] * y[n] for n in range(len(y))) for i in range(p)]
    for i in range(p):
        piv = A[i][i]
        for j in range(i + 1, p):
            f = A[j][i] / piv
            A[j] = [A[j][k] - f * A[i][k] for k in range(p)]
            v[j] -= f * v[i]
    beta = [0.0] * p
    for i in reversed(range(p)):
        beta[i] = (v[i] - sum(A[i][k] * beta[k] for k in range(i + 1, p))) / A[i][i]
    return [y[n] - sum(beta[k] * X[n][k] for k in range(p)) for n in range(len(y))]


def corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    sa = sum((x - ma) ** 2 for x in a) ** 0.5
    sb = sum((y - mb) ** 2 for y in b) ** 0.5
    return sab / (sa * sb) if sa and sb else 0.0


def test(rows, fx, fy, rng):
    """편 스피어만: 순위로 바꾼 뒤 성별·나이를 회귀로 뺀 잔차끼리의 상관. 한쪽 순열 검정."""
    data = [(fx(r), fy(r), r["_g"], r["_a"]) for r in rows]
    data = [d for d in data if None not in d]
    x, y, g, a = (list(t) for t in zip(*data))
    rx, ry, ra = ranks(x), ranks(y), ranks(a)
    raw = corr(rx, ry)
    ex, ey = residualize(rx, [g, ra]), residualize(ry, [g, ra])
    part = corr(ex, ey)
    ge = 0
    for _ in range(B):
        rng.shuffle(ey)
        ge += corr(ex, ey) >= part
    return {"n": len(x), "spearman_raw": round(raw, 4), "spearman_partial_age_gender": round(part, 4),
            "p_one_sided": (ge + 1) / (B + 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("responses")
    ap.add_argument("out")
    a = ap.parse_args()
    rows, dropped = [], 0
    with open(a.responses, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            g = {"female": 1.0, "male": 0.0}.get((r.get("Gender") or "").strip())
            age = num(r, "Age")
            if g is None or age is None:
                dropped += 1
                continue
            r["_g"], r["_a"] = g, age
            rows.append(r)

    def m(r):
        return score(r, MUSIC)

    def v(r):
        return score(r, MOVIE_A, MOVIE_B)

    def ad(r):
        return score(r, ADREN)

    def pl(r):
        return score(r, PLACEBO)

    rng = random.Random(SEED)
    res = {"preregistration": "reports/transfer/yps_general_axis_preregistration.md",
           "data_sha256": sha256(a.responses), "seed": SEED, "B": B,
           "counts": {"rows_used": len(rows), "dropped_no_gender_or_age": dropped}}
    for key, fx, fy, alpha in (("Y1_music_movie", m, v, 0.01), ("Y2_adrenaline_music", ad, m, 0.005),
                               ("Y3_adrenaline_movie", ad, v, 0.005)):
        r = test(rows, fx, fy, rng)
        r["alpha"] = alpha
        r["verdict"] = "통과" if r["p_one_sided"] < alpha and r["spearman_partial_age_gender"] > 0 else "실패"
        res[key] = r
    res["P1_healthyfood_music"] = test(rows, pl, m, rng)
    res["P2_healthyfood_movie"] = test(rows, pl, v, rng)
    with open(a.out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
