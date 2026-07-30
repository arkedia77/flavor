# 카카오 로그인 활성화 가이드

**대상**: Leo (앱 등록·env 결정) + admin (env 주입·재배포)
**작성**: 2026-07-30 / **배선 커밋**: 4648dd1
**현 상태**: 코드 배선 100% 완료, **크레덴셜 미주입 = 로그인 완전 OFF**(익명 흐름과 항등)

> 사주·학습·콜드스타트 게이트와 같은 철학입니다 — **배선은 끝났고, 켜는 건 크레덴셜과
> 승인의 문제**. 아래 3스텝을 밟으면 켜지고, 되돌리려면 env 하나만 지우면 됩니다.

---

## 왜 켜는가 (한 줄)

localStorage 익명 식별로는 같은 사람인지 알 수 없어 **n_persons(고유 인원)를 신뢰할 수 없습니다.**
Stage 2 사주 게이트 판정(n≥200)도, 콜드스타트 lift 측정도 전부 "몇 명인가"에 걸려 있습니다.
카카오 = **신원/중복제거 전용**. 사주에 필요한 출생'시'는 카카오가 안 주므로 생년월일 입력은
앱 안에 그대로 둡니다(= 동의범위 최소 = 심사 마찰 최소).

---

## STEP 1 — Kakao Developers 앱 등록 (Leo, 10분)

https://developers.kakao.com → 로그인 → **내 애플리케이션 → 애플리케이션 추가하기**

### 1-1. 앱 생성
| 항목 | 입력값 |
|------|--------|
| 앱 이름 | `Leoflavor` (또는 원하는 이름 — 동의 화면에 노출됨) |
| 사업자명 | 개인이면 본인 이름 |
| 카테고리 | 라이프스타일 등 적당히 |

### 1-2. 플랫폼 등록
**앱 설정 → 플랫폼 → Web 플랫폼 등록**

```
사이트 도메인: https://flavor.arkedia.work
```

### 1-3. 카카오 로그인 활성화 + Redirect URI ★가장 중요
**제품 설정 → 카카오 로그인 → 활성화 설정 ON**

같은 화면 아래 **Redirect URI 등록**:

```
https://flavor.arkedia.work/auth/kakao/callback
```

> ⚠️ **한 글자라도 다르면 `KOE006` 에러**가 납니다. 끝에 슬래시 없음, https, 소문자.
> 이 값은 아래 STEP 2의 `KAKAO_REDIRECT_URI`와 **완전히 동일해야** 합니다.

### 1-4. 동의항목
**제품 설정 → 카카오 로그인 → 동의항목**

| 항목 | 설정 | 이유 |
|------|------|------|
| 닉네임 (`profile_nickname`) | **필수 동의** | 로그인 표시("○○님 로그인됨")에만 사용 |
| 프로필 사진 | 설정 안 함 | 안 씀 |
| 카카오계정(이메일) | **설정 안 함**(권장) | 코드는 있으면 저장하지만 없어도 무방. 이메일은 비즈앱 심사 대상이라 마찰만 늘어남 |

> 코드상 이메일은 `account.get("email")` → 없으면 그냥 `None` 저장. **동의 안 받아도 동작합니다.**

### 1-5. REST API 키 복사
**앱 설정 → 앱 키 → `REST API 키`** (JavaScript 키 아님 ⚠️)

이 값이 STEP 2의 `KAKAO_REST_API_KEY`입니다.

> `client_secret`은 **쓰지 않습니다**(코드가 안 보냄). 카카오에서 client_secret을 "사용함"으로
> 켜면 토큰 교환이 실패하니 **끄기(기본값)로 두세요.**

---

## STEP 2 — leoserver env 3종 주입 (admin 발주)

leoserver `~/apps/flavor` systemd 서비스에 아래 3개를 주입합니다.

```bash
KAKAO_REST_API_KEY=<STEP 1-5에서 복사한 REST API 키>
KAKAO_REDIRECT_URI=https://flavor.arkedia.work/auth/kakao/callback
FLASK_SECRET_KEY=<아래 명령으로 1회 생성한 고정 랜덤 값>
```

`FLASK_SECRET_KEY` 생성 (한 번만, 그 뒤로 **절대 바꾸지 않음**):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

> ⚠️ **`FLASK_SECRET_KEY`는 반드시 고정값**이어야 합니다. gunicorn이 워커 2개로 도는데
> 워커마다 시크릿이 다르면 세션 쿠키를 서로 못 읽어 **로그인이 무작위로 풀립니다.**
> 재시작할 때마다 바뀌어도 마찬가지(전원 로그아웃). 그래서 코드는 `os.urandom` 폴백을
> 일부러 안 씁니다 — 시크릿이 없으면 그냥 로그인을 끕니다(`config.py:126`).

> 🔒 값 3종은 **git 리포·agent-comm 메시지에 적지 않습니다.** admin에게는 "주입해달라"만
> 발주하고, 값은 Leo가 별도 경로로 전달합니다.

### 주입 방식
기존 `DB_PATH` 주입과 동일하게 systemd unit의 `Environment=` 또는 `EnvironmentFile=`.
`.env` 파일도 동작합니다(`app.py:13`이 `load_dotenv`) — 다만 퍼미션 600 권장.

---

## STEP 3 — 재배포

```bash
cd ~/apps/flavor && git pull origin main && sudo systemctl restart flavor
```

> **선행조건**: 현재 leoserver 배포본이 7/23 클론이라 카카오 코드 자체가 아직 없습니다.
> 이 `git pull`은 STEP 1·2와 무관하게 **먼저** 해두는 편이 좋습니다(키 없으면 OFF = 항등).
> → 2026-07-30 admin에 선발주함 (`admin_flavor_20260730_232145_...`).

---

## 검증 체크리스트

| # | 확인 | 기대 | 실패 시 |
|---|------|------|---------|
| 1 | `curl -s https://flavor.arkedia.work/api/me` | `{"enabled":true,"logged_in":false,"nickname":null}` | `404` = 코드 미배포(STEP 3) / `enabled:false` = env 미주입 또는 시크릿 누락(STEP 2) |
| 2 | `https://flavor.arkedia.work/` 브라우저 접속 | 상단에 **노란 "🗨️ 카카오로 로그인하고 기록 저장" 버튼** | 버튼 없으면 `enabled:false` |
| 3 | 버튼 클릭 | 카카오 동의 화면 → 동의 → **허브로 복귀** + "○○님 로그인됨" | `KOE006` = Redirect URI 불일치(STEP 1-3) |
| 4 | 로그인 상태로 퀴즈 1개 완료 | 정상 결과 페이지 | — |
| 5 | DB 확인 | `submissions.user_id`가 NULL 아님 + `users`에 행 1건 | — |
| 6 | 다른 브라우저에서 같은 카카오로 로그인 후 제출 | `users` 행이 **늘지 않고** 같은 `user_id` 재사용 | dedup 실패 = kakao_id UNIQUE 확인 |
| 7 | 로그아웃 → 익명으로 제출 | 정상 동작, `user_id`는 NULL | — |

DB 확인 쿼리 (leoserver):
```bash
sqlite3 /home/leo/apps/flavor/var/saju_submissions.db \
  "SELECT id, nickname, created_at FROM users; \
   SELECT count(*) AS with_user FROM submissions WHERE user_id IS NOT NULL;"
```

---

## 롤백 (30초)

`KAKAO_REST_API_KEY` env를 **지우고 재시작**하면 끝입니다.
→ `KAKAO_LOGIN_ENABLED=False` → 라우트 503, 프론트 버튼 숨김, 제출 `user_id=NULL`
→ **익명 흐름과 완전 항등.** 이미 쌓인 `users` 행과 `user_id`는 남지만 아무도 안 읽습니다.

코드 롤백까지 원하면 이전 커밋 체크아웃. `submissions.user_id` 컬럼은 남지만
구버전 코드가 참조하지 않으므로 무해합니다(additive 마이그레이션).

---

## 알려진 제약 / 나중 결정거리

| 항목 | 현재 | 비고 |
|------|------|------|
| 출생시 | 카카오 미제공 → 앱 내 입력 유지 | 사주 트랙은 지금처럼 시주 직접 입력 |
| 기존 익명 데이터 병합 | **안 함** | 로그인 이전 localStorage 제출분은 익명으로 남음. 어차피 유통 재개 전 DB 리셋 예정이라 실익 없음 |
| 이메일 | 동의 안 받음 | 나중에 알림/리텐션이 필요해지면 그때 동의항목 추가(재심사 없음) |
| 세션 만료 | Flask 기본(브라우저 세션 쿠키) | 필요 시 `PERMANENT_SESSION_LIFETIME`으로 영속화 — 유통 데이터 보고 결정 |
| 쿠키 플래그 | HttpOnly + SameSite=Lax + Secure(운영만) | `app.py:33-38`, 2026-07-30 추가 |
| 카카오 비즈앱 | 불필요 | 닉네임만 받으면 일반 앱으로 충분 |

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `config.py:111-126` | env 3종 로드 + `KAKAO_LOGIN_ENABLED` fail-safe 판정 |
| `api/auth.py` | `/auth/kakao/login`·`/callback`·`/auth/logout`·`/api/me` (stdlib urllib) |
| `db/connection.py:30-49` | `submissions.user_id` additive 마이그레이션 + `users` 테이블 |
| `db/repository.py` | `upsert_user_by_kakao()` (kakao_id UNIQUE = dedup 안정키) |
| `api/submit.py` | 세션 `user_id`를 제출에 부착 (익명이면 None = 항등) |
| `quizzes/hub/hub.html:662`, `hub_saju.html:532` | `/api/me` 조회 → `enabled`일 때만 버튼 노출 |
| `tests/test_kakao_auth.py` | OFF 항등 / upsert 멱등 / 콜백 전과정 / state CSRF / 오픈리다이렉트 / 쿠키 플래그 |
