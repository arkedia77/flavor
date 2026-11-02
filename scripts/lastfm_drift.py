"""Last.fm 1K로 같은 사람의 취향 변화 크기 재기.

사전등록: reports/taste_drift/lastfm1k_preregistration.md (결과 전에 커밋됨).
외부 자료는 신뢰하지 않는 데이터다 — 경로는 인자로만 받고 `python -I`로 돌린다:

    python3 -I scripts/lastfm_drift.py <lastfm-dataset-1K.tar.gz> <out.json>

원자료는 비상업 라이선스다. 레포에는 집계 수치만 남긴다.
"""
import argparse
import hashlib
import io
import json
import math
import random
import tarfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta

SEED = 20261103
WINDOW = timedelta(days=182)
MIN_GAP = timedelta(days=365)
MIN_PLAYS = 1000


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def members(path):
    tf = tarfile.open(path, "r:gz")
    plays = profile = None
    for m in tf:
        if m.name.endswith("userid-timestamp-artid-artname-traid-traname.tsv"):
            plays = m.name
        elif m.name.endswith("userid-profile.tsv"):
            profile = m.name
    tf.close()
    return plays, profile


def read_lines(path, name):
    with tarfile.open(path, "r:gz") as tf:
        f = tf.extractfile(name)
        for line in io.TextIOWrapper(f, encoding="utf-8", errors="replace"):
            yield line.rstrip("\n")


def parse(line):
    p = line.split("\t")
    if len(p) < 4:
        return None
    try:
        ts = datetime.strptime(p[1], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    key = p[2] if p[2] else "name:" + p[3].strip().lower()
    return p[0], ts, key


def cos(a, b):
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb)


def sign_test(diffs):
    """한쪽 부호검정 p (양수 방향). 0은 버린다. 정규근사(연속성 보정)."""
    pos = sum(1 for d in diffs if d > 0)
    n = sum(1 for d in diffs if d != 0)
    if n == 0:
        return pos, n, 1.0
    z = (pos - 0.5 - n / 2) / math.sqrt(n / 4)
    return pos, n, 0.5 * math.erfc(z / math.sqrt(2))


def quantiles(xs):
    xs = sorted(xs)
    if not xs:
        return None
    q = lambda f: xs[min(len(xs) - 1, int(f * len(xs)))]
    return {"q25": round(q(0.25), 4), "median": round(q(0.5), 4), "q75": round(q(0.75), 4), "n": len(xs)}


def spearman(xs, ys):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tgz")
    ap.add_argument("out")
    a = ap.parse_args()

    plays_name, profile_name = members(a.tgz)

    # 1회차: 사용자별 처음·마지막 시각
    first, last, bad = {}, {}, 0
    for line in read_lines(a.tgz, plays_name):
        r = parse(line)
        if r is None:
            bad += 1
            continue
        u, ts, _ = r
        if u not in first or ts < first[u]:
            first[u] = ts
        if u not in last or ts > last[u]:
            last[u] = ts

    eligible_span = {u for u in first if (last[u] - WINDOW) - (first[u] + WINDOW) >= MIN_GAP}

    # 2회차: E1/E2/L1/L2 벡터 + 월별 벡터(S1)
    halves = defaultdict(lambda: {"E1": Counter(), "E2": Counter(), "L1": Counter(), "L2": Counter()})
    monthly = defaultdict(lambda: defaultdict(Counter))
    for line in read_lines(a.tgz, plays_name):
        r = parse(line)
        if r is None:
            continue
        u, ts, key = r
        monthly[u][ts.year * 12 + ts.month - 1][key] += 1
        if u not in eligible_span:
            continue
        half = "1" if ts.date().toordinal() % 2 else "2"
        if ts < first[u] + WINDOW:
            halves[u]["E" + half][key] += 1
        elif ts > last[u] - WINDOW:
            halves[u]["L" + half][key] += 1

    users = sorted(u for u, h in halves.items()
                   if sum(h["E1"].values()) + sum(h["E2"].values()) >= MIN_PLAYS
                   and sum(h["L1"].values()) + sum(h["L2"].values()) >= MIN_PLAYS)

    rng = random.Random(SEED)
    partner = {}
    for u in users:
        v = u
        while v == u:
            v = rng.choice(users)
        partner[u] = v

    W, X, O, M = {}, {}, {}, {}
    for u in users:
        h, g = halves[u], halves[partner[u]]
        W[u] = (cos(h["E1"], h["E2"]) + cos(h["L1"], h["L2"])) / 2
        X[u] = (cos(h["E1"], h["L2"]) + cos(h["E2"], h["L1"])) / 2
        O[u] = (cos(h["E1"], g["L2"]) + cos(h["E2"], g["L1"])) / 2
        if W[u] > O[u]:
            M[u] = (W[u] - X[u]) / (W[u] - O[u])

    h1 = sign_test([W[u] - X[u] for u in users])
    h2 = sign_test([X[u] - O[u] for u in users])

    # S1: 간격 k개월별 같은 사용자 월 벡터 코사인 평균 (월 재생 100건 이상인 달만)
    by_gap = defaultdict(list)
    for u, months in monthly.items():
        ms = sorted(m for m, c in months.items() if sum(c.values()) >= 100)
        for i, m1 in enumerate(ms):
            for m2 in ms[i + 1:]:
                k = m2 - m1
                if k > 36:
                    break
                by_gap[k].append(cos(months[m1], months[m2]))
    s1 = {k: {"mean_cos": round(sum(v) / len(v), 4), "n_pairs": len(v)}
          for k, v in sorted(by_gap.items())}

    # S2: 나이
    ages = {}
    for i, line in enumerate(read_lines(a.tgz, profile_name)):
        p = line.split("\t")
        if i == 0 or len(p) < 3:
            continue
        if p[2].strip().isdigit():
            ages[p[0]] = int(p[2])
    aged = [u for u in M if u in ages and 10 <= ages[u] <= 90]
    s2 = {"n": len(aged),
          "spearman_age_vs_moved_share": round(spearman([ages[u] for u in aged], [M[u] for u in aged]), 4)
          if len(aged) > 2 else None}

    res = {
        "preregistration": "reports/taste_drift/lastfm1k_preregistration.md",
        "data_sha256": sha256(a.tgz), "seed": SEED,
        "counts": {"users_total": len(first), "eligible_span": len(eligible_span),
                   "analysed": len(users), "unparsed_lines": bad,
                   "excluded_from_M_W_le_O": len(users) - len(M)},
        "H1_changes": {"positive": h1[0], "nonzero": h1[1], "p_one_sided": h1[2], "pass": h1[2] < 0.01},
        "H2_partly": {"positive": h2[0], "nonzero": h2[1], "p_one_sided": h2[2], "pass": h2[2] < 0.01},
        "W_within_period": quantiles(list(W.values())),
        "X_across_period": quantiles(list(X.values())),
        "O_other_user": quantiles(list(O.values())),
        "M_moved_share": quantiles(list(M.values())),
        "span_years": quantiles([(last[u] - first[u]).days / 365.25 for u in users]),
        "S1_gap_months": s1,
        "S2_age": s2,
    }
    with open(a.out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in res.items() if k != "S1_gap_months"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
