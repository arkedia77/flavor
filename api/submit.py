"""API Blueprint: /api/submit, /api/feedback, /api/results, /api/calibration-data, /api/ux-vote

Leoflavor Engine v0.2 — 검증 게이트 방식
- 추천 = 설문 기반 + 사주 prior의 게이트 블렌드 (게이트 가중치 전부 0 = 설문 100%)
- 사주 피처는 서버에서 계산·저장 (saju_json), 검증 하네스가 신호 확인 전까지 추천 무영향
- 피드백 학습 경로 배선 (confidence/feedback_signal 주석 — 추천 아이템은 불변)
"""

import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify

from config import ENGINE_VERSION, SAJU_GATE
from engines.survey import raw_to_survey
from engines.persona import get_persona
from engines.personality import get_personality_type
from engines.recommend import recommend
from engines.saju_features import (
    extract_features_from_birth, saju_prior_9d, SCHEMA_VERSION as SAJU_SCHEMA_VERSION,
)
from engines.gated_blend import apply_gated_blend, any_weight_open
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

        # 사주 피처 계산 (실패해도 제출은 성공 — profile=survey 폴백)
        # 사주 트랙 퀴즈만 birth_time=12를 실제 선택으로 신뢰
        saju_record = None
        prior = None
        hour_known = False
        try:
            is_saju_quiz = quiz_type.endswith("_saju")
            features = extract_features_from_birth(
                f"{year:04d}-{month:02d}-{day:02d}", birth_time,
                trust_default_noon=is_saju_quiz,
            )
            hour_known = features["input"]["hour_known"]
            prior = saju_prior_9d(features)
            saju_record = {
                "feature_version": SAJU_SCHEMA_VERSION,
                "hour_known": hour_known,
                "features": features,
                "prior_9d": prior,
            }
        except Exception:
            pass

        # 게이트 블렌드 (가중치 전부 0이면 profile == survey 정확 일치)
        profile, applied_w = apply_gated_blend(survey, prior, SAJU_GATE, hour_known)
        if saju_record is not None:
            saju_record["gate"] = {
                "gate_version": SAJU_GATE.get("gate_version"),
                "applied_weights": applied_w,
            }

        # 추천 (규칙 기반 + 유사 유저 피드백 보정 — 아이템은 규칙 결과 그대로)
        try:
            all_profiles = get_feedback_data()
        except Exception:
            all_profiles = None
        results = recommend(profile, all_profiles)

        # 취향 아키타입 (9차원 기반)
        personality = get_personality_type(profile)

        # 사주 페르소나 (마케팅 훅, 추천에 영향 없음)
        persona = get_persona(year, month, day)

        result_id = str(uuid.uuid4())[:8]

        # 게이트가 열려 블렌드된 행만 profile_version에 표시 (옛 파싱 무영향)
        profile_version = f"{ENGINE_VERSION}_{quiz_type}"
        if any_weight_open(applied_w):
            profile_version += f"_g{SAJU_GATE.get('gate_version')}"

        # DB 저장 (elements_json에 persona 저장, 하위호환 / saju_json에 피처 벡터)
        save_submission(
            result_id, name, birth_date, birth_time, gender,
            {"persona": persona["name"], "element": persona["element"],
             "day_stem": persona["day_stem"]},
            raw_answers,
            survey, profile, results,
            profile_version,
            datetime.now().isoformat(),
            saju=saju_record,
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
        if not submission_id or not domain or thumb not in (2, 1, -1, -2):
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
