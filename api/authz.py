"""관리자 토큰 게이트 — `/api/admin/*`와 **PII를 내보내는 엔드포인트**가 함께 쓴다.

이 모듈이 막는 사고는 하나다: ***유통을 여는 순간 참가자의 `name`·`birth_date`·
`gender`가 무인증 공개 URL로 다운로드된다***(2026-09-24 발견, LEO 「나중에」 → 09-27 집행).

★**fail-closed** — `ADMIN_TOKEN`이 **없으면 전부 403**이다. 열리지 않는다.
  그 사고는 「공격」으로만 오지 않고 「환경변수를 깜박했다」로도 똑같이 온다.
⛔**robots.txt는 이 자리를 못 막는다** — 크롤러에게 하는 부탁이고 접근 제어가 아니다
  (URL을 알면 그냥 열린다). 색인 차단과 인증은 **다른 축**이다.
"""

import hmac
import os
from functools import wraps

from flask import jsonify, request


def _expected():
    """기대 토큰. 미설정이면 빈 문자열 = 게이트가 아무도 통과시키지 않는다."""
    return os.environ.get("ADMIN_TOKEN", "")


def token_ok(allow_query=False):
    """요청이 관리자 토큰을 들고 있나. 토큰 미설정이면 무조건 False(fail-closed).

    허용 위치: `Authorization: Bearer <tok>` · `X-Admin-Token: <tok>`.
    `allow_query=True`면 `?token=<tok>`도 받는다 — 브라우저 **주소창**으로 여는
    관리자 HTML 페이지는 헤더를 붙일 방법이 없기 때문이다.
    ⚠쿼리스트링은 액세스 로그·리퍼러에 남는다 ⇒ **기계용 JSON API에는 열지 않는다.**
    """
    expected = _expected()
    if not expected:
        return False

    given = []
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        given.append(auth[len("Bearer "):])
    hdr = request.headers.get("X-Admin-Token", "")
    if hdr:
        given.append(hdr)
    if allow_query:
        q = request.args.get("token", "")
        if q:
            given.append(q)

    # compare_digest = 비교 시간이 내용에 안 의존 → 한 글자씩 맞춰가는 탐색을 막는다.
    # bytes로 넘긴다 — str 인자는 비ASCII가 섞이면 TypeError를 던진다(토큰에 한글이
    # 들어오면 403이 아니라 500이 됐을 자리).
    e = expected.encode("utf-8")
    return any(hmac.compare_digest(g.encode("utf-8"), e) for g in given)


def require_token(f):
    """JSON API용 게이트. **헤더만** 받는다(쿼리스트링 불가)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not token_ok():
            return jsonify({"status": "error", "message": "Unauthorized"}), 403
        return f(*args, **kwargs)
    return wrapper


def require_token_page(f):
    """브라우저로 여는 관리자 HTML용 게이트. `?token=`도 받는다."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not token_ok(allow_query=True):
            return ("접근 권한이 없습니다.", 403, {
                "Content-Type": "text/plain; charset=utf-8",
                "X-Robots-Tag": "noindex, nofollow",
            })
        return f(*args, **kwargs)
    return wrapper
