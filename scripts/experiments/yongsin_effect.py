#!/usr/bin/env python3
"""sf-4 후보 설정의 용신 측면 효과 측정 (격국 명칭 외 2차 지표)"""
import json, os, sys

ROOT = os.path.expanduser("~/projects/flavor")
sys.path.insert(0, ROOT)

from scripts.validate_theory import load_golden, compute, is_special_structure

charts = [c for c in load_golden() if (c.get("labels") or {}).get("용신")]
print(f"용신 라벨: {len(charts)}건")

CONFIGS = {
    "sf-3(off)": {"guk_full_blend": 0.0, "guk_half_blend": 0.0,
                  "special_jw_gwan_tugan_block": "off"},
    "guk 0.85/0 block=guk": {"guk_full_blend": 0.85, "guk_half_blend": 0.0,
                             "special_jw_gwan_tugan_block": "guk"},
    "guk 0.85/0 block=off": {"guk_full_blend": 0.85, "guk_half_blend": 0.0,
                             "special_jw_gwan_tugan_block": "off"},
    "guk 0.70/0 block=off": {"guk_full_blend": 0.70, "guk_half_blend": 0.0,
                             "special_jw_gwan_tugan_block": "off"},
}

for name, params in CONFIGS.items():
    agg = {}
    for c in charts:
        f = compute(c, params=params)
        gt_y = c["labels"]["용신"]
        gt_hs = c["labels"].get("희신") or []
        if isinstance(gt_hs, str):
            gt_hs = [x.strip() for x in gt_hs.split("/") if x.strip()]
        pair = {f["yongsin"]["element"], f["yongsin"]["희신"]}
        exact = f["yongsin"]["element"] == gt_y
        incl = (gt_y in pair) or (f["yongsin"]["element"] in set([gt_y] + gt_hs))
        key = "별격" if is_special_structure(c) else "정격"
        for k in ("전체", key):
            a = agg.setdefault(k, [0, 0, 0])
            a[0] += 1; a[1] += exact; a[2] += incl
    line = " / ".join(f"{k} n={a[0]} 정확 {a[1]/a[0]:.3f} ∪희신 {a[2]/a[0]:.3f}"
                      for k, a in agg.items())
    print(f"{name}: {line}")
