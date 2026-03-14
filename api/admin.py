"""Admin API Blueprint: /api/admin/deploy, /api/admin/export"""

import os
import signal
import subprocess
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, request

from db.connection import get_db_connection

admin_bp = Blueprint('admin', __name__)

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
PID_FILE = os.path.join(PROJECT_DIR, "logs", "gunicorn.pid")


def require_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = os.environ.get("ADMIN_TOKEN", "")
        auth = request.headers.get("Authorization", "")
        if not token or auth != f"Bearer {token}":
            return jsonify({"status": "error", "message": "Unauthorized"}), 403
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route("/api/admin/deploy", methods=["POST"])
@require_token
def deploy():
    # git pull
    result = subprocess.run(
        ["git", "pull", "origin", "main"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        return jsonify({
            "status": "error",
            "step": "git pull",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }), 500

    # gunicorn SIGHUP (graceful reload)
    try:
        with open(PID_FILE) as f:
            master_pid = int(f.read().strip())
        os.kill(master_pid, signal.SIGHUP)
        reload_status = "ok"
    except Exception as e:
        reload_status = f"warn: {e}"

    # 현재 commit
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    ).stdout.strip()

    return jsonify({
        "status": "ok",
        "commit": commit,
        "git_output": result.stdout.strip(),
        "reload": reload_status,
        "timestamp": datetime.now().isoformat(),
    })


@admin_bp.route("/api/admin/export", methods=["GET"])
@require_token
def export_data():
    table = request.args.get("table", "submissions")
    limit = request.args.get("limit", type=int)
    since = request.args.get("since")

    if table not in ("submissions", "feedbacks"):
        return jsonify({"status": "error", "message": "table must be submissions or feedbacks"}), 400

    conn = get_db_connection()
    c = conn.cursor()

    if table == "submissions":
        query = "SELECT id, name, birth_date, birth_time, gender, elements_json, raw_survey_json, survey_json, profile_json, results_json, profile_version, created_at FROM submissions"
        params = []
        if since:
            query += " WHERE created_at >= ?"
            params.append(since)
        query += " ORDER BY created_at ASC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        c.execute(query, params)
        cols = ["id", "name", "birth_date", "birth_time", "gender",
                "elements_json", "raw_survey_json", "survey_json",
                "profile_json", "results_json", "profile_version", "created_at"]
    else:
        query = "SELECT submission_id, domain, thumb, created_at FROM feedbacks"
        params = []
        if since:
            query += " WHERE created_at >= ?"
            params.append(since)
        query += " ORDER BY created_at ASC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        c.execute(query, params)
        cols = ["submission_id", "domain", "thumb", "created_at"]

    rows = c.fetchall()
    conn.close()

    data = [dict(zip(cols, row)) for row in rows]
    return jsonify({"status": "ok", "table": table, "count": len(data), "data": data})
