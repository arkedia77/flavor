#!/usr/bin/env python3
"""콜드스타트 예측 lift 하네스 — 파일럿 A (커피 쓴맛형/산미형)

목적: 코호트+seed 예측(engines/coldstart)이 base rate보다 취향을 잘 맞히는지,
자체 라벨 데이터 없이 **저장된 피드백만으로** 측정한다.

부분관측 문제(유저는 아이템 1개만 봄) 하에서 정직한 지표:
  concordance lift = P(👍 | 보여준 아이템 타입 == 예측 타입)
                   − P(👍 | 보여준 아이템 타입 != 예측 타입)
  예측이 실제 선호를 추적하면, 예측과 '일치하는' 아이템이 더 높은 👍를 받는다.
  base rate = 전체 👍율. lift>0 = 예측이 base rate 위에 신호를 얹음.

예측은 저장된 birth_date·gender에서 결정적으로 재계산하므로 예측을 미리 로깅할
필요가 없다(옛 행도 소급 측정 가능). seed 자연어는 아직 수집 전이라 코호트-only.

사용법:
  python scripts/measure_coldstart_lift.py --db /path/to.db
  python scripts/measure_coldstart_lift.py --self-test   # 합성 자가검증
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.coldstart import predict_coffee_type, coffee_item_type
from engines.recommend import THUMB_VALUE  # noqa: F401 (thumb 해석 일관성 참조)

COFFEE_DOMAIN = "커피"


def compute_lift(records: list) -> dict:
    """records: [{age, gender, seeds?, shown_type('black'|'sweet'), positive(bool)}]

    shown_type이 black/sweet이 아닌 것(mixed/unknown)은 제외.
    """
    match_pos = match_n = mis_pos = mis_n = pos_total = 0
    used = 0
    for r in records:
        shown = r.get("shown_type")
        if shown not in ("black", "sweet"):
            continue
        pred = predict_coffee_type(r.get("age"), r.get("gender"),
                                   r.get("seeds"))["type"]
        pos = 1 if r.get("positive") else 0
        used += 1
        pos_total += pos
        if shown == pred:
            match_n += 1
            match_pos += pos
        else:
            mis_n += 1
            mis_pos += pos

    p_match = match_pos / match_n if match_n else None
    p_mis = mis_pos / mis_n if mis_n else None
    base = pos_total / used if used else None
    lift = (p_match - p_mis) if (p_match is not None and p_mis is not None) else None
    return {
        "n_used": used, "base_rate_pos": _r(base),
        "n_match": match_n, "p_pos_match": _r(p_match),
        "n_mismatch": mis_n, "p_pos_mismatch": _r(p_mis),
        "concordance_lift": _r(lift),
    }


def _r(v):
    return round(v, 4) if isinstance(v, float) else v


def records_from_stored(submissions: list, feedbacks: list, reference_year: int,
                        arm: str = "all") -> list:
    """저장된 submissions + 커피 피드백 → 예측 lift 측정용 레코드 재구성.

    arm: 'random'=랜덤 노출만(무교란 추정), 'rule'=규칙 노출만, 'all'=전부.
    노출 arm 태그(results[커피]._arm)는 랜덤 arm 게이트가 켜진 뒤 제출분에만 있다.
    태그 없는 옛 행은 'rule'로 간주(규칙 노출).
    seed는 results._coldstart.seeds에서 읽어 예측에 반영(있을 때만).
    """
    by_id = {s["id"]: s for s in submissions}
    records = []
    for fb in feedbacks:
        if fb.get("domain") != COFFEE_DOMAIN:
            continue
        sub = by_id.get(fb.get("submission_id"))
        if not sub:
            continue
        bd = (sub.get("birth_date") or "").split("-")
        if len(bd) != 3 or not bd[0].isdigit():
            continue
        age = reference_year - int(bd[0])
        results = sub.get("results") or {}
        coffee = results.get(COFFEE_DOMAIN) or {}
        shown_item = coffee.get("item")
        if not shown_item:
            continue
        rec_arm = coffee.get("_arm") or "rule"  # 태그 없으면 규칙 노출
        if arm != "all" and rec_arm != arm:
            continue
        seeds = (results.get("_coldstart") or {}).get("seeds") or None
        records.append({
            "age": age, "gender": sub.get("gender"), "seeds": seeds,
            "shown_type": coffee_item_type(shown_item),
            "positive": int(fb.get("thumb", 0)) >= 1,
            "arm": rec_arm,
        })
    return records


# ── 합성 자가검증 (하네스 정합성 + 신호 감지력 확인) ──

def _synthetic_records(n, signal: bool, seed=20260712):
    """signal=True면 실제 선호가 코호트 방향과 상관, False면 무상관(null)."""
    rng = random.Random(seed)
    from engines.coldstart import cohort_black_prior
    recs = []
    for _ in range(n):
        age = rng.randint(18, 80)
        gender = rng.choice(["male", "female"])
        # 잠재 블랙 선호 확률
        if signal:
            p_like_black = cohort_black_prior(age, gender)  # 코호트와 상관
        else:
            p_like_black = 0.5  # 무상관
        likes_black = rng.random() < p_like_black
        shown_type = rng.choice(["black", "sweet"])
        # 보여준 타입이 그의 실제 선호와 맞으면 👍 확률↑
        pos = rng.random() < (0.75 if (shown_type == "black") == likes_black else 0.30)
        recs.append({"age": age, "gender": gender,
                     "shown_type": shown_type, "positive": pos})
    return recs


def self_test():
    sig = compute_lift(_synthetic_records(4000, signal=True))
    null = compute_lift(_synthetic_records(4000, signal=False))
    print("[self-test] 신호 있음:", json.dumps(sig, ensure_ascii=False))
    print("[self-test] null    :", json.dumps(null, ensure_ascii=False))
    ok = (sig["concordance_lift"] is not None and sig["concordance_lift"] > 0.08
          and abs(null["concordance_lift"]) < 0.06)
    print("[self-test]", "PASS" if ok else "FAIL",
          "— 신호 lift>0.08 ∧ null≈0 기대")
    return ok


def main():
    ap = argparse.ArgumentParser(description="콜드스타트 lift 하네스 (커피)")
    ap.add_argument("--db", type=str, help="로컬 SQLite DB")
    ap.add_argument("--url", type=str, default="https://flavor.arkedia.work")
    ap.add_argument("--token", type=str)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--reference-year", type=int, default=datetime.now().year)
    ap.add_argument("--arm", choices=["random", "rule", "all"], default="all",
                    help="노출 arm 필터. 무교란 lift 추정=random (랜덤 arm 게이트 개방 후)")
    args = ap.parse_args()

    if args.self_test or not (args.db or os.environ.get("FLAVOR_ADMIN_TOKEN") or args.token):
        ok = self_test()
        if args.self_test:
            sys.exit(0 if ok else 1)
        if not args.db:
            print("[i] 실데이터 소스 미지정 — 자가검증만 실행. --db 또는 --token으로 실측정.")
            return

    from scripts.data_io import fetch_from_admin_api, fetch_from_db
    if args.db:
        submissions, feedbacks = fetch_from_db(args.db, since=None)
    else:
        submissions, feedbacks = fetch_from_admin_api(args.url, args.token, since=None)

    records = records_from_stored(submissions, feedbacks, args.reference_year, arm=args.arm)
    result = compute_lift(records)
    n_random = sum(1 for r in records_from_stored(submissions, feedbacks, args.reference_year, arm="random"))
    print(json.dumps({"reference_year": args.reference_year, "arm": args.arm,
                      "n_coffee_feedback": sum(1 for f in feedbacks if f.get("domain") == COFFEE_DOMAIN),
                      "n_random_arm": n_random,
                      **result}, ensure_ascii=False, indent=1))
    if args.arm != "random":
        print("[i] arm=all/rule은 비랜덤 노출이라 셀렉션 바이어스로 교란될 수 있음 — "
              "무교란 추정은 --arm random (랜덤 arm 게이트 개방 후).")
    if result["n_used"] < 30:
        print(f"[!] 유효 레코드 {result['n_used']}개 — lift 신뢰엔 수십+ 필요 (수집 진행 중)")


if __name__ == "__main__":
    main()
