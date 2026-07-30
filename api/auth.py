"""API Blueprint: 카카오 로그인 (선택적 유저 식별)

Leoflavor — localStorage 익명 식별 → 카카오 OAuth 서버 세션(중복제거).
fail-safe: KAKAO_LOGIN_ENABLED=False(키/시크릿 미설정)면 라우트 503·프론트 버튼 숨김 →
           익명 흐름과 완전 항등. 활성화 = env 3종 주입 + 재배포(게이트 철학).

카카오 인가 코드 플로우:
  /auth/kakao/login  → state 발급(CSRF) → kauth authorize 리다이렉트
  /auth/kakao/callback → state 검증 → 코드 교환 → user/me → upsert → 세션 set → next 복귀
  /auth/logout       → 세션 clear
  /api/me            → {enabled, logged_in, nickname} (프론트 상태 표시용)

Kakao HTTP는 stdlib urllib (engines/·requirements 무의존). 네트워크 두 함수는
모듈 레벨로 분리해 테스트에서 주입(monkeypatch) 가능.
"""

import json
import secrets
import urllib.parse
import urllib.request

from flask import Blueprint, request, redirect, session, jsonify

from config import (
    KAKAO_REST_API_KEY, KAKAO_REDIRECT_URI, KAKAO_LOGIN_ENABLED,
)
from db.repository import upsert_user_by_kakao

auth_bp = Blueprint("auth", __name__)

KAKAO_AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USERME_URL = "https://kapi.kakao.com/v2/user/me"


def _safe_next(raw: str) -> str:
    """오픈 리다이렉트 방지: 사이트 내부 상대경로만 허용. 그 외 '/'."""
    if not raw or not raw.startswith("/") or raw.startswith("//"):
        return "/"
    return raw


def _exchange_code_for_token(code: str) -> dict:
    """인가 코드 → 액세스 토큰 (kauth). 테스트에서 monkeypatch."""
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }).encode("utf-8")
    req = urllib.request.Request(
        KAKAO_TOKEN_URL, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_kakao_user(access_token: str) -> dict:
    """액세스 토큰 → 카카오 유저 정보 (kapi). 테스트에서 monkeypatch."""
    req = urllib.request.Request(
        KAKAO_USERME_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


@auth_bp.route("/auth/kakao/login")
def kakao_login():
    if not KAKAO_LOGIN_ENABLED:
        return jsonify({"error": "kakao_login_disabled"}), 503
    state = secrets.token_urlsafe(24)
    session["kakao_oauth_state"] = state
    session["kakao_next"] = _safe_next(request.args.get("next", "/"))
    params = urllib.parse.urlencode({
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "response_type": "code",
        "state": state,
    })
    return redirect(f"{KAKAO_AUTHORIZE_URL}?{params}")


@auth_bp.route("/auth/kakao/callback")
def kakao_callback():
    if not KAKAO_LOGIN_ENABLED:
        return jsonify({"error": "kakao_login_disabled"}), 503

    next_url = _safe_next(session.pop("kakao_next", "/"))
    expected_state = session.pop("kakao_oauth_state", None)

    # 사용자 취소/에러
    if request.args.get("error"):
        return redirect(next_url)

    # CSRF: state 불일치/부재면 거부
    state = request.args.get("state")
    if not expected_state or state != expected_state:
        return jsonify({"error": "invalid_state"}), 400

    code = request.args.get("code")
    if not code:
        return jsonify({"error": "missing_code"}), 400

    try:
        token = _exchange_code_for_token(code)
        access_token = token.get("access_token")
        if not access_token:
            return jsonify({"error": "token_exchange_failed"}), 400
        me = _fetch_kakao_user(access_token)
    except Exception:
        return jsonify({"error": "kakao_api_error"}), 502

    kakao_id = me.get("id")
    if kakao_id is None:
        return jsonify({"error": "no_kakao_id"}), 400
    account = me.get("kakao_account", {}) or {}
    profile = account.get("profile", {}) or {}
    nickname = profile.get("nickname")
    email = account.get("email")

    user_id = upsert_user_by_kakao(kakao_id, nickname, email)
    session["user_id"] = user_id
    session["nickname"] = nickname
    return redirect(next_url)


@auth_bp.route("/auth/logout")
def logout():
    session.clear()
    return redirect(_safe_next(request.args.get("next", "/")))


@auth_bp.route("/api/me")
def me():
    """프론트 로그인 상태 표시용. enabled=False면 프론트는 버튼을 숨긴다(현 UI 항등)."""
    return jsonify({
        "enabled": KAKAO_LOGIN_ENABLED,
        "logged_in": bool(session.get("user_id")),
        "nickname": session.get("nickname"),
    })
