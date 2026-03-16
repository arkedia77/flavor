#!/usr/bin/env python3
"""Leoflavor v0.1 적중률 측정 스크립트

서버 API에서 calibration-data + feedback-data를 가져와
v0.1 엔진(설문 100%)의 추천 적중률을 측정합니다.

사용법:
  python scripts/measure_accuracy.py                    # 서버 API에서 fetch
  python scripts/measure_accuracy.py --db /path/to.db   # 로컬 DB 직접 접근
"""

import argparse
import json
import sys
import os

# flavor 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.domains import run_all_domains
from engines.recommend import centered_cosine
from config import DIMENSIONS


def fetch_from_admin_api(base_url="https://flavor.arkedia.work", token=None):
    """서버 admin export API에서 submissions + feedbacks fetch"""
    import urllib.request

    if not token:
        token = os.environ.get("FLAVOR_ADMIN_TOKEN", "")
    if not token:
        print("[!] FLAVOR_ADMIN_TOKEN 환경변수 또는 --token 필요")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "leoflavor-accuracy/1.0",
    }

    # submissions (profile_json, results_json 포함)
    sub_url = f"{base_url}/api/admin/export?table=submissions&limit=1000"
    print(f"[*] Fetching submissions from {sub_url}")
    req = urllib.request.Request(sub_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        sub_data = json.loads(resp.read())

    submissions = []
    for r in sub_data.get("data", []):
        submissions.append({
            "id": r["id"],
            "birth_date": r.get("birth_date", ""),
            "birth_time": r.get("birth_time", "12"),
            "gender": r.get("gender", ""),
            "elements": json.loads(r["elements_json"]) if r.get("elements_json") else {},
            "raw_answers": json.loads(r["raw_survey_json"]) if r.get("raw_survey_json") else {},
            "survey": json.loads(r["survey_json"]) if r.get("survey_json") else {},
            "profile": json.loads(r["profile_json"]) if r.get("profile_json") else {},
            "results": json.loads(r["results_json"]) if r.get("results_json") else {},
            "profile_version": r.get("profile_version"),
            "created_at": r.get("created_at", ""),
        })

    # feedbacks
    fb_url = f"{base_url}/api/admin/export?table=feedbacks&limit=5000"
    print(f"[*] Fetching feedbacks from {fb_url}")
    req = urllib.request.Request(fb_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        fb_data = json.loads(resp.read())

    feedbacks = fb_data.get("data", [])

    print(f"[*] Loaded {len(submissions)} submissions, {len(feedbacks)} feedbacks")
    return submissions, feedbacks


def fetch_from_db(db_path):
    """로컬 SQLite DB에서 직접 로드"""
    import sqlite3

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # submissions
    c.execute("""
        SELECT id, birth_date, birth_time, gender,
               elements_json, raw_survey_json, survey_json,
               profile_version, created_at, profile_json, results_json
        FROM submissions ORDER BY created_at ASC
    """)
    submissions = []
    for row in c.fetchall():
        submissions.append({
            "id": row[0],
            "birth_date": row[1],
            "birth_time": row[2],
            "gender": row[3],
            "elements": json.loads(row[4]) if row[4] else {},
            "raw_answers": json.loads(row[5]) if row[5] else {},
            "survey": json.loads(row[6]) if row[6] else {},
            "profile_version": row[7],
            "created_at": row[8],
            "profile": json.loads(row[9]) if row[9] else {},
            "results": json.loads(row[10]) if row[10] else {},
        })

    # feedbacks
    c.execute("""
        SELECT submission_id, domain, thumb, created_at
        FROM feedbacks ORDER BY created_at ASC
    """)
    feedbacks = []
    for row in c.fetchall():
        feedbacks.append({
            "submission_id": row[0],
            "domain": row[1],
            "thumb": row[2],
            "created_at": row[3],
        })

    conn.close()

    total = len(submissions)
    print(f"[*] Loaded {total} submissions, {len(feedbacks)} feedbacks from {db_path}")

    return submissions, feedbacks


def measure_accuracy(submissions, feedbacks):
    """적중률 측정

    적중률 = 피드백 중 👍(thumb=1)의 비율
    + 도메인별 상세 분석
    + v0.1 엔진으로 재계산한 추천 vs 저장된 추천 비교
    """
    # 피드백을 submission_id → list로 그룹화
    fb_map = {}
    for fb in feedbacks:
        sid = fb["submission_id"]
        if sid not in fb_map:
            fb_map[sid] = []
        fb_map[sid].append(fb)

    # 전체 적중률
    total_fb = len(feedbacks)
    thumbs_up = sum(1 for fb in feedbacks if fb["thumb"] == 1)
    thumbs_down = total_fb - thumbs_up
    overall_accuracy = thumbs_up / total_fb * 100 if total_fb > 0 else 0

    print(f"\n{'='*50}")
    print(f"  Leoflavor v0.1 적중률 리포트")
    print(f"{'='*50}")
    print(f"  제출 건수: {len(submissions)}")
    print(f"  피드백 총수: {total_fb}")
    print(f"  👍: {thumbs_up}  👎: {thumbs_down}")
    print(f"  전체 적중률: {overall_accuracy:.1f}%")

    # 도메인별 분석
    domain_stats = {}
    for fb in feedbacks:
        d = fb["domain"]
        if d not in domain_stats:
            domain_stats[d] = {"up": 0, "down": 0}
        if fb["thumb"] == 1:
            domain_stats[d]["up"] += 1
        else:
            domain_stats[d]["down"] += 1

    print(f"\n{'─'*50}")
    print(f"  도메인별 적중률")
    print(f"{'─'*50}")
    print(f"  {'도메인':<10} {'👍':>5} {'👎':>5} {'적중률':>8} {'총수':>5}")
    print(f"  {'─'*38}")

    for domain in sorted(domain_stats.keys()):
        s = domain_stats[domain]
        total = s["up"] + s["down"]
        acc = s["up"] / total * 100 if total > 0 else 0
        bar = "█" * int(acc / 5) + "░" * (20 - int(acc / 5))
        print(f"  {domain:<10} {s['up']:>5} {s['down']:>5} {acc:>6.1f}% {total:>5}  {bar}")

    # 유저별 적중률 분포
    user_accs = []
    for sid, fbs in fb_map.items():
        up = sum(1 for f in fbs if f["thumb"] == 1)
        user_accs.append(up / len(fbs) * 100)

    if user_accs:
        avg_user_acc = sum(user_accs) / len(user_accs)
        perfect = sum(1 for a in user_accs if a == 100)
        zero = sum(1 for a in user_accs if a == 0)

        print(f"\n{'─'*50}")
        print(f"  유저별 적중률 분포 (피드백 있는 유저: {len(user_accs)}명)")
        print(f"{'─'*50}")
        print(f"  평균 유저 적중률: {avg_user_acc:.1f}%")
        print(f"  100% 적중 유저: {perfect}명")
        print(f"  0% 적중 유저: {zero}명")

        # 분포 히스토그램
        bins = [0, 25, 50, 75, 100, 101]
        labels = ["0-24%", "25-49%", "50-74%", "75-99%", "100%"]
        for i, label in enumerate(labels):
            count = sum(1 for a in user_accs if bins[i] <= a < bins[i+1])
            bar = "█" * count
            print(f"  {label:>8}: {count:>3}명 {bar}")

    # v0.1 엔진 재계산 비교
    print(f"\n{'─'*50}")
    print(f"  v0.1 엔진 재계산 검증")
    print(f"{'─'*50}")

    recalc_match = 0
    recalc_total = 0
    for sub in submissions:
        survey = sub.get("survey", {})
        if not survey or not any(survey.values()):
            continue
        # v0.1: 설문 = 프로필
        recalc_results = run_all_domains(survey)
        stored_results = sub.get("results", {})

        for domain in recalc_results:
            recalc_total += 1
            if domain in stored_results:
                if recalc_results[domain].get("item") == stored_results[domain].get("item"):
                    recalc_match += 1

    if recalc_total > 0:
        recalc_pct = recalc_match / recalc_total * 100
        print(f"  재계산 일치율: {recalc_pct:.1f}% ({recalc_match}/{recalc_total})")
        if recalc_pct < 100:
            print(f"  ⚠️ 불일치 발생 — 일부 제출이 다른 엔진 버전으로 생성됨")
    else:
        print(f"  (survey 데이터가 없어 재계산 불가)")

    # 프로필 간 유사도 분포 (centered cosine 변별력 검증)
    profiles = [s["survey"] for s in submissions if s.get("survey") and any(s["survey"].values())]
    if len(profiles) >= 2:
        sims = []
        for i in range(len(profiles)):
            for j in range(i+1, len(profiles)):
                sims.append(centered_cosine(profiles[i], profiles[j]))

        avg_sim = sum(sims) / len(sims)
        min_sim = min(sims)
        max_sim = max(sims)
        high_sim = sum(1 for s in sims if s > 0.85) / len(sims) * 100

        print(f"\n{'─'*50}")
        print(f"  프로필 유사도 분포 (centered cosine)")
        print(f"{'─'*50}")
        print(f"  평균: {avg_sim:.3f}  최소: {min_sim:.3f}  최대: {max_sim:.3f}")
        print(f"  0.85 초과 비율: {high_sim:.1f}% (낮을수록 변별력 좋음)")

    print(f"\n{'='*50}")

    return {
        "total_submissions": len(submissions),
        "total_feedbacks": total_fb,
        "overall_accuracy": round(overall_accuracy, 1),
        "domain_stats": domain_stats,
    }


def main():
    parser = argparse.ArgumentParser(description="Leoflavor v0.1 적중률 측정")
    parser.add_argument("--db", type=str, help="로컬 SQLite DB 경로")
    parser.add_argument("--url", type=str, default="https://flavor.arkedia.work",
                        help="서버 API base URL")
    parser.add_argument("--token", type=str, help="Admin API 토큰 (또는 FLAVOR_ADMIN_TOKEN 환경변수)")
    args = parser.parse_args()

    if args.db:
        submissions, feedbacks = fetch_from_db(args.db)
    else:
        try:
            submissions, feedbacks = fetch_from_admin_api(args.url, args.token)
        except Exception as e:
            print(f"[!] API 접근 실패: {e}")
            print(f"    로컬 DB로 실행: python scripts/measure_accuracy.py --db /path/to/saju_submissions.db")
            sys.exit(1)

    measure_accuracy(submissions, feedbacks)


if __name__ == "__main__":
    main()
