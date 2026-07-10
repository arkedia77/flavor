#!/usr/bin/env python3
"""명리 이론 검증 하네스 — 정답지(golden set) 대조 + 민감도 분석

목적: 취향 데이터와 무관하게, 사주 피처 엔진의 해석층(신강약/용신/격국)이
전문가 판정과 얼마나 일치하는지 측정한다. Leo 지시(2026-07-10):
"실데이터 수집 재시작 전에 이론·가설 완전 검증".

검증 대상 층위:
  L0 만세력/기둥 계산  — lunar 검증 완료 (앵커 테스트). 여기선 pillars 재확인만
  L1 신강약/용신/격국  — 이 하네스의 주 대상 (정답지 일치율)
  L2 MAP_V2 십신→취향  — 이 하네스 범위 밖 (문헌 근거 + 실데이터 게이트로 검증)

수용 기준 (pre-registered, 2026-07-10):
  - 신강약 방향 일치율 (중화 제외 양자 판정): classical tier에서 >= 80%
  - 용신: 정확 일치 >= 60%, 용신∪희신 포함 일치 >= 80% (classical tier)
  - 격국: 명칭 일치 >= 70% (자평진전 tier)
  - 민감도: 주력 파라미터 변형에서 신강약 판정 뒤집힘 비율 <= 15%
    (결론이 파라미터 선택에 강건해야 "이론의 신호"라 말할 수 있음)

사용법:
  python scripts/validate_theory.py                # data/golden_charts.json
  python scripts/validate_theory.py --sensitivity  # 파라미터 변형 비교 포함
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.saju_features import (
    extract_features, extract_features_from_pillars, DEFAULT_PARAMS,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN_PATH = os.path.join(ROOT, "data", "golden_charts.json")
REPORT_DIR = os.path.join(ROOT, "reports", "theory")

# 수용 기준 (pre-registered)
ACCEPT = {
    "신강약_방향_classical": 0.80,
    "용신_정확_classical": 0.60,
    "용신_희신포함_classical": 0.80,
    "격국_classical": 0.70,
    "민감도_신강약_뒤집힘_max": 0.15,
}

# ── 민감도 분석 변형 ──
# 리서치(유파 기준 조사) 완료 후 실제 유파 배점으로 교체/보강 예정.
# 현재는 구조적 변형 4종: 결론이 우리 임의 선택값에 얼마나 민감한지 1차 확인용.
SENSITIVITY_VARIANTS = {
    "기본(sf-1)": {},
    "궁성_균등": {"palace_weights": {
        "년간": 1.0, "월간": 1.0, "시간": 1.0,
        "년지": 1.0, "월지": 1.0, "일지": 1.0, "시지": 1.0}},
    "월지_강조약화(1.8)": {"palace_weights": {
        "년간": 1.0, "월간": 1.2, "시간": 1.0,
        "년지": 1.0, "월지": 1.8, "일지": 1.5, "시지": 1.0}},
    "월지_강조강화(3.2)": {"palace_weights": {
        "년간": 1.0, "월간": 1.2, "시간": 1.0,
        "년지": 1.0, "월지": 3.2, "일지": 1.5, "시지": 1.0}},
    "인성지지_동등(1.0)": {"support_inseong": 1.0, "strength_neutral": 0.40,
                        "strength_strong": 0.46, "strength_weak": 0.34},
}


def load_golden(path=GOLDEN_PATH):
    with open(path, encoding="utf-8") as fp:
        data = json.load(fp)
    return data["charts"]


def compute(chart_entry, params=None):
    """정답지 항목 → 엔진 피처. pillars 우선, 없으면 birth."""
    if chart_entry.get("pillars"):
        return extract_features_from_pillars(chart_entry["pillars"], params=params)
    birth = chart_entry.get("birth", "")
    parts = birth.split()
    date = parts[0]
    hour = None
    if len(parts) > 1:
        h = parts[1].replace("시", "")
        if h.isdigit():
            hour = int(h)
    y, m, d = (int(x) for x in date.split("-"))
    return extract_features(y, m, d, hour, params=params)


def compare_one(entry, features):
    """항목별 일치 여부. 라벨 없는 필드는 None(집계 제외)."""
    labels = entry.get("labels") or {}
    out = {"id": entry["id"], "tier": entry.get("source_tier", "web")}

    # 기둥 재확인 (출처 간지 vs 엔진 재계산 — birth가 있고 pillars도 있을 때만 의미)
    if entry.get("pillars") and entry.get("birth"):
        try:
            from_date = compute({"birth": entry["birth"]})
            out["pillars_match"] = all(
                from_date["pillars"].get(k) == v for k, v in entry["pillars"].items())
        except Exception:
            out["pillars_match"] = None
    else:
        out["pillars_match"] = None

    gt = labels.get("신강약")
    if gt in ("신강", "신약"):
        pred = features["strength"]["label"]
        # 방향 판정: 중화 예측은 score 부호로 양자화
        if pred == "중화":
            pred = "신강" if features["strength"]["score"] >= DEFAULT_PARAMS["strength_neutral"] else "신약"
        out["신강약"] = (pred == gt)
        out["신강약_pred"] = features["strength"]["label"]
        out["신강약_score"] = features["strength"]["score"]
    else:
        out["신강약"] = None

    gt_y = labels.get("용신")
    if gt_y:
        out["용신_정확"] = (features["yongsin"]["element"] == gt_y)
        pair = {features["yongsin"]["element"], features["yongsin"]["희신"]}
        out["용신_희신포함"] = gt_y in pair
        out["용신_pred"] = features["yongsin"]["element"]
    else:
        out["용신_정확"] = None
        out["용신_희신포함"] = None

    gt_g = labels.get("격국")
    if gt_g:
        norm = lambda s: s.replace("격", "").strip()
        out["격국"] = (norm(features["gyeokguk"]["name"]) == norm(gt_g))
        out["격국_pred"] = features["gyeokguk"]["name"]
    else:
        out["격국"] = None

    return out


def aggregate(rows, tier=None):
    """필드별 일치율 (라벨 있는 것만)"""
    sel = [r for r in rows if tier is None or r["tier"] == tier]
    out = {"n": len(sel)}
    for field in ("pillars_match", "신강약", "용신_정확", "용신_희신포함", "격국"):
        vals = [r[field] for r in sel if r.get(field) is not None]
        out[field] = {"n": len(vals),
                      "rate": round(sum(vals) / len(vals), 3) if vals else None}
    return out


def sensitivity_analysis(charts):
    """변형별 신강약/용신 판정 + 기본 대비 뒤집힘 비율"""
    labeled = [c for c in charts if (c.get("labels") or {}).get("신강약") or
               (c.get("labels") or {}).get("용신")]
    universe = labeled if len(labeled) >= 10 else charts  # 라벨 부족하면 전체 명식 사용

    base_preds = {}
    variant_results = {}
    for name, override in SENSITIVITY_VARIANTS.items():
        preds = {}
        for c in universe:
            try:
                f = compute(c, params=override or None)
            except Exception:
                continue
            preds[c["id"]] = {"신강약": f["strength"]["label"],
                              "score": f["strength"]["score"],
                              "용신": f["yongsin"]["element"]}
        if name == "기본(sf-1)":
            base_preds = preds
        variant_results[name] = preds

    flips = {}
    for name, preds in variant_results.items():
        if name == "기본(sf-1)":
            continue
        common = [cid for cid in preds if cid in base_preds]
        if not common:
            continue
        s_flip = sum(preds[c]["신강약"] != base_preds[c]["신강약"] for c in common)
        y_flip = sum(preds[c]["용신"] != base_preds[c]["용신"] for c in common)
        flips[name] = {"n": len(common),
                       "신강약_뒤집힘": round(s_flip / len(common), 3),
                       "용신_뒤집힘": round(y_flip / len(common), 3)}
    return {"n_universe": len(universe), "flips": flips}


def _git_sha():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5,
                              cwd=ROOT).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description="명리 이론 검증 (정답지 대조)")
    parser.add_argument("--golden", default=GOLDEN_PATH)
    parser.add_argument("--sensitivity", action="store_true")
    parser.add_argument("--out-dir", default=REPORT_DIR)
    args = parser.parse_args()

    charts = load_golden(args.golden)
    labeled = [c for c in charts
               if any((c.get("labels") or {}).get(k) for k in ("신강약", "용신", "격국"))]
    print(f"[*] golden set: {len(charts)} charts ({len(labeled)} labeled)")

    rows = []
    errors = []
    for c in charts:
        try:
            f = compute(c)
            rows.append(compare_one(c, f))
        except Exception as e:
            errors.append({"id": c["id"], "error": str(e)})

    report = {
        "harness": "validate_theory/1.0",
        "git_commit": _git_sha(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "n_charts": len(charts), "n_labeled": len(labeled), "n_errors": len(errors),
        "accept_criteria": ACCEPT,
        "overall": aggregate(rows),
        "by_tier": {t: aggregate(rows, t) for t in ("classical", "expert", "web")},
        "disagreements": [r for r in rows
                          if any(r.get(k) is False
                                 for k in ("신강약", "용신_희신포함", "격국", "pillars_match"))],
        "errors": errors,
    }
    if args.sensitivity:
        report["sensitivity"] = sensitivity_analysis(charts)

    os.makedirs(args.out_dir, exist_ok=True)
    stamp = f"{report['date']}_{report['git_commit']}"
    out_json = os.path.join(args.out_dir, f"{stamp}.json")
    with open(out_json, "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=1)

    print(json.dumps({"overall": report["overall"],
                      "by_tier": report["by_tier"],
                      **({"sensitivity": report["sensitivity"]} if args.sensitivity else {})},
                     ensure_ascii=False, indent=1))
    print(f"[*] report → {out_json}")
    if len(labeled) < 20:
        print(f"[!] 라벨된 명식 {len(labeled)}개 — 판정에는 최소 20개+ 필요 (수집 진행 중)")


if __name__ == "__main__":
    main()
