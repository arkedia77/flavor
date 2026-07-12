#!/usr/bin/env python3
"""사주 신호 검증 하네스 — Leoflavor v0.2 검증 게이트의 판정 도구

주 타깃: 사주 prior(십신→MAP_V2) → 9차원 survey 벡터 (person 단위)
  게이트가 열리면 prior가 대체하는 대상이 정확히 survey 차원이므로
  검증 대상과 배포 사용처가 일치한다.

게이트 기준 (pre-registered — 사후 변경 금지, docs/ENGINE_V02_DESIGN.md):
  Stage 1 (n_persons < 200):  탐색 전용. 어떤 가중치도 열지 않음.
  Stage 2 (n_persons >= 200): 차원 d "signal confirmed" ⇔
      |Spearman rho_d| >= 0.20  AND  BH-FDR q_d < 0.05 (9검정)
      AND 순열검정 p_perm < 0.01  AND  시간분할 부호 일치
      → 통과 차원만 w_d = 0.15 (Leo 승인 커밋)
  Stage 3 (n_persons >= 500): Stage 2 판정 이후 신규 데이터만으로
      동일 기준 재확인 시 w_d <= 0.30 (cap)
  시주 의존 차원은 hour_known 부분집합 n으로 별도 충족 필요.

2026-03-12의 교훈: 판정만 남고 분석 스크립트가 증발했다.
이 하네스와 리포트(reports/saju_signal/)는 반드시 git에 커밋한다.

사용법:
  python scripts/validate_saju_signal.py --url https://flavor.arkedia.work
  python scripts/validate_saju_signal.py --db /path/to/saju_submissions.db
"""

import argparse
import json
import math
import os
import random
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DIMENSIONS
from engines.saju_features import extract_features_from_birth, saju_prior_9d, flatten
from engines.recommend import THUMB_VALUE
from scripts.data_io import (
    DUMMY_CUTOFF, fetch_from_admin_api, fetch_from_db,
    dedupe_persons, dataset_hash,
)

HARNESS_VERSION = "1.1"
# v1.1 (2026-07-12, EVIDENCE_AUDIT 완화책 4 — 수집 재개 전 pre-registered 수정안):
#   ① 노출 전 서브셋: person의 시간순 첫 제출 survey(해당 제출이 실제 측정한 차원만)
#      — 이후 제출은 결과 화면에서 선천 성향을 본 뒤라 자기귀인 오염 가능
#   ② 네거티브 컨트롤: nc_* 차원(사주 이론·카피 무연결)에서 CONFIRMED 동등 기준
#      충족 쌍 발생 시 CONTAMINATION_FLAG — 리포트의 모든 CONFIRMED 무효
#   ③ 신봉도 층화: CONFIRMED 차원이 비신봉군에서 |rho|<0.05 또는 부호 불일치면
#      SELF_ATTRIBUTION_SUSPECT — 게이트 개방 보류 (Leo 판단)
#   상세: docs/ENGINE_V02_DESIGN.md §4 수정안

# ── 게이트 기준 상수 (pre-registered) ──
STAGE2_MIN_N = 200
STAGE3_MIN_N = 500
RHO_MIN = 0.20
Q_MAX = 0.05
P_PERM_MAX = 0.01
N_PERMUTATIONS = 10_000
N_BOOTSTRAP = 1_000
SEED = 20260710

GATE_CRITERIA_TEXT = (
    f"Stage 2 (n>={STAGE2_MIN_N}) signal confirmed ⇔ |Spearman rho| >= {RHO_MIN} "
    f"AND BH-FDR q < {Q_MAX} (9검정) AND permutation p < {P_PERM_MAX} "
    f"({N_PERMUTATIONS}회) AND 시간분할 부호 일치. "
    f"Stage 3 (n>={STAGE3_MIN_N}): Stage 2 이후 신규 데이터만으로 재확인 → w<=0.30 cap. "
    "시주 의존 차원은 hour_known 부분집합에서 별도 충족."
)


# ── stdlib 통계 ──

def _ranks(xs):
    """tie 평균 순위"""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    da = [x - ma for x in a]
    db = [x - mb for x in b]
    num = sum(x * y for x, y in zip(da, db))
    den = math.sqrt(sum(x * x for x in da) * sum(y * y for y in db))
    return num / den if den > 0 else 0.0


def spearman(a, b):
    if len(a) < 3:
        return 0.0
    return _pearson(_ranks(a), _ranks(b))


def permutation_p(a, b, observed_rho, n_perm=N_PERMUTATIONS, seed=SEED):
    """|rho_shuffled| >= |observed| 비율 (rank 사전계산으로 고속화)"""
    ra, rb = _ranks(a), _ranks(b)
    rng = random.Random(seed)
    hits = 0
    rb_copy = list(rb)
    for _ in range(n_perm):
        rng.shuffle(rb_copy)
        if abs(_pearson(ra, rb_copy)) >= abs(observed_rho) - 1e-12:
            hits += 1
    return (hits + 1) / (n_perm + 1)  # add-one 보정


def bootstrap_ci(a, b, n_boot=N_BOOTSTRAP, seed=SEED, alpha=0.05):
    rng = random.Random(seed)
    n = len(a)
    stats = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        stats.append(spearman([a[i] for i in idx], [b[i] for i in idx]))
    stats.sort()
    lo = stats[int(n_boot * alpha / 2)]
    hi = stats[min(n_boot - 1, int(n_boot * (1 - alpha / 2)))]
    return round(lo, 3), round(hi, 3)


def bh_fdr(pvals):
    """Benjamini-Hochberg q값"""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    qs = [0.0] * m
    prev = 1.0
    for rank_from_end in range(m, 0, -1):
        i = order[rank_from_end - 1]
        q = min(prev, pvals[i] * m / rank_from_end)
        qs[i] = q
        prev = q
    return qs


def fisher_z_p(r, n):
    """탐색 스크린용 근사 p (Fisher z + 정규근사)"""
    if n < 4 or abs(r) >= 1.0:
        return 1.0
    z = math.atanh(r) * math.sqrt(n - 3)
    return math.erfc(abs(z) / math.sqrt(2))


def binom_two_sided_p(k, n, p=0.5):
    if n == 0:
        return 1.0
    lo = sum(math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(0, k + 1))
    hi = sum(math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))
    return min(1.0, 2 * min(lo, hi))


# ── 분석 본체 ──

def compute_person_features(persons):
    """person별 사주 피처 + prior 계산. 실패 person은 제외."""
    enriched = []
    for p in persons:
        bd = p.get("birth_date") or ""
        if len(bd.split("-")) != 3:
            continue
        try:
            feats = extract_features_from_birth(
                bd, p["birth_time"] if p["hour_known"] else None,
                trust_default_noon=True,  # person 레벨 birth_time은 이미 신뢰 판정 통과분
            )
        except Exception:
            continue
        enriched.append({**p, "features": feats,
                         "prior": saju_prior_9d(feats),
                         "flat": flatten(feats),
                         "_first_dims": first_measured_dims(p)})
    return enriched


def confirmatory(persons, label, survey_key="survey", dim_filter=None):
    """차원별 prior vs survey — 게이트 판정용 9검정.

    survey_key: person dict에서 읽을 설문 벡터 키 ("survey" | "survey_first")
    dim_filter(person, dim): False면 해당 person을 그 차원 검정에서 제외
      (노출 전 서브셋에서 첫 제출이 실제 측정한 차원만 쓰기 위함)
    """
    results = {}
    pvals = []
    for dim in DIMENSIONS:
        sel = [p for p in persons if dim_filter is None or dim_filter(p, dim)]
        xs = [p["prior"][dim] for p in sel]
        ys = [p[survey_key][dim] for p in sel]
        n_dim = len(sel)
        rho = spearman(xs, ys)
        if n_dim >= 10 and len(set(xs)) > 1:
            p_perm = permutation_p(xs, ys, rho)
            ci = bootstrap_ci(xs, ys)
            half = n_dim // 2
            rho_a = spearman(xs[:half], ys[:half])
            rho_b = spearman(xs[half:], ys[half:])
            split_ok = (rho_a * rho_b > 0) and (rho_a * rho > 0)
        else:
            p_perm, ci, split_ok = 1.0, (None, None), False
        results[dim] = {"n": n_dim, "rho": round(rho, 3), "p_perm": round(p_perm, 4),
                        "ci95": ci, "split_sign_consistent": split_ok}
        pvals.append(p_perm)

    qs = bh_fdr(pvals)
    for dim, q in zip(DIMENSIONS, qs):
        r = results[dim]
        r["q"] = round(q, 4)
        if r["n"] < STAGE2_MIN_N:
            r["verdict"] = "insufficient_n"
        elif (abs(r["rho"]) >= RHO_MIN and r["q"] < Q_MAX
              and r["p_perm"] < P_PERM_MAX and r["split_sign_consistent"]):
            r["verdict"] = "CONFIRMED"
        else:
            r["verdict"] = "no_signal"
    return {"label": label, "n": len(persons), "per_dim": results}


def exploratory_screen(persons):
    """개별 사주 피처 × 9차원 전행렬 — 게이트 사용 금지, 가설 개정용"""
    if len(persons) < 10:
        return {"note": "n<10, skipped", "top": []}
    n = len(persons)
    feature_keys = sorted(persons[0]["flat"].keys())
    rows = []
    pvals = []
    for fk in feature_keys:
        xs = [p["flat"][fk] for p in persons]
        if len(set(xs)) < 2:
            continue
        for dim in DIMENSIONS:
            ys = [p["survey"][dim] for p in persons]
            rho = spearman(xs, ys)
            p_approx = fisher_z_p(rho, n)
            rows.append({"feature": fk, "dim": dim, "rho": round(rho, 3),
                         "p_approx": round(p_approx, 4)})
            pvals.append(p_approx)
    qs = bh_fdr(pvals)
    for row, q in zip(rows, qs):
        row["q"] = round(q, 4)
    rows.sort(key=lambda r: -abs(r["rho"]))
    return {"n_tests": len(rows), "top": rows[:25],
            "significant_q05": [r for r in rows if r["q"] < 0.05]}


def first_measured_dims(person) -> set:
    """시간순 첫 제출이 실제 측정한 9차원 부분집합 (노출 전 서브셋용).

    A/B 퀴즈는 raw_answers가 답변 리스트(dimension 필드 보유),
    vol1 27문항은 {"q1":...} dict — 27문항은 9차원 전부 측정.
    포맷 불명 시 전체로 간주 (리셋 후 데이터는 전부 신형 포맷).
    """
    subs = person.get("submissions") or []
    if not subs:
        return set(DIMENSIONS)
    first = min(subs, key=lambda s: s.get("created_at") or "")
    raw = first.get("raw_answers")
    items = raw if isinstance(raw, list) else (
        list(raw.values()) if isinstance(raw, dict) else [])
    dims = {it.get("dimension") for it in items
            if isinstance(it, dict) and not it.get("meta")}
    dims &= set(DIMENSIONS)
    return dims or set(DIMENSIONS)


def negative_control(persons):
    """네거티브 컨트롤 (pre-registered v1.1-②) — 사주 prior → nc_* 차원 상관.

    nc 차원은 사주 이론(MAP_V2)·표시 카피 어디에도 연결되지 않은 취향이므로
    진짜 신호가 있을 수 없다. CONFIRMED 동등 기준을 충족하는 (prior, nc) 쌍이
    하나라도 나오면 방법론/오염 문제 → 리포트 전체 CONTAMINATION_FLAG,
    같은 리포트의 모든 CONFIRMED는 무효 (게이트 개방 금지).
    """
    nc_keys = sorted({k for p in persons for k in (p.get("meta") or {})
                      if k.startswith("nc_")})
    if not nc_keys:
        return {"note": "nc 데이터 없음 (구버전 제출)", "flag": False,
                "n_tests": 0, "flagged": [], "pairs": []}
    rows = []
    skipped = []
    for nc in nc_keys:
        sel = [p for p in persons if nc in (p.get("meta") or {})]
        ys = [p["meta"][nc] for p in sel]
        if len(sel) < 10 or len(set(ys)) < 2:
            skipped.append({"nc": nc, "note": f"n={len(sel)} 부족 또는 무변동"})
            continue
        for dim in DIMENSIONS:
            xs = [p["prior"][dim] for p in sel]
            if len(set(xs)) < 2:
                continue
            rho = spearman(xs, ys)
            p_perm = permutation_p(xs, ys, rho)
            rows.append({"nc": nc, "prior_dim": dim, "n": len(sel),
                         "rho": round(rho, 3), "p_perm": round(p_perm, 4)})
    if rows:
        qs = bh_fdr([r["p_perm"] for r in rows])
        for r, q in zip(rows, qs):
            r["q"] = round(q, 4)
    flagged = [r for r in rows
               if abs(r["rho"]) >= RHO_MIN and r["q"] < Q_MAX
               and r["p_perm"] < P_PERM_MAX]
    return {"n_tests": len(rows), "flag": bool(flagged), "flagged": flagged,
            "skipped": skipped,
            "pairs": sorted(rows, key=lambda r: -abs(r["rho"]))[:10]}


def belief_stratified(persons, conf_primary):
    """신봉도 층화 (pre-registered v1.1-③).

    CONFIRMED 차원의 신호가 신봉군에서만 존재하고 비신봉군에서 부재
    (|rho|<0.05)하거나 부호가 뒤집히면 바넘/자기귀인 의심 —
    해당 차원 SELF_ATTRIBUTION_SUSPECT, 게이트 개방 보류 (Leo 판단).
    """
    withb = [p for p in persons if "meta_belief" in (p.get("meta") or {})]
    hi = [p for p in withb if p["meta"]["meta_belief"] >= 0.5]
    lo = [p for p in withb if p["meta"]["meta_belief"] < 0.5]
    out = {"n_with_belief": len(withb), "n_believer": len(hi), "n_skeptic": len(lo)}
    if min(len(hi), len(lo)) < 20:
        out["note"] = "층화 불가 — 양 군 각 20명 미만"
        out["self_attribution_suspect"] = []
        return out
    out["believer"] = confirmatory(hi, "belief_high")
    out["skeptic"] = confirmatory(lo, "belief_low")
    suspects = []
    for dim, r in (conf_primary.get("per_dim") or {}).items():
        if r.get("verdict") != "CONFIRMED":
            continue
        rlo = out["skeptic"]["per_dim"][dim]
        if abs(rlo["rho"]) < 0.05 or rlo["rho"] * r["rho"] < 0:
            suspects.append(dim)
    out["self_attribution_suspect"] = suspects
    return out


def innate_agreement(persons):
    """보조: 퀴즈 문항의 agreed_with_innate (클라이언트 가설 대비 동의율)"""
    agree, total = 0, 0
    for p in persons:
        for sub in p.get("submissions", []):
            raw = sub.get("raw_answers")
            items = raw if isinstance(raw, list) else (
                list(raw.values()) if isinstance(raw, dict) else [])
            for it in items:
                if isinstance(it, dict) and "agreed_with_innate" in it:
                    total += 1
                    if it["agreed_with_innate"]:
                        agree += 1
    if total == 0:
        return {"n_items": 0, "note": "agreed_with_innate 데이터 없음"}
    rate = agree / total
    return {"n_items": total, "agree_rate": round(rate, 3),
            "binom_p_vs_50": round(binom_two_sided_p(agree, total), 4)}


def feedback_monitoring(submissions, feedbacks):
    """모니터링 전용 (게이트 기준 아님): 도메인별 피드백 가중 점수"""
    stats = {}
    for fb in feedbacks:
        d = fb["domain"]
        s = stats.setdefault(d, {"n": 0, "weighted_sum": 0.0, "hit": 0})
        v = THUMB_VALUE.get(fb["thumb"], 0.0)
        s["n"] += 1
        s["weighted_sum"] += v
        if fb["thumb"] >= 1:
            s["hit"] += 1
    out = {}
    for d, s in sorted(stats.items()):
        out[d] = {"n": s["n"],
                  "hit_rate": round(s["hit"] / s["n"], 3) if s["n"] else None,
                  "mean_weighted": round(s["weighted_sum"] / s["n"], 3) if s["n"] else None}
    return out


# ── 리포트 ──

def _git_sha():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5,
                              cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                              ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def write_report(report, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    stamp = f"{report['date']}_{report['git_commit']}_{report['dataset_hash']}"
    json_path = os.path.join(out_dir, f"{stamp}.json")
    md_path = os.path.join(out_dir, f"{stamp}.md")

    with open(json_path, "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=1)

    lines = [
        f"# 사주 신호 검증 리포트 — {report['date']}",
        "",
        f"- harness v{report['harness_version']} / features {report['saju_feature_version']}"
        f" / git `{report['git_commit']}` / dataset `{report['dataset_hash']}`",
        f"- 필터: since={report['since']} (더미 제외), n_submissions={report['n_submissions']},"
        f" **n_persons={report['n_persons']}** (hour_known={report['n_hour_known']})",
        f"- **판정 stage: {report['gate_stage']}**",
        "",
        "## 게이트 기준 (pre-registered)",
        f"> {GATE_CRITERIA_TEXT}",
        "> 수정안 v1.1 (2026-07-12, 리셋·수집 재개 전 등록): ① 게이트 판정 주 대상 = "
        "노출 전 응답(첫 제출, 실측 차원만) ② nc 컨트롤 유의 시 CONTAMINATION_FLAG "
        "③ 비신봉군 신호 부재 시 SELF_ATTRIBUTION_SUSPECT (개방 보류)",
        "",
        "## Confirmatory — prior → survey (노출 전, 게이트 판정 대상)",
        "",
        "| 차원 | n | rho | 95% CI | p_perm | q(BH) | 분할부호 | 판정 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for dim in DIMENSIONS:
        r = report["confirmatory_first_preexposure"]["per_dim"].get(dim)
        if not r:
            continue
        ci = f"[{r['ci95'][0]}, {r['ci95'][1]}]" if r["ci95"][0] is not None else "—"
        lines.append(f"| {dim} | {r.get('n', '—')} | {r['rho']} | {ci} | {r['p_perm']} "
                     f"| {r['q']} | {'✓' if r['split_sign_consistent'] else '✗'} "
                     f"| {r['verdict']} |")

    nc = report["negative_control"]
    lines += ["", f"## 네거티브 컨트롤 (v1.1-②) — flag: {'⚠️ 발생' if nc.get('flag') else '없음'}"]
    if nc.get("note"):
        lines.append(f"- {nc['note']}")
    for r in nc.get("flagged", []):
        lines.append(f"- ⚠️ {r['prior_dim']} → {r['nc']}: rho={r['rho']} q={r['q']} "
                     f"(있을 수 없는 신호 — 방법론/오염 점검)")

    bl = report["belief_stratified"]
    lines += ["", "## 신봉도 층화 (v1.1-③)",
              f"- 신봉 {bl.get('n_believer', 0)} / 비신봉 {bl.get('n_skeptic', 0)}"
              + (f" — {bl['note']}" if bl.get("note") else ""),
              f"- SELF_ATTRIBUTION_SUSPECT: {bl.get('self_attribution_suspect', [])}"]

    ca = report["confirmatory_all"]
    lines += ["", f"### 참고: 전체 응답 평균 기준 (n={ca['n']} — 노출 후 포함, 게이트 비사용)",
              "", "| 차원 | rho | p_perm | q | 판정 |", "|---|---|---|---|---|"]
    for dim in DIMENSIONS:
        r = ca["per_dim"].get(dim)
        if r:
            lines.append(f"| {dim} | {r['rho']} | {r['p_perm']} | {r['q']} | {r['verdict']} |")

    hk = report.get("confirmatory_hour_known")
    if hk:
        lines += ["", f"### hour_known 부분집합 (n={hk['n']})", "",
                  "| 차원 | rho | p_perm | q | 판정 |", "|---|---|---|---|---|"]
        for dim in DIMENSIONS:
            r = hk["per_dim"][dim]
            lines.append(f"| {dim} | {r['rho']} | {r['p_perm']} | {r['q']} | {r['verdict']} |")

    ex = report["exploratory"]
    lines += ["", f"## Exploratory screen (참고용 — 게이트 사용 금지, {ex.get('n_tests', 0)}검정)",
              "", "| 피처 | 차원 | rho | q |", "|---|---|---|---|"]
    for row in ex.get("top", [])[:15]:
        lines.append(f"| {row['feature']} | {row['dim']} | {row['rho']} | {row['q']} |")

    ia = report["innate_agreement"]
    lines += ["", "## 보조: innate 동의율",
              f"- {json.dumps(ia, ensure_ascii=False)}"]

    lines += ["", "## 모니터링: 도메인별 피드백 (게이트 무관)", "",
              "| 도메인 | n | 적중률(>=👍) | 가중평균 |", "|---|---|---|---|"]
    for d, s in report["feedback_monitoring"].items():
        lines.append(f"| {d} | {s['n']} | {s['hit_rate']} | {s['mean_weighted']} |")

    lines += ["", "## 결론", f"- {report['conclusion']}", ""]

    with open(md_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))

    index_path = os.path.join(out_dir, "index.md")
    entry = (f"- {report['date']} `{report['git_commit']}` `{report['dataset_hash']}` "
             f"n_persons={report['n_persons']} stage={report['gate_stage']} "
             f"confirmed={report['n_confirmed']} → [{stamp}.md]({stamp}.md)\n")
    header = "# 사주 신호 검증 실행 이력\n\n"
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as fp:
            content = fp.read()
    else:
        content = header
    with open(index_path, "w", encoding="utf-8") as fp:
        fp.write(content + entry)

    return json_path, md_path


def main():
    parser = argparse.ArgumentParser(description="사주 신호 검증 하네스")
    parser.add_argument("--db", type=str, help="로컬 SQLite DB 경로")
    parser.add_argument("--url", type=str, default="https://flavor.arkedia.work")
    parser.add_argument("--token", type=str, help="Admin API 토큰 (또는 FLAVOR_ADMIN_TOKEN)")
    parser.add_argument("--since", type=str, default=DUMMY_CUTOFF)
    parser.add_argument("--out-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.dirname(
                            os.path.abspath(__file__))), "reports", "saju_signal"))
    args = parser.parse_args()

    if args.db:
        submissions, feedbacks = fetch_from_db(args.db, since=args.since)
    else:
        submissions, feedbacks = fetch_from_admin_api(args.url, args.token, since=args.since)
    print(f"[*] {len(submissions)} submissions, {len(feedbacks)} feedbacks (since {args.since})")

    persons = compute_person_features(dedupe_persons(submissions))
    hour_persons = [p for p in persons if p["hour_known"]]
    n = len(persons)
    print(f"[*] persons: {n} (hour_known: {len(hour_persons)})")

    conf_all = confirmatory(persons, "all") if n >= 3 else {"label": "all", "n": n, "per_dim": {}}
    conf_hour = confirmatory(hour_persons, "hour_known") if len(hour_persons) >= 10 else None
    # 노출 전 서브셋 (v1.1-①: 게이트 판정의 주 대상) — 첫 제출 survey,
    # 해당 제출이 실제 측정한 차원만
    conf_first = (confirmatory(persons, "first_submission_preexposure",
                               survey_key="survey_first",
                               dim_filter=lambda p, d: d in p["_first_dims"])
                  if n >= 3 else {"label": "first_submission_preexposure",
                                  "n": n, "per_dim": {}})
    nc = negative_control(persons)
    belief = belief_stratified(persons, conf_first)
    exploratory = exploratory_screen(persons)
    ia = innate_agreement(persons)
    fb_mon = feedback_monitoring(submissions, feedbacks)

    if n >= STAGE3_MIN_N:
        stage = "Stage 3 후보 (신규 데이터 분리 재확인 필요)"
    elif n >= STAGE2_MIN_N:
        stage = "Stage 2 (게이트 판정 유효)"
    else:
        stage = f"Stage 1 (탐색 전용, n<{STAGE2_MIN_N} — 가중치 개방 불가)"

    # v1.1-①: 게이트 판정의 주 대상 = 노출 전 서브셋 (conf_all은 참고 지표)
    confirmed = [d for d, r in conf_first.get("per_dim", {}).items()
                 if r.get("verdict") == "CONFIRMED"]
    suspects = belief.get("self_attribution_suspect", [])
    openable = [d for d in confirmed if d not in suspects]
    if n < STAGE2_MIN_N:
        conclusion = (f"n_persons={n} < {STAGE2_MIN_N}: 탐색 단계. 게이트 가중치는 전부 0 유지. "
                      "결과는 가설 개정 참고용으로만 사용.")
    elif nc["flag"]:
        conclusion = (f"⚠️ CONTAMINATION_FLAG: 네거티브 컨트롤 {len(nc['flagged'])}쌍이 "
                      f"CONFIRMED 동등 기준 충족 — 이 리포트의 모든 CONFIRMED 무효 "
                      f"(pre-registered v1.1-②). 원인 규명 전 게이트 개방 금지.")
    elif confirmed:
        parts = [f"게이트 통과 차원(노출 전 기준): {confirmed}."]
        if suspects:
            parts.append(f"단 SELF_ATTRIBUTION_SUSPECT {suspects}는 개방 보류 (v1.1-③).")
        if openable:
            parts.append(f"Leo 승인 후 config/saju_gate.json에서 {openable} w=0.15 개방 가능.")
        conclusion = " ".join(parts)
    else:
        conclusion = "게이트 통과 차원 없음 (노출 전 기준). 가중치 전부 0 유지."

    report = {
        "harness_version": HARNESS_VERSION,
        "saju_feature_version": persons[0]["features"]["schema_version"] if persons else "sf-1",
        "git_commit": _git_sha(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "dataset_hash": dataset_hash(submissions),
        "since": args.since,
        "filters_applied": ["since(더미 제외)", "person dedupe(name,birth_date,gender)",
                            "hour_known 판정(비사주퀴즈 12시 불신)"],
        "n_submissions": len(submissions),
        "n_persons": n,
        "n_hour_known": len(hour_persons),
        "gate_stage": stage,
        "gate_criteria": GATE_CRITERIA_TEXT,
        "confirmatory_first_preexposure": conf_first,
        "confirmatory_all": conf_all,
        "confirmatory_hour_known": conf_hour,
        "negative_control": nc,
        "belief_stratified": belief,
        "exploratory": exploratory,
        "innate_agreement": ia,
        "feedback_monitoring": fb_mon,
        "n_confirmed": len(confirmed),
        "conclusion": conclusion,
    }

    json_path, md_path = write_report(report, args.out_dir)
    print(f"[*] report → {md_path}")
    print(f"[*] {conclusion}")


if __name__ == "__main__":
    main()
