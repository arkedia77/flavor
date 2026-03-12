"""API Blueprint: /api/submit, /api/feedback, /api/results, /api/calibration-data, /api/ux-vote"""

import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify

from config import PROFILE_VERSION, CALIBRATION_THRESHOLDS, AGENT_COMM
from engines.saju import calc_saju
from engines.vector import saju_to_innate_vector
from engines.survey import raw_to_survey
from engines.blend import elements_to_profile, blend_profile
from engines.personality import get_personality_type
from engines.domains import run_all_domains
from engines.gap import innate_to_expected_profile, compute_gap, interpret_gap
from db.repository import (
    save_submission, save_feedback, get_recent_submissions,
    get_calibration_data, get_submission_count, check_and_record_milestone,
    save_ux_vote, get_ux_vote_tally, get_ux_vote_comments,
)

submit_bp = Blueprint('submit', __name__)


def _notify_milestone(milestone: int, total: int):
    """임계점 도달 시 flavor/tasks/에 JSON push"""
    try:
        import subprocess

        tasks_dir = os.path.join(AGENT_COMM, "flavor", "tasks")
        if not os.path.isdir(tasks_dir):
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"{ts}_flavor_reklvm_calibration_milestone_{milestone}.json"
        payload = {
            "id": f"{ts}_flavor_reklvm_calibration_milestone_{milestone}",
            "from": "flavor",
            "to": "reklvm",
            "project": "flavor",
            "task": "calibration_alert",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "message": f"설문 {milestone}명 도달! 레이어1-4 캘리브레이션 분석 요청",
            "payload": {
                "total_submissions": total,
                "milestone": milestone,
                "note": CALIBRATION_THRESHOLDS.get(milestone, ""),
                "data_endpoint": "/api/calibration-data",
            }
        }
        fpath = os.path.join(tasks_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        subprocess.run(
            ["git", "-C", AGENT_COMM, "add", f"flavor/tasks/{fname}"],
            capture_output=True
        )
        subprocess.run(
            ["git", "-C", AGENT_COMM, "commit", "-m",
             f"alert: flavor→reklvm 설문 {milestone}명 도달, 캘리브레이션 요청"],
            capture_output=True
        )
        subprocess.run(
            ["git", "-C", AGENT_COMM, "push", "origin", "main"],
            capture_output=True
        )
    except Exception as e:
        import logging
        logging.warning(f"milestone notify failed: {e}")


@submit_bp.route("/api/submit", methods=["POST"])
def submit():
    try:
        data = request.get_json(force=True)

        name       = data.get("name", "익명")
        birth_date = data.get("birth_date", "")
        birth_time = data.get("birth_time", "12")
        gender     = data.get("gender", "unknown")

        quiz_type   = data.get("quiz_type", "vol1_taste")

        raw_answers   = data.get("raw_answers", {})
        ab_answers    = data.get("ab_answers", [])
        swipe_answers = data.get("swipe_answers", [])

        if raw_answers:
            survey = raw_to_survey(raw_answers)
        elif swipe_answers or ab_answers:
            survey_raw = data.get("survey", {})
            survey = {
                "social":      float(survey_raw.get("social", 0.5)),
                "aesthetic":   float(survey_raw.get("aesthetic", 0.5)),
                "adventurous": float(survey_raw.get("adventurous", 0.5)),
                "comfort":     float(survey_raw.get("comfort", 0.5)),
                "budget":      float(survey_raw.get("budget", 0.5)),
                "maximalist":  float(survey_raw.get("maximalist", 0.5)),
                "energetic":   float(survey_raw.get("energetic", 0.5)),
                "urban":       float(survey_raw.get("urban", 0.5)),
                "bitter":      float(survey_raw.get("bitter", 0.5)),
            }
        else:
            survey = {
                "social":      float(data.get("social", 0.5)),
                "aesthetic":   float(data.get("aesthetic", 0.5)),
                "adventurous": float(data.get("adventurous", 0.5)),
                "comfort":     float(data.get("comfort", 0.5)),
                "budget":      float(data.get("budget", 0.5)),
                "maximalist":  float(data.get("maximalist", 0.5)),
                "energetic":   float(data.get("energetic", 0.5)),
                "urban":       float(data.get("urban", 0.5)),
                "bitter":      float(data.get("bitter", 0.5)),
            }

        if data.get("birth_year"):
            year  = int(data.get("birth_year", 1995))
            month = int(data.get("birth_month", 6))
            day   = int(data.get("birth_day", 15))
            hour  = int(data.get("birth_hour", 12))
        else:
            parts = birth_date.split("-")
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            hour = int(birth_time)

        saju = calc_saju(year, month, day, hour)
        saju_detail = saju.get("saju_detail")

        # Phase 2: 12D innate vector 기반 블렌딩 (saju_detail 있을 때)
        if saju_detail:
            innate_vec = saju_to_innate_vector(saju_detail)
            profile = blend_profile(innate_vec, survey)
            expected = innate_to_expected_profile(innate_vec)
            gap_result = compute_gap(expected, survey)
            gap_interp = interpret_gap(gap_result)
        else:
            # fallback: 기존 방식
            profile = elements_to_profile(saju["elements"], gender, survey)
            innate_vec = None
            gap_result = None
            gap_interp = None

        results = run_all_domains(profile)
        personality = get_personality_type(profile, saju_detail)

        result_id = str(uuid.uuid4())[:8]

        save_submission(
            result_id, name, birth_date, birth_time, gender,
            saju["elements"],
            raw_answers or swipe_answers or ab_answers,
            survey, profile, results,
            f"{PROFILE_VERSION}_{quiz_type}",
            datetime.now().isoformat()
        )

        total = get_submission_count()
        milestone_hit = None
        for m in [50, 200, 500]:
            if total >= m and check_and_record_milestone(m):
                milestone_hit = m

        if milestone_hit:
            _notify_milestone(milestone_hit, total)

        response = {
            "status": "ok",
            "id": result_id,
            "name": name,
            "profile": profile,
            "results": results,
            "personality": personality,
        }

        # Phase 2 확장 필드 (있을 때만)
        if saju_detail:
            response["saju_detail"] = {
                "day_master": saju_detail["day_master"],
                "geokguk": saju_detail["geokguk"],
                "strength": saju_detail["strength"],
                "strength_label": saju_detail["strength_label"],
                "type_code": saju_detail["type_code"],
                "yin_yang_ratio": saju_detail["yin_yang_ratio"],
            }
            response["innate_vector"] = innate_vec
            response["gap"] = gap_interp

        return jsonify(response)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@submit_bp.route("/api/feedback", methods=["POST"])
def feedback():
    try:
        data = request.get_json(force=True)
        submission_id = data.get("submission_id", "")
        domain        = data.get("domain", "")
        thumb         = int(data.get("thumb", 0))
        if not submission_id or not domain or thumb not in (1, -1):
            return jsonify({"status": "error", "message": "invalid params"}), 400
        save_feedback(submission_id, domain, thumb, datetime.now().isoformat())
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@submit_bp.route("/api/results")
def api_results():
    rows = get_recent_submissions()
    return jsonify([{
        "id": r[0], "name": r[1], "birth_date": r[2],
        "gender": r[3], "created_at": r[4]
    } for r in rows])


@submit_bp.route("/api/calibration-data")
def calibration_data():
    rows, total = get_calibration_data()
    return jsonify({
        "total": total,
        "profile_version": PROFILE_VERSION,
        "calibration_thresholds": CALIBRATION_THRESHOLDS,
        "next_threshold": next((m for m in [50, 200, 500] if m > total), None),
        "data": [{
            "id": r[0],
            "birth_date": r[1],
            "birth_time": r[2],
            "gender": r[3],
            "elements": json.loads(r[4]) if r[4] else {},
            "raw_answers": json.loads(r[5]) if r[5] else {},
            "survey": json.loads(r[6]) if r[6] else {},
            "profile_version": r[7],
            "created_at": r[8],
        } for r in rows]
    })


@submit_bp.route("/api/ux-vote", methods=["POST"])
def ux_vote():
    try:
        data = request.get_json(force=True)
        preferred = data.get("preferred", "")
        comment   = data.get("comment", "")
        done_set  = data.get("done_set", [])
        source    = data.get("source", "")

        save_ux_vote(preferred, comment, json.dumps(done_set), source, datetime.now().isoformat())
        tally = get_ux_vote_tally()
        return jsonify({"ok": True, "tally": tally})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@submit_bp.route("/api/ux-vote/tally", methods=["GET"])
def ux_vote_tally():
    try:
        tally = get_ux_vote_tally()
        comments = get_ux_vote_comments()
        return jsonify({"tally": tally, "comments": comments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
