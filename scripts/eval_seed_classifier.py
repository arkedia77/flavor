#!/usr/bin/env python3
"""seed 분류기 오프라인 평가 — 커피 seed 자연어 → 극(black/sweet/neutral) 정확도.

방금 배선한 LLM 우도 경로(scripts/llm_claude)와 현행 키워드 휴리스틱의 품질을
**실데이터 이전에** 대표 seed 라벨셋으로 검증한다(Leo 우선순위: 이론·측정 공고히).
seed 우도는 콜드스타트 lift의 핵심 레버이므로, 잘못 매핑하면 lift가 죽는다.

축 a = '우유·단맛 유무'(black=진한 블랙 / sweet=부드러운 스위트). 산미·핸드드립 등
축 b 어휘는 **의도적으로 축 a에서 중립**(_ACIDITY_RESERVED, 현재 우도 미사용) — 라벨도 neutral.

사용법:
  python scripts/eval_seed_classifier.py                 # 키워드 휴리스틱(크레덴셜 불필요)
  python scripts/eval_seed_classifier.py --llm           # Claude 추론(anthropic+자격증명 필요)
  python scripts/eval_seed_classifier.py --llm --llm-model claude-haiku-4-5
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.coldstart import _keyword_likelihood

# 대표 seed 라벨셋 (축 a). neutral = 축 a 정보 거의 없음(무정보 또는 축 b 전용 어휘).
# 라벨은 '이 seed가 축 a에서 어느 극을 가리켜야 하는가'의 정답지.
LABELED = [
    # 진한 블랙형
    ("아메리카노 없으면 못 살아", "black"),
    ("에스프레소만 마셔요", "black"),
    ("진한 블랙 커피 좋아함", "black"),
    ("콜드브루 즐겨 마심", "black"),
    ("아메리카노 진하게 두 샷", "black"),
    ("다크로스트 원두 선호", "black"),
    ("룽고 한 잔", "black"),
    # 부드러운 스위트형
    ("바닐라라떼 최고", "sweet"),
    ("카페라떼에 시럽 추가", "sweet"),
    ("달달한 커피가 좋아", "sweet"),
    ("카라멜 마키아토 자주 마심", "sweet"),
    ("오트밀크 라떼", "sweet"),
    ("연하고 달콤한 라떼", "sweet"),
    ("플랫화이트 부드러운 거", "sweet"),
    # 무정보 / 중립
    ("커피 잘 몰라요", "neutral"),
    ("그냥 아무거나 주세요", "neutral"),
    ("카페인만 있으면 됩니다", "neutral"),
    ("따뜻한 거 아무거나", "neutral"),
    # 축 b 전용 어휘 → 축 a에서는 중립이어야 정답 (산미는 우유·단맛 축과 직교)
    ("산미 있는 핸드드립 좋아함", "neutral"),
    ("라이트로스트 게이샤 원두", "neutral"),
]

# 어휘 밖(OOV) 하드셋 — 키워드 패밀리 단어를 **일부러 피한** 자연어. 키워드 휴리스틱은
# 대부분 중립으로 흘리므로(recall↓), LLM 경로의 존재 이유를 정확히 드러낸다.
# 실유저 seed는 이 분포에 가까움("우유 없이", "달게" 등 자유표현).
LABELED_OOV = [
    ("우유 없이 쓴맛으로 주세요", "black"),
    ("쓴 거 좋아해요", "black"),
    ("설탕 팍팍 넣어서", "sweet"),
    ("생크림 잔뜩 올린 거", "sweet"),
    ("부드럽고 안 쓴 걸로", "sweet"),
    ("우유 많이 넣은 커피", "sweet"),
    ("믹스커피처럼 달게", "sweet"),
    ("쓰지 않고 목 넘김 부드러운 거", "sweet"),
]

_MARGIN = 1.15  # L 비가 이 이상이면 방향 확정, 아니면 neutral


def pole_from_likelihood(lb: float, ls: float) -> str:
    if lb >= ls * _MARGIN:
        return "black"
    if ls >= lb * _MARGIN:
        return "sweet"
    return "neutral"


def keyword_infer(seed: str):
    lb, ls = _keyword_likelihood(seed)
    return {"black": lb, "sweet": ls}


def evaluate(infer, labeled=LABELED) -> dict:
    """infer: seed -> {'black','sweet'}. 반환: 정확도 + 항목별 + 극별 집계."""
    rows, correct = [], 0
    by_pole = {}  # expected -> [n, hit]
    for seed, expected in labeled:
        lk = infer(seed)
        pred = pole_from_likelihood(lk["black"], lk["sweet"])
        hit = pred == expected
        correct += hit
        by_pole.setdefault(expected, [0, 0])
        by_pole[expected][0] += 1
        by_pole[expected][1] += hit
        rows.append({"seed": seed, "expected": expected, "pred": pred,
                     "hit": hit, "L": (round(lk["black"], 3), round(lk["sweet"], 3))})
    n = len(labeled)
    return {
        "n": n, "correct": correct, "accuracy": round(correct / n, 4) if n else None,
        "by_pole": {k: {"n": v[0], "hit": v[1],
                        "recall": round(v[1] / v[0], 3) if v[0] else None}
                    for k, v in by_pole.items()},
        "rows": rows,
    }


def print_report(result: dict, mode: str):
    print(f"[seed 분류기 평가 — {mode}]  정확도 {result['accuracy']} "
          f"({result['correct']}/{result['n']})")
    for pole, s in result["by_pole"].items():
        print(f"  {pole:8s} recall {s['recall']}  ({s['hit']}/{s['n']})")
    misses = [r for r in result["rows"] if not r["hit"]]
    if misses:
        print("  오분류:")
        for r in misses:
            print(f"    '{r['seed']}' → {r['pred']} (기대 {r['expected']}, L={r['L']})")


def main():
    ap = argparse.ArgumentParser(description="seed 분류기 오프라인 평가 (커피 축 a)")
    ap.add_argument("--llm", action="store_true",
                    help="Claude 추론으로 평가(anthropic+자격증명 필요). 기본=키워드 휴리스틱")
    ap.add_argument("--llm-model", type=str, default=None)
    args = ap.parse_args()

    if args.llm:
        from engines.coldstart import build_llm_infer
        from scripts.llm_claude import build_claude_complete_fn, DEFAULT_LLM_MODEL
        model = args.llm_model or DEFAULT_LLM_MODEL
        infer = build_llm_infer(build_claude_complete_fn(model=model))
        mode = f"Claude({model})"
    else:
        infer = keyword_infer
        mode = "키워드 휴리스틱"

    print_report(evaluate(infer, LABELED), f"{mode} · 어휘 내(in-vocab)")
    print()
    print_report(evaluate(infer, LABELED_OOV), f"{mode} · 어휘 밖(OOV 자연어)")
    print("\n[i] OOV에서 키워드 정확도가 낮으면 = 실유저 자유표현을 놓친다는 뜻. "
          "--llm 으로 같은 셋을 돌려 Claude가 이를 얼마나 회복하는지 비교하라.")


if __name__ == "__main__":
    main()
