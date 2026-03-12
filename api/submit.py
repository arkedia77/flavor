"""API Blueprint: /api/submit, /api/feedback, /api/results, /api/calibration-data, /api/ux-vote

Leoflavor Engine v0.1
- 설문 100% 기반 추천 (사주 blend 제거)
- 사주는 페르소나(캐릭터명)만 생성
- 피드백 학습 루프 준비
"""

import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify

from config import ENGINE_VERSION
from engines.survey import raw_to_survey
from engines.persona import get_persona
from engines.personality import get_personality_type
from engines.recommend import recommend
from db.repository import (
    save_submission, save_feedback, get_recent_submissions,
    get_calibration_data, get_submission_count, check_and_record_milestone,
    save_ux_vote, get_ux_vote_tally, get_ux_vote_comments,
    get_feedback_data,
)

submit_bp = Blueprint('submit', __name__)


def _parse_survey(data: dict) -> dict:
    """요청 데이터에서 9차원 설문 추출"""
    raw_answers   = data.get("raw_answers", {})
    ab_answers    = data.get("ab_answers", [])
    swipe_answers = data.get("swipe_answers", [])

    if raw_answers:
        return raw_to_survey(raw_answers), raw_answers

    if swipe_answers or ab_answers:
        survey_raw = data.get("survey", {})
    else:
        survey_raw = data

    survey = {
        dim: float(survey_raw.get(dim, 0.5))
        for dim in ["social", "aesthetic", "adventurous", "comfort",
                     "budget", "maximalist", "energetic", "urban", "bitter"]
    }
    return survey, raw_answers or swipe_answers or ab_answers


def _parse_birth(data: dict) -> tuple:
    """생년월일 파싱"""
    if data.get("birth_year"):
        return (int(data["birth_year"]), int(data.get("birth_month", 6)),
                int(data.get("birth_day", 15)))

    birth_date = data.get("birth_date", "")
    if birth_date and "-" in birth_date:
        parts = birth_date.split("-")
        return int(parts[0]), int(parts[1]), int(parts[2])

    return 1990, 1, 1


@submit_bp.route("/api/submit", methods=["POST"])
def submit():
    try:
        data = request.get_json(force=True)

        name       = data.get("name", "익명")
        birth_date = data.get("birth_date", "")
        birth_time = data.get("birth_time", "12")
        gender     = data.get("gender", "unknown")
        quiz_type  = data.get("quiz_type", "vol1_taste")

        survey, raw_answers = _parse_survey(data)
        year, month, day = _parse_birth(data)

        # 설문 = 프로필 (사주 blend 없음, 설문 100%)
        profile = survey

        # 추천 (규칙 기반, 추후 피드백 학습 보정)
        results = recommend(profile)

        # 취향 아키타입 (9차원 기반)
        personality = get_personality_type(profile)

        # 사주 페르소나 (마케팅 훅, 추천에 영향 없음)
        persona = get_persona(year, month, day)

        result_id = str(uuid.uuid4())[:8]

        # DB 저장 (elements_json에 persona 저장, 하위호환)
        save_submission(
            result_id, name, birth_date, birth_time, gender,
            {"persona": persona["name"], "element": persona["element"],
             "day_stem": persona["day_stem"]},
            raw_answers,
            survey, profile, results,
            f"{ENGINE_VERSION}_{quiz_type}",
            datetime.now().isoformat()
        )

        total = get_submission_count()
        for m in [50, 200, 500]:
            if total >= m:
                check_and_record_milestone(m)

        return jsonify({
            "status": "ok",
            "id": result_id,
            "name": name,
            "profile": profile,
            "results": results,
            "personality": personality,
            "persona": persona,
        })

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
        "engine_version": ENGINE_VERSION,
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
