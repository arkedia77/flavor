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


def _cmdline(pid):
    """PID의 실행 커맨드라인. 읽을 수 없으면 빈 문자열."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return f.read().replace(b"\0", b" ").decode("utf-8", "replace").strip()
    except OSError:
        pass
    try:
        return subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        return ""


def resolve_gunicorn_master():
    """SIGHUP을 보낼 gunicorn 마스터 PID를 찾는다. (pid, cmdline, error) 반환.

    이 핸들러는 gunicorn 워커 안에서 돌므로 **부모가 곧 마스터**다.
    PID 파일을 읽던 옛 방식은 두 가지로 틀렸다:
      1) 유닛에 --pid가 없으면 파일이 갱신되지 않아 stale PID가 남는다
         (leoserver 실측: 파일=31344(사망), 실제 마스터=1758506 → 리로드가 조용히 무산)
      2) stale PID가 무관한 프로세스에 재활용됐다면 그쪽에 SIGHUP(기본 동작=종료)을 쏜다
    그래서 부모 PID를 쓰되, **커맨드라인으로 gunicorn임을 확인한 뒤에만** 시그널을 보낸다.
    """
    pid = os.getppid()
    if pid <= 1:
        return None, "", f"부모 PID가 {pid} — gunicorn 워커로 실행 중이 아님"
    cmd = _cmdline(pid)
    if "gunicorn" not in cmd:
        return None, cmd, "부모가 gunicorn이 아님 (개발 서버로 실행 중일 수 있음)"
    return pid, cmd, None


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

    # 현재 commit (pull 이후)
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    ).stdout.strip()

    payload = {
        "commit": commit,
        "git_output": result.stdout.strip(),
        "timestamp": datetime.now().isoformat(),
    }

    # gunicorn SIGHUP (graceful reload)
    master_pid, cmd, err = resolve_gunicorn_master()
    if master_pid is None:
        # 리로드 실패는 '조용한 성공'이 되면 안 된다 — pull만 되고 구코드가 계속 도는 상태다.
        payload.update({
            "status": "error",
            "step": "reload",
            "reload": f"failed: {err}",
            "parent_cmdline": cmd,
            "hint": "코드는 pull됐으나 프로세스는 구버전입니다. `sudo systemctl restart flavor`로 마무리하세요.",
        })
        return jsonify(payload), 500

    try:
        os.kill(master_pid, signal.SIGHUP)
    except OSError as e:
        payload.update({
            "status": "error",
            "step": "reload",
            "reload": f"failed: SIGHUP {master_pid}: {e}",
            "hint": "코드는 pull됐으나 프로세스는 구버전입니다. `sudo systemctl restart flavor`로 마무리하세요.",
        })
        return jsonify(payload), 500

    payload.update({"status": "ok", "reload": "ok", "master_pid": master_pid})
    return jsonify(payload)


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
        query = "SELECT id, name, birth_date, birth_time, gender, elements_json, raw_survey_json, survey_json, profile_json, results_json, profile_version, created_at, saju_json FROM submissions"
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
                "profile_json", "results_json", "profile_version", "created_at",
                "saju_json"]
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
