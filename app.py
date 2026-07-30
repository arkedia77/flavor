"""
SAJU 취향 분석 서비스 - Flask 백엔드
flavor.arkedia.work
"""

import os
import sys

# 프로젝트 루트를 sys.path에 추가 (모듈 임포트용)
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from flask import Flask

from config import FLASK_SECRET_KEY
from db.connection import init_db
from api.public import public
from api.submit import submit_bp
from api.admin import admin_bp
from api.auth import auth_bp


def create_app():
    app = Flask(__name__)

    # 세션 시크릿: 카카오 로그인 활성화 시 반드시 env로 고정값 주입(다중 워커·재시작 간 동일).
    # 미설정(로그인 OFF) 시 세션은 쓰이지 않으므로 고정 폴백 상수로 둔다.
    app.secret_key = FLASK_SECRET_KEY or "flavor-login-disabled-no-session-secret"

    init_db()

    app.register_blueprint(public)
    app.register_blueprint(submit_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("DEBUG", "false").lower() == "true",
            host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
