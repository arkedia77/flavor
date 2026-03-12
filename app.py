"""
SAJU 취향 분석 서비스 - Flask 백엔드
flavor.arkedia.work
"""

import os
import sys

# 프로젝트 루트를 sys.path에 추가 (모듈 임포트용)
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask

from db.connection import init_db
from api.public import public
from api.submit import submit_bp


def create_app():
    app = Flask(__name__)

    init_db()

    app.register_blueprint(public)
    app.register_blueprint(submit_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("DEBUG", "false").lower() == "true",
            host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
