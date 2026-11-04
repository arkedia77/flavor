"""Last.fm 1K 장르 단위 재측정 — 레이어 2가 레이어 4보다 덜 움직이나.

사전등록: reports/taste_drift/lastfm1k_genre_preregistration.md (결과 전에 커밋됨).

    python3 -I scripts/lastfm_genre_drift.py <lastfm-dataset-1K.tar.gz> <mb_genres.jsonl> <out.json>

mb_genres.jsonl = 줄마다 {"mbid", "genres": [[name, count], ...]} (MusicBrainz artist?inc=genres).
"""
import argparse
import json
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lastfm_drift import (MIN_GAP, SEED, WINDOW, cos, members, parse,  # noqa: E402
                          quantiles, read_lines, sha256, sign_test)

MIN_GENRE_PLAYS = 200
HALVES = ("E1", "E2", "L1", "L2")


def load_genres(path):
    out = {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            g = [(n, c) for n, c in r.get("genres", []) if c > 0]
            tot = sum(c for _, c in g)
            if tot:
                out[r["mbid"]] = {n: c / tot for n, c in g}
    return out


def to_genre(counter, genres):
    v = Counter()
    for art, n in counter.items():
        for g, w in genres[art].items():
            v[g] += n * w
    return v


def metrics(h, g):
    W = (cos(h["E1"], h["E2"]) + cos(h["L1"], h["L2"])) / 2
    X = (cos(h["E1"], h["L2"]) + cos(h["E2"], h["L1"])) / 2
    O = (cos(h["E1"], g["L2"]) + cos(h["E2"], g["L1"])) / 2
    return W, X, O


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tgz")
    ap.add_argument("genres")
    ap.add_argument("out")
    a = ap.parse_args()

    genres = load_genres(a.genres)
    plays_name, _ = members(a.tgz)

    first, last = {}, {}
    for line in read_lines(a.tgz, plays_name):
        r = parse(line)
        if r is None:
            continue
        u, ts, _ = r
        if u not in first or ts < first[u]:
            first[u] = ts
        if u not in last or ts > last[u]:
            last[u] = ts
    eligible = {u for u in first if (last[u] - WINDOW) - (first[u] + WINDOW) >= MIN_GAP}

    halves = defaultdict(lambda: {k: Counter() for k in HALVES})
    total = Counter()
    for line in read_lines(a.tgz, plays_name):
        r = parse(line)
        if r is None:
            continue
        u, ts, key = r
        if u not in eligible:
            continue
        half = "1" if ts.date().toordinal() % 2 else "2"
        if ts < first[u] + WINDOW:
            seg = "E" + half
        elif ts > last[u] - WINDOW:
            seg = "L" + half
        else:
            continue
        total[u] += 1
        if key in genres:
            halves[u][seg][key] += 1

    users = sorted(u for u, h in halves.items()
                   if all(sum(h[k].values()) >= MIN_GENRE_PLAYS for k in HALVES))
    covered = sum(sum(sum(halves[u][k].values()) for k in HALVES) for u in users)
    coverage = covered / sum(total[u] for u in users) if users else 0

    rng = random.Random(SEED)
    partner = {}
    for u in users:
        v = u
        while v == u:
            v = rng.choice(users)
        partner[u] = v

    gen = {u: {k: to_genre(halves[u][k], genres) for k in HALVES} for u in users}
    rows = {}
    for u in users:
        Wa, Xa, Oa = metrics(halves[u], halves[partner[u]])
        Wg, Xg, Og = metrics(gen[u], gen[partner[u]])
        if Wa > Oa and Wg > Og:
            rows[u] = dict(Wa=Wa, Xa=Xa, Oa=Oa, Ma=(Wa - Xa) / (Wa - Oa),
                           Wg=Wg, Xg=Xg, Og=Og, Mg=(Wg - Xg) / (Wg - Og))

    g1 = sign_test([r["Ma"] - r["Mg"] for r in rows.values()])
    g2 = sign_test([r["Wg"] - r["Xg"] for r in rows.values()])
    col = lambda k: [r[k] for r in rows.values()]
    res = {
        "preregistration": "reports/taste_drift/lastfm1k_genre_preregistration.md",
        "data_sha256": sha256(a.tgz), "genres_sha256": sha256(a.genres), "seed": SEED,
        "counts": {"artists_with_genres": len(genres), "eligible_span": len(eligible),
                   "users_min_plays": len(users), "analysed": len(rows),
                   "play_coverage_by_genre_artists": round(coverage, 4)},
        "G1_layer2_moves_less": {"positive": g1[0], "nonzero": g1[1], "p_one_sided": g1[2], "pass": g1[2] < 0.01},
        "G2_genre_changes": {"positive": g2[0], "nonzero": g2[1], "p_one_sided": g2[2], "pass": g2[2] < 0.01},
        "M_artist_restricted": quantiles(col("Ma")),
        "M_genre": quantiles(col("Mg")),
        "genre_W": quantiles(col("Wg")), "genre_X": quantiles(col("Xg")), "genre_O": quantiles(col("Og")),
    }
    with open(a.out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
