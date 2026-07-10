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
# 유파 조사(reports/theory/SCHOOL_PARAMS_2026-07-10.md) 기반 실제 배점 등가 변형.
# V1/V2는 해당 유파의 궁위+경계를 함께 적용한 "등가", 경계 효과 분리는 경계상향 변형으로.
SENSITIVITY_VARIANTS = {
    "기본(sf-1)": {},
    # 김동완(대덕) 배점제 등가: 천간 각10/년지10/월지30/일지15/시지15, 인성=비겁 등가, 55/45 경계
    "김동완_대덕등가": {
        "palace_weights": {"년간": 1.0, "월간": 1.0, "시간": 1.0,
                           "년지": 1.0, "월지": 3.0, "일지": 1.5, "시지": 1.5},
        "support_inseong": 1.0,
        "strength_neutral": 0.50, "strength_strong": 0.55, "strength_weak": 0.45},
    # 중국 성수법 등가: 월령4성/일지2성/월간1.5성/시간1성/년주1성/시지0.5성, 40~60 평형
    "중국_성수법등가": {
        "palace_weights": {"년간": 0.5, "월간": 1.5, "시간": 1.0,
                           "년지": 0.5, "월지": 4.0, "일지": 2.0, "시지": 0.5},
        "support_inseong": 1.0,
        "strength_neutral": 0.50, "strength_strong": 0.60, "strength_weak": 0.40},
    # 득령·득지·득세 50/30/20 가중 등가
    "득령득지득세_503020": {
        "palace_weights": {"년간": 0.667, "월간": 0.667, "시간": 0.667,
                           "년지": 0.75, "월지": 5.0, "일지": 1.5, "시지": 0.75},
        "strength_neutral": 0.45, "strength_strong": 0.50, "strength_weak": 0.40},
    # 월률분야 일수 근사 지장간 (생지형 [16/7/7일]. 한계: len 기반이라 고지에도 적용됨)
    "월률분야_지장간근사": {
        "hidden_weights_by_len": {1: [1.0], 2: [0.667, 0.333],
                                  3: [0.533, 0.233, 0.233]}},
    # 인성 지지 강도 스윕 (기본 0.8 대비)
    "인성등가(1.0)": {"support_inseong": 1.0, "strength_neutral": 0.40,
                    "strength_strong": 0.46, "strength_weak": 0.34},
    "인성반가(0.5)": {"support_inseong": 0.5, "strength_neutral": 0.30,
                    "strength_strong": 0.36, "strength_weak": 0.24},
    # red flag 검증: 경계만 주류(50% 중심)로 상향, 궁위는 sf-1 유지
    "경계상향_주류50중심": {"strength_neutral": 0.45, "strength_strong": 0.50,
                        "strength_weak": 0.40},
    # 구조 대조군
    "궁성_균등": {"palace_weights": {
        "년간": 1.0, "월간": 1.0, "시간": 1.0,
        "년지": 1.0, "월지": 1.0, "일지": 1.0, "시지": 1.0}},
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


# 별격(외격) 마커 — 억부용신 비적용 영역. 신강약/용신 집계에서 분리
SPECIAL_GYEOKGUK_MARKERS = (
    "종격", "전왕격", "합화격", "양기성상격", "곡직", "염상", "윤하", "가색",
    "종혁", "종강", "종아", "종재", "종관", "종세", "종살",
)


def is_special_structure(entry) -> bool:
    gk = (entry.get("labels") or {}).get("격국") or ""
    return any(m in gk for m in SPECIAL_GYEOKGUK_MARKERS)


def compare_one(entry, features):
    """항목별 일치 여부. 라벨 없는 필드는 None(집계 제외)."""
    labels = entry.get("labels") or {}
    out = {"id": entry["id"], "tier": entry.get("source_tier", "web"),
           "special": is_special_structure(entry)}

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
        # 우리 {용신,희신} 쌍에 정답 용신이 포함되는가 + 정답 {용신,희신들}에
        # 우리 용신이 포함되는가 — 양방향 관대 판정 중 전자를 기본으로
        pair = {features["yongsin"]["element"], features["yongsin"]["희신"]}
        gt_hs = labels.get("희신") or []
        if isinstance(gt_hs, str):
            gt_hs = [p.strip() for p in gt_hs.split("/") if p.strip()]
        out["용신_희신포함"] = (gt_y in pair) or (
            features["yongsin"]["element"] in set([gt_y] + gt_hs))
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


def aggregate(rows, tier=None, special=None):
    """필드별 일치율 (라벨 있는 것만). special: True=별격만, False=억부 적용군만"""
    sel = [r for r in rows if (tier is None or r["tier"] == tier)
           and (special is None or r.get("special") == special)]
    out = {"n": len(sel)}
    for field in ("pillars_match", "신강약", "용신_정확", "용신_희신포함", "격국"):
        vals = [r[field] for r in sel if r.get(field) is not None]
        out[field] = {"n": len(vals),
                      "rate": round(sum(vals) / len(vals), 3) if vals else None}
    return out


def sensitivity_analysis(charts):
    """변형별 (a) 정답지 일치율 — 캘리브레이션의 본체, (b) 기본 대비 뒤집힘 비율"""
    labeled = [c for c in charts if (c.get("labels") or {}).get("신강약") or
               (c.get("labels") or {}).get("용신")]
    universe = labeled if len(labeled) >= 10 else charts  # 라벨 부족하면 전체 명식 사용

    base_preds = {}
    variant_results = {}
    accuracy = {}
    for name, override in SENSITIVITY_VARIANTS.items():
        neutral = (override or {}).get("strength_neutral",
                                       DEFAULT_PARAMS["strength_neutral"])
        preds = {}
        # 정답 일치 집계 (억부 적용군 = 정격만)
        s_hit = s_n = y_hit = y_incl = y_n = 0
        for c in universe:
            try:
                f = compute(c, params=override or None)
            except Exception:
                continue
            pred_label = f["strength"]["label"]
            preds[c["id"]] = {"신강약": pred_label,
                              "score": f["strength"]["score"],
                              "용신": f["yongsin"]["element"]}
            if is_special_structure(c):
                continue  # 별격은 억부 정확도 집계 제외
            labels = c.get("labels") or {}
            gt_s = labels.get("신강약")
            if gt_s in ("신강", "신약"):
                p = pred_label
                if p == "중화":
                    p = "신강" if f["strength"]["score"] >= neutral else "신약"
                s_n += 1
                s_hit += (p == gt_s)
            gt_y = labels.get("용신")
            if gt_y:
                y_n += 1
                y_hit += (f["yongsin"]["element"] == gt_y)
                gt_hs = labels.get("희신") or []
                if isinstance(gt_hs, str):
                    gt_hs = [x.strip() for x in gt_hs.split("/") if x.strip()]
                pair = {f["yongsin"]["element"], f["yongsin"]["희신"]}
                y_incl += (gt_y in pair) or (f["yongsin"]["element"] in set([gt_y] + gt_hs))
        accuracy[name] = {
            "신강약_일치": {"n": s_n, "rate": round(s_hit / s_n, 3) if s_n else None},
            "용신_정확": {"n": y_n, "rate": round(y_hit / y_n, 3) if y_n else None},
            "용신_희신포함": {"n": y_n, "rate": round(y_incl / y_n, 3) if y_n else None},
        }
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
    return {"n_universe": len(universe), "accuracy_by_variant": accuracy, "flips": flips}


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
        # 억부 적용군 = 정격 (게이트 수용 기준의 판정 대상), 별격 = 참고
        "eokbu_applicable": aggregate(rows, special=False),
        "special_structures": aggregate(rows, special=True),
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
