#!/usr/bin/env python3
"""sf-4 국(局) blend 계수 그리드서치 + 홀짝 교차평가"""
import itertools, json, os, sys

ROOT = os.path.expanduser("~/projects/flavor")
sys.path.insert(0, ROOT)

from scripts.validate_theory import load_golden, compute, is_special_structure

charts = [c for c in load_golden() if (c.get("labels") or {}).get("격국")]
print(f"격국 라벨: {len(charts)}건")

def norm(s):
    return s.replace("격", "").strip()

def evaluate(subset, params):
    tot = hit = n_sp = hit_sp = n_nm = hit_nm = n_jp = hit_jp = 0
    for c in subset:
        f = compute(c, params=params or None)
        ok = norm(f["gyeokguk"]["name"]) == norm(c["labels"]["격국"])
        sp = is_special_structure(c)
        tot += 1; hit += ok
        if sp: n_sp += 1; hit_sp += ok
        else: n_nm += 1; hit_nm += ok
        if "자평진전" in (c.get("source") or "") or c.get("source_book") == "자평진전":
            n_jp += 1; hit_jp += ok
    return {"all": hit / tot, "special": hit_sp / n_sp if n_sp else None,
            "normal": hit_nm / n_nm if n_nm else None,
            "japyeong": hit_jp / n_jp if n_jp else None,
            "n": (tot, n_sp, n_nm, n_jp)}

GRID = {
    "guk_full_blend": [0.5, 0.7, 0.85, 1.0],
    "guk_half_blend": [0.0, 0.15, 0.3, 0.5],
    "special_jw_gwan_tugan_block": ["guk", "off"],
}

keys = list(GRID)
results = []
for combo in itertools.product(*(GRID[k] for k in keys)):
    params = dict(zip(keys, combo))
    r = evaluate(charts, params)
    results.append((params, r))

results.sort(key=lambda x: -x[1]["all"])
print("\n=== 전체 그리드 상위 10 (전체 정확도순) ===")
for p, r in results[:10]:
    jp = f" 자평 {r['japyeong']:.2f}" if r["japyeong"] is not None else ""
    print(f"full={p['guk_full_blend']:.2f} half={p['guk_half_blend']:.2f} "
          f"block={p['special_jw_gwan_tugan_block']} → "
          f"전체 {r['all']:.3f} 별격 {r['special']:.3f} 정격 {r['normal']:.3f}{jp}")

print("\n베이스라인 sf-3 (국 미적용 = full 0, half 0):")
r0 = evaluate(charts, {"guk_full_blend": 0.0, "guk_half_blend": 0.0,
                       "special_jw_gwan_tugan_block": "off"})
jp0 = f" 자평 {r0['japyeong']:.2f}" if r0["japyeong"] is not None else ""
print(f"  전체 {r0['all']:.3f} 별격 {r0['special']:.3f} 정격 {r0['normal']:.3f}{jp0} n={r0['n']}")

# 홀짝 교차평가: 홀수 인덱스에서 최적 → 짝수에서 평가, 반대도
odd = charts[0::2]
even = charts[1::2]

def best_on(subset):
    best, bp = -1, None
    for combo in itertools.product(*(GRID[k] for k in keys)):
        params = dict(zip(keys, combo))
        r = evaluate(subset, params)
        if r["all"] > best:
            best, bp = r["all"], params
    return bp, best

bp_odd, s_odd = best_on(odd)
bp_even, s_even = best_on(even)
print(f"\n홀수셋 최적 {bp_odd} (인샘플 {s_odd:.3f}) → 짝수셋 평가: {evaluate(even, bp_odd)['all']:.3f}")
print(f"짝수셋 최적 {bp_even} (인샘플 {s_even:.3f}) → 홀수셋 평가: {evaluate(odd, bp_even)['all']:.3f}")
print(f"교차 기준 베이스라인: 짝수 {evaluate(even, {'guk_full_blend':0,'guk_half_blend':0})['all']:.3f} / "
      f"홀수 {evaluate(odd, {'guk_full_blend':0,'guk_half_blend':0})['all']:.3f}")
