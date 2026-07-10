#!/usr/bin/env python3
"""정답지(golden set) 병합 도구 — 리서치 산출 JSON을 검증 후 data/golden_charts.json에 합침

검증 항목:
- pillars 간지 유효성 (엔진으로 실제 파싱 시도)
- birth만 있는 항목은 날짜 파싱 시도
- labels 값 유효성 (신강약 ∈ {신강,신약,중화}, 용신/희신 ∈ 오행, 격국 형식)
- id 중복 (기존 파일과 신규 배치 내 모두)
- pillars+birth 둘 다 있으면 기둥 재계산 대조 (불일치 시 경고, notes에 기록)

사용법:
  python scripts/merge_golden_charts.py new_charts.json           # 검증만 (dry-run)
  python scripts/merge_golden_charts.py new_charts.json --write   # 병합 저장
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.saju_features import extract_features_from_pillars, extract_features

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN_PATH = os.path.join(ROOT, "data", "golden_charts.json")

VALID_STRENGTH = {"신강", "신약", "중화", None}
VALID_ELEMENT = {"목", "화", "토", "금", "수", None}
VALID_TIER = {"classical", "expert", "web"}


def _parse_birth(birth):
    parts = (birth or "").split()
    date = parts[0]
    y, m, d = (int(x) for x in date.split("-"))
    hour = None
    if len(parts) > 1:
        h = parts[1].replace("시", "")
        if h.isdigit():
            hour = int(h)
    return y, m, d, hour


def validate_entry(entry, seen_ids):
    """(ok: bool, issues: list[str], severity: 'error'|'warn'|None)"""
    issues = []
    eid = entry.get("id", "")
    if not eid:
        return False, ["id 없음"], "error"
    if eid in seen_ids:
        return False, [f"id 중복: {eid}"], "error"

    labels = entry.get("labels") or {}
    if labels.get("신강약") not in VALID_STRENGTH:
        issues.append(f"신강약 값 이상: {labels.get('신강약')!r}")
    if labels.get("용신") not in VALID_ELEMENT:
        issues.append(f"용신 값 이상: {labels.get('용신')!r}")
    # 희신은 복수 가능 ("수/목" 또는 리스트) → 리스트로 정규화
    hs = labels.get("희신")
    if isinstance(hs, str):
        hs = [p.strip() for p in hs.split("/") if p.strip()]
        labels["희신"] = hs or None
    if labels.get("희신") is not None:
        if not all(h in VALID_ELEMENT for h in labels["희신"]):
            issues.append(f"희신 값 이상: {labels['희신']!r}")
    gk = labels.get("격국")
    if gk is not None and not isinstance(gk, str):
        issues.append(f"격국 형식 이상: {gk!r}")
    if entry.get("source_tier") not in VALID_TIER:
        issues.append(f"source_tier 이상: {entry.get('source_tier')!r}")
    if not entry.get("source"):
        issues.append("source 없음")
    if issues:
        return False, issues, "error"

    pillars = entry.get("pillars")
    birth = entry.get("birth")
    if not pillars and not birth:
        return False, ["pillars와 birth 둘 다 없음"], "error"

    # 엔진 파싱 검증
    feats_p = feats_b = None
    if pillars:
        try:
            feats_p = extract_features_from_pillars(pillars)
        except Exception as e:
            return False, [f"pillars 파싱 실패: {e}"], "error"
    if birth:
        try:
            y, m, d, hour = _parse_birth(birth)
            feats_b = extract_features(y, m, d, hour)
        except Exception as e:
            if not pillars:
                return False, [f"birth 파싱 실패: {e}"], "error"
            issues.append(f"birth 파싱 실패(무시, pillars 사용): {e}")

    # 둘 다 있으면 기둥 대조
    if feats_p and feats_b:
        mismatch = {k: (v, feats_b["pillars"].get(k))
                    for k, v in feats_p["pillars"].items()
                    if feats_b["pillars"].get(k) != v}
        if mismatch:
            issues.append(f"기둥 불일치 (출처 간지 vs 날짜 재계산): {mismatch} "
                          "— 출처 오기이거나 야자시/절기 경계. pillars를 정본으로 사용")
            return True, issues, "warn"

    return True, issues, ("warn" if issues else None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="리서치 산출 JSON (배열 또는 {charts: [...]})")
    parser.add_argument("--write", action="store_true", help="검증 통과분 병합 저장")
    parser.add_argument("--golden", default=GOLDEN_PATH)
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as fp:
        incoming = json.load(fp)
    if isinstance(incoming, dict):
        incoming = incoming.get("charts", [])

    with open(args.golden, encoding="utf-8") as fp:
        golden = json.load(fp)
    seen_ids = {c["id"] for c in golden["charts"]}

    accepted, warned, rejected = [], [], []
    for entry in incoming:
        ok, issues, severity = validate_entry(entry, seen_ids)
        if ok:
            if issues:
                entry.setdefault("notes", "")
                entry["notes"] = (entry["notes"] + " | " if entry["notes"] else "") + \
                    "; ".join(issues)
                warned.append((entry["id"], issues))
            accepted.append(entry)
            seen_ids.add(entry["id"])
        else:
            rejected.append((entry.get("id", "?"), issues))

    labeled = [e for e in accepted
               if any((e.get("labels") or {}).get(k) for k in ("신강약", "용신", "격국"))]
    print(f"[*] 입력 {len(incoming)}건 → 수용 {len(accepted)} (경고 {len(warned)}), "
          f"거부 {len(rejected)} / 라벨 있음 {len(labeled)}")
    for eid, issues in rejected:
        print(f"  [거부] {eid}: {'; '.join(issues)}")
    for eid, issues in warned[:10]:
        print(f"  [경고] {eid}: {'; '.join(issues)}")

    if args.write and accepted:
        golden["charts"].extend(accepted)
        tiers = {}
        for c in golden["charts"]:
            tiers[c.get("source_tier", "?")] = tiers.get(c.get("source_tier", "?"), 0) + 1
        golden["_status"] = (f"총 {len(golden['charts'])}건 (tier: {tiers}) — "
                             f"마지막 병합 {os.path.basename(args.input)}")
        with open(args.golden, "w", encoding="utf-8") as fp:
            json.dump(golden, fp, ensure_ascii=False, indent=1)
        print(f"[*] 저장: {args.golden} (총 {len(golden['charts'])}건)")
    elif accepted:
        print("[*] dry-run — 저장하려면 --write")


if __name__ == "__main__":
    main()
