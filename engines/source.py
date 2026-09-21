"""유입 출처 파싱 — 어느 채널이 데려왔는가 (2026-09-21, LEO 승인)

★소급 불가: **안 물으면 영원히 없다.** 유통이 시작된 뒤엔 그 기간의 출처를 사후에 알 수
없다(8/14에 「비랜덤 노출은 소급 불가라 리셋 순간부터 켜야 한다」고 판단한 것과 같은 성질).
그래서 유입 개시 «전에» 켠다.

★프론트 무변경 설계: `/api/submit`은 **같은 오리진 XHR**이라 브라우저가 `Referer`에 퀴즈
페이지 URL을 **쿼리스트링째** 싣는다(same-origin은 full URL 전송). ⇒ 유저가
`/cafe-saju?utm_source=x`로 들어오면 서버가 그 utm을 그대로 읽는다. 퀴즈 HTML 40여 파일을
안 건드리고 전 라우트에 즉시 적용된다.
⚠**한계**: 이건 「우리 링크에 붙은 태그」만 본다. 브라우저가 «우리 사이트에 오기 전» 어디서
왔는지(`document.referrer`)는 서버가 못 본다 — 그건 프론트가 실어 보내야 하고, 필요해지면
`extra`로 확장한다(이 함수는 그 자리를 이미 비워 뒀다).

★수집 최소주의(의도적): utm 5종 + 랜딩 경로만 저장한다. ⛔**IP·User-Agent·raw URL은 저장하지
않는다** — 이 DB엔 이미 이름·생년월일시가 들어 있어 식별자를 더 붙일 이유가 없고, raw URL은
utm 외의 파라미터까지 딸려 들어온다. 「필요해서 켰다」와 「있으니 담았다」는 다르다.

Flask 무의존(순수 Python) — 표준 라이브러리만 쓴다.
"""

from urllib.parse import urlsplit, parse_qs

# 저장 대상 키. ⛔화이트리스트다 — 목록에 없는 쿼리 파라미터는 버린다.
UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")

_MAX_VALUE = 120   # 값 1개 상한(쓰레기·주입 방어)
_MAX_PATH = 200


def _clean(v):
    """앞뒤 공백 제거 + 길이 상한. 빈 값은 None."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    return s[:_MAX_VALUE]


def parse_source(referrer_url=None, extra=None) -> dict:
    """(퀴즈 페이지 URL, 추가 필드) → 출처 dict. 아무것도 없으면 **빈 dict**.

    referrer_url: `/api/submit` 요청의 `Referer` 헤더(같은 오리진이라 쿼리 포함).
    extra: 프론트가 나중에 실어 보낼 값을 위한 확장구(예: {"ref_host": "..."}).
           ⛔화이트리스트 밖 키는 버린다.

    반환: `{"utm_source": ..., "landing_path": ...}` 형태. ★**빈 dict면 호출 측이
    컬럼을 NULL로 둬야 한다** — 그래야 기존 행·직접 유입과 완전히 항등이다.
    """
    out = {}

    if referrer_url:
        try:
            parts = urlsplit(str(referrer_url))
            qs = parse_qs(parts.query or "", keep_blank_values=False)
            for k in UTM_KEYS:
                v = _clean((qs.get(k) or [None])[0])
                if v:
                    out[k] = v
            # 랜딩 경로는 utm이 하나라도 있을 때만 의미가 있다(어느 퀴즈로 들어왔나).
            # ⛔경로만 담는다 — 호스트·쿼리 전문은 안 담는다.
            if out:
                path = _clean(parts.path)
                if path:
                    out["landing_path"] = path[:_MAX_PATH]
        except Exception:
            # 출처 파싱 실패가 제출을 막으면 안 된다 — fail-safe로 조용히 비운다.
            return {}

    if isinstance(extra, dict):
        for k in ("ref_host",):
            v = _clean(extra.get(k))
            if v:
                out[k] = v

    return out
