"""Open Gauquelin 출생 시점 × 직업 1차 스크린.

사전등록: reports/saju_signal/og_screen_preregistration.md (결과 전에 커밋됨).
외부 CSV는 신뢰하지 않는 데이터다 — 경로는 인자로만 받고 `python -I`로 돌린다:

    .venv/bin/python -I scripts/og_saju_screen.py <ogdb-time-sep.csv> <out.json> [--cache feats.json]

-I 모드라 레포 루트를 sys.path에 직접 넣는다.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.saju_features import extract_features  # noqa: E402

SEED = 20261103
OCCUPATIONS = [
    "military-personnel", "physician", "politician", "painter", "actor",
    "scientist", "writer", "journalist", "musician", "catholic-priest",
    "executive", "football-player", "cyclist", "conductor-of-military-band",
    "aircraft-pilot", "novelist", "poet", "athletics-competitor",
]
EUROPE = {"FR", "IT", "DE", "BE", "NL", "GB", "ES", "CH", "AT", "LU"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rows(path):
    main, aux, skipped = [], [], Counter()
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["OCCU"] not in OCCUPATIONS:
                skipped["occupation"] += 1
                continue
            if r["Y"] and r["H"] and not (r["H"].isdigit() and 0 <= int(r["H"]) <= 23):
                # 실행 중 발견(사전등록 밖 파싱 규칙): '.2'·'  '·'24' 등은 버린다
                skipped["malformed_hour"] += 1
                continue
            if r["Y"] and r["MON"] and r["D"] and r["H"]:
                rec = dict(id=r["OGID"], occ=r["OCCU"], cy=r["CY"],
                           y=int(r["Y"]), m=int(r["MON"]), d=int(r["D"]),
                           h=int(r["H"]), sample="main")
                main.append(rec)
            elif (r["Y-UT"] and r["H-UT"].isdigit() and r["CY"] in EUROPE
                  and 0 <= int(r["H-UT"]) <= 21):
                rec = dict(id=r["OGID"], occ=r["OCCU"], cy=r["CY"],
                           y=int(r["Y-UT"]), m=int(r["MON-UT"]), d=int(r["D-UT"]),
                           h=None, sample="aux")
                aux.append(rec)
            else:
                skipped["no_usable_date"] += 1
    return main, aux, skipped


def features(rec, cache):
    key = f'{rec["y"]}-{rec["m"]}-{rec["d"]}-{rec["h"]}'
    if key not in cache:
        o = extract_features(rec["y"], rec["m"], rec["d"], rec["h"])
        p = o["pillars"]
        cache[key] = {
            "day_stem": o["day_master"]["stem"],
            "yongsin": o["yongsin"]["element"],
            "strength": o["strength"]["label"],
            "gyeok_group": o["gyeokguk"]["group"],
            "month_branch": p["월주"][1],
            "hour_branch": p["시주"][1] if p.get("시주") else None,
        }
    return cache[key]


def chi2(xs, ys):
    """xs, ys: 정수 코드 리스트. 기대값은 주변합에서 — 순열 하에서 불변."""
    kx, ky = max(xs) + 1, max(ys) + 1
    n = len(xs)
    cx, cy = Counter(xs), Counter(ys)
    obs = Counter(zip(xs, ys))
    s = 0.0
    for i in range(kx):
        for j in range(ky):
            e = cx[i] * cy[j] / n
            if e > 0:
                s += (obs[(i, j)] - e) ** 2 / e
    return s, min(len(cx), len(cy))


def cramers_v(stat, n, k):
    return math.sqrt(stat / (n * (k - 1))) if k > 1 else 0.0


def encode(vals):
    levels = sorted(set(vals))
    idx = {v: i for i, v in enumerate(levels)}
    return [idx[v] for v in vals], levels


def perm_test(feat, occ, strata, B, rng):
    """strata=None이면 전체 섞기, 아니면 층 안에서만 섞기."""
    x, _ = encode(feat)
    y, _ = encode(occ)
    obs, k = chi2(x, y)
    n = len(x)
    groups = defaultdict(list)
    for i, s in enumerate(strata if strata is not None else [0] * n):
        groups[s].append(i)
    groups = [g for g in groups.values() if len(g) > 1]
    ge, null_v = 0, []
    yp = list(y)
    for _ in range(B):
        for g in groups:
            lab = [y[i] for i in g]
            rng.shuffle(lab)
            for i, v in zip(g, lab):
                yp[i] = v
        s, _ = chi2(x, yp)
        null_v.append(cramers_v(s, n, k))
        if s >= obs:
            ge += 1
    null_v.sort()
    return {
        "n": n, "chi2": round(obs, 3), "p_perm": (ge + 1) / (B + 1), "B": B,
        "cramers_v": round(cramers_v(obs, n, k), 5),
        "null_v_p99": round(null_v[int(0.99 * B) - 1], 5),
        "n_strata": len(groups) if strata is not None else None,
    }


def cv_logloss_gain(feat, occ, folds=5, alpha=1.0, seed=SEED):
    """일간→직업 분포 vs 전체 직업 분포, 5겹 CV 평균 로그손실 차(nats/인). 양수=일간이 나음."""
    rng = random.Random(seed)
    idx = list(range(len(feat)))
    rng.shuffle(idx)
    occs = sorted(set(occ))
    K = len(occs)
    base_ll = cond_ll = 0.0
    for f in range(folds):
        test = set(idx[f::folds])
        tr = [i for i in idx if i not in test]
        base = Counter(occ[i] for i in tr)
        cond = defaultdict(Counter)
        for i in tr:
            cond[feat[i]][occ[i]] += 1
        nb = len(tr)
        for i in test:
            base_ll -= math.log((base[occ[i]] + alpha) / (nb + alpha * K))
            c = cond[feat[i]]
            cond_ll -= math.log((c[occ[i]] + alpha) / (sum(c.values()) + alpha * K))
    n = len(feat)
    return round((base_ll - cond_ll) / n, 6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("out")
    ap.add_argument("--cache")
    ap.add_argument("--B", type=int, default=10000)
    ap.add_argument("--B2", type=int, default=2000)
    a = ap.parse_args()

    cache = {}
    if a.cache and os.path.exists(a.cache):
        with open(a.cache) as f:
            cache = json.load(f)
    main_rows, aux_rows, skipped = load_rows(a.csv)
    bad = Counter()
    for rows in (main_rows, aux_rows):
        for r in rows:
            try:
                r["f"] = features(r, cache)
            except Exception as e:  # 달력상 불가능한 날짜 등
                bad[type(e).__name__] += 1
                r["f"] = None
    if a.cache:
        with open(a.cache, "w") as f:
            json.dump(cache, f, ensure_ascii=False)
    main_rows = [r for r in main_rows if r["f"]]
    aux_rows = [r for r in aux_rows if r["f"]]

    rng = random.Random(SEED)
    res = {
        "preregistration": "reports/saju_signal/og_screen_preregistration.md",
        "data_sha256": sha256(a.csv), "seed": SEED,
        "counts": {"main": len(main_rows), "aux": len(aux_rows),
                   "skipped": dict(skipped), "feature_errors": dict(bad)},
    }

    def p1(rows):
        return perm_test([r["f"]["day_stem"] for r in rows],
                         [r["occ"] for r in rows], None, a.B, rng)

    fr = [r for r in main_rows if r["cy"] == "FR"]
    nonfr = [r for r in main_rows if r["cy"] != "FR"]
    res["P1"] = {"all": p1(main_rows), "FR": p1(fr), "nonFR": p1(nonfr)}
    P = res["P1"]
    res["P1"]["pass"] = (P["all"]["p_perm"] < 0.01 and P["FR"]["p_perm"] < 0.05
                         and P["nonFR"]["p_perm"] < 0.05)
    res["P1"]["cv_logloss_gain_nats"] = cv_logloss_gain(
        [r["f"]["day_stem"] for r in main_rows], [r["occ"] for r in main_rows])

    ym = [f'{r["y"]}|{r["f"]["month_branch"]}' for r in main_rows]
    dc = [f'{r["y"] // 10}|{r["cy"]}' for r in main_rows]
    occ = [r["occ"] for r in main_rows]
    sec = {}
    for name, key, strata in [("S1_yongsin", "yongsin", ym),
                              ("S2_strength", "strength", ym),
                              ("S3_gyeok_group", "gyeok_group", ym),
                              ("S4_hour_branch", "hour_branch", dc)]:
        sec[name] = perm_test([r["f"][key] for r in main_rows], occ, strata, a.B2, rng)
        sec[name]["pass_bonferroni_0.0025"] = sec[name]["p_perm"] < 0.0025
    res["secondary"] = sec

    res["sensitivity_aux_P1"] = p1(aux_rows) if aux_rows else None
    with open(a.out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
