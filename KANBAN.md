# Leoflavor KANBAN

**최종 수정**: 2026-08-20
**엔진**: Leoflavor v0.2 (사주 검증 게이트, 피처 sf-3 — sf-4 국 감지는 검증 후 미채택)

---

## 🔄 IN PROGRESS

| 항목 | 우선순위 | 담당 | 비고 |
|------|---------|------|------|
| 커피 자아 리빌 비주얼 다듬기 | Low | **LEO 결정** | 카피/톤 결정 2건은 8/13 완료(DONE 참조). 남은 여지 = **리빌 카드 비주얼**(색·레이아웃)뿐. 개방 전 언제든 |

> **Leo 결정 (7/10)**: 실데이터 수집은 0으로 리셋 후 재시작. 그 전에 이론·가설 완전 검증.
> 순서: 이론 검증 → 플랫폼(서버/카카오 로그인) → 유통. 배포·유통은 검증 완료까지 보류.
> **Leo 결정 (7/11)**: ① 서버는 레오서버로 이관(admin) ② 오염 차단 UX 승인(완료) ③ 별격 감지 진행(완료)

---

## 🚧 BLOCKED

| 항목 | 담당 | 사유 |
|------|------|------|
| Stage 1 검증 리포트 (실데이터) | reklcli | ✅ 서버 언블록(7/29) ✅ **DB 0 리셋 + arm 개방 완료(8/14)** → ★**이제 남은 전제는 「유입」 하나** = **유통 채널(LEO) 단독**. ★**8/15 교정** — 그전까지 「카카오 활성화 + 유통」 둘로 적어뒀으나 **카카오 로그인은 유입 수단이 아니다**(kimsecretary 지적, 수용): 들어온 사람을 붙잡는 장치일 뿐 데려오는 장치가 아님. 게다가 실측상 person dedupe 키가 `(name, birth_date, gender)`(`scripts/data_io.py:151`)라 **user_id에 안 물려 있어 검증 모수 품질 기여도 현재 0**. ⇒ 카카오 로그인 카드는 유입 전제에서 **분리**(TODO로 강등). 수집 시작선에 서 있고 **유입이 0이면 데이터도 0** |
| ~~자가배포 수정분 서버 반영~~ | ~~Leo~~ | ✅ **완료 (8/7, Leo 승인 후 flavor 직접 집행)** — 아래 DONE 참조. 배포 HEAD **f6d3d90**, 자가배포 첫 실사용에서 `reload:"ok"` + 워커 실교체 확인 |

---

## 📋 TODO

| 항목 | 우선순위 | 담당 | 비고 |
|------|---------|------|------|
| 콜드스타트 실 lift 측정 | Medium | reklcli | 리셋 후 커피 피드백 축적 시 `measure_coldstart_lift.py --db --arm random`(무교란). lift 확인 시 seed+LLM 주입 → 추천 교체 게이트(Leo 승인) |
| ~~콜드스타트 arm 게이트 개방~~ | ~~Medium~~ | ~~Leo~~ | ✅ **완료 (8/14, LEO 승인 — DB 리셋과 한 판)** — 아래 DONE 참조. `csa1-open-20260814` enabled=true·frac 0.15·seed_collection=true 라이브 |
| ~~seed 온보딩 문항 프론트 배선~~ | ~~High~~ | reklcli | ✅ **완료 (7/16)** — 아래 DONE 참조 |
| ~~커피 자아 리빌 카피/톤 결정 반영~~ | ~~Low~~ | ~~LEO~~ | ✅ **완료 (8/13, LEO 둘 다 B안)** — 아래 DONE 참조 |
| 파일럿 B (음악 콜드스타트) | Low | reklcli | 커피 파일럿 실 lift 검증 후. Music4All-Onion 코호트+경량 성격 |
| 학습 게이트 개방 (learning_gate enabled=true) | Medium | **Leo** | 리셋 후 도메인별 피드백 신뢰 규모 도달 시. 구현·테스트 완료, 활성화만 |
| vol1_taste(27문항) 메타 문항 적용 여부 | Low | Leo→reklcli | 별도 포맷이라 미적용 — 유통 재개 전 결정 |
| v0.2 서버 배포 | High | Leo→reklcli | 이론 검증 완료 후. Leo 배포 승인 필요 |
| ~~DB 리셋 실행~~ | ~~High~~ | ~~flavor2~~ | ✅ **완료 (8/14, flavor 직접 집행)** — 아래 DONE 참조. **submissions/feedbacks/users/milestones 전부 0행** |
| 카카오 로그인 **활성화** | ~~High~~ **Medium** | **LEO 본인** (kimsecretary 상신 중) | ★**8/15 강등** — 유입 수단 아님이 확정돼 「수집 개시」를 막는 카드가 아니게 됨(BLOCKED 24행 참조). ★**김비서 회신 결론(8/15 14:13)**: A-1 기등록 앱 **김비서 기록엔 0건**(단 「세상에 없다」는 아님 — LEO 계정에서 직접 앱 목록 확인 필요) / A-2 **대행 불가, LEO 본인 로그인 필수** — 김비서 카카오 MCP는 커넥터 제공 앱 경유라 **REST 키를 만들지도 꺼내지도 못함**. 김비서가 LEO께 3스텝 카드 상신 중(★flavor 재발신 불요). 실측 `/api/me` → `enabled:false` = **배선 라이브·키만 OFF**. 배선 완료(7/30, fail-safe OFF). **활성화 3스텝**: ① LEO 본인이 Kakao Developers 앱 등록(REST 키·Redirect URI `https://flavor.arkedia.work/auth/kakao/callback`·동의항목 profile_nickname) ② leoserver env 3종(`KAKAO_REST_API_KEY`·`KAKAO_REDIRECT_URI`·`FLASK_SECRET_KEY`) ③ `git pull`+재배포. 키 없으면 익명 흐름 항등 |
| 유통/바이럴 채널 결정 | **High** ← Medium | **LEO** | ★**8/15 승격 — 이제 이게 수집 개시를 막는 유일한 카드**. 김비서 실측으로 카카오 후보 2종이 걸러짐: ⑴ 김비서 카카오 MCP = 발송 도구가 전부 `send_*_template_to_me`(**수신자 파라미터가 스키마에 아예 없음**) ⇒ **유입 수단 아님, 계획에서 제외** ⑵ kmsg(카톡 데스크톱 자동화) = 실발송 되지만 **LEO 개인 계정으로 지인·기존 대화방**에 보내는 것 ⇒ n≥200 규모 아님, **LEO 결정 없이 집행 금지**(선 그어둠). ★남은 카카오 정공법 = **카카오톡 채널(비즈니스)/친구톡/알림톡** — 사업자 등록이 붙는 별건이고 **보유 여부 미확인, 개설은 LEO 결정**. 김비서가 이 건도 LEO께 별도 상신 예정 |
| Stage 2 게이트 판정 | Medium | reklcli | 리셋 후 n_persons 200 도달 시 `scripts/validate_saju_signal.py` |
| Phase D: ML 전환 | Low | reklcli | 200명+ 데이터 후, 하네스 Ridge CV 활성화 |

---

## ✅ DONE (최근)

| 날짜 | 항목 |
|------|------|
| 2026-08-21 | **ari 검사 판정 수령·반영** (LEO 지시 「에이리한테 검사받아」, 판정문=`flavor_ari_20260821_104924`): A(이사 정리)·B(슬랙 개통) **적정**. ⛔**단 내 「교정 실물」 주장이 가짜였음** — `AGENT_ID=flavor`는 스코프훅 트리거일 뿐 **커밋 author를 안 바꿈**(e33e32274 author=arkedia77 실측, solself author 오염 123건과 동근인). ▶**정처방**: `AGENT_ID=flavor git -c user.name=flavor -c user.email=flavor@leomusic.os commit …` + 커밋 후 `git log --format=%an -1`로 **「됐다」 실측** 후에만 보고. **이사 체크리스트 누락 축 4건 추가**: ⒜iterm 프로파일·기동 배선(admin, 정본=agent-comm `admin/tools/iterm_config.json`) ⒝AGENT_ID env 부여(이사 때 admin 집행 — flavor는 08-20 전수조사 「조치필요」 3슬롯 중 하나) ⒞ari 장부 machine 필드 갱신(ari 소관·이사 후) ⒟**슬랙 답신 경로 재확인 — `~/.ssh/config`의 `Host mukl mushin` alias가 머신 로컬분이라 이사하면 그대로 재발**. 부수: roster에 flavor 엔트리 0건은 ari 결손 — ari가 주내 세움(records/flavor.md 포함). 처분=계상만(실해 0) |
| 2026-08-20 | **★머신 이사(reklcli→미정, LEO 예고) 대비 전수 정리**: 레포 2개(flavor=`git@github.com:arkedia77/flavor`·agent-comm) **clean+origin 동기** = 새 머신 clone만 / leoserver `~/apps/flavor` **e4ff290 라이브·/health 200** 실측, 서버 이후 커밋 3건 전부 KANBAN.md뿐 = **배포 대기분 0건**(서버는 이사 무관) / 옮길 로컬분 = ①`~/.ssh/id_ed25519`(leoserver·mukl·github 공용 단일 키) ②`~/.ssh/config` 엔트리 2개(`leoserver`→100.110.3.116 · `mukl mushin`→100.75.69.61, 후자는 admin 8/18 추가분 — 없으면 슬랙 답신 `ssh mukl` 조용히 실패) ③메모리 폴더 `reklcli:~/.claude/projects/-Users-leo-projects-flavor/`(폴더명=작업폴더 절대경로 파생 — 새 경로가 다르면 개명 필요) / **ADMIN_TOKEN 로컬 값 없음=정상**(8/5 「회수」=ssh 개통으로 로컬 보관 불요, 값은 leoserver systemd drop-in에만) / `.venv` 재생성(requirements.txt, 테스트 185개로 검증). 상세=메모리 `project_flavor.md` 8/20 갈무리 |
| 2026-08-18 | **슬랙 답신 경로 개통 + LEO 앞 상태 톡 발신**: admin 공지 2건(`all_admin_20260818_204326` 표준 경로·`_210913` LEO 지시) 처리 — #flavor 방에 상태 한 줄 발신 성공(게시 ok 실측). 함정: 공지의 `ssh mukl`이 hostname 미해석 → Tailscale `mushin@100.75.69.61`로 성공 → admin이 `~/.ssh/config`에 `Host mukl mushin` alias 추가로 해소. 규율: [ROOM]/[SLACK] 주입 시 **당일 내 답신 또는 admin 대리([슬랙답신대리])**까지가 처리 |
| 2026-08-14 | **★★DB 0 리셋 + 콜드스타트 arm 개방 (LEO 승인, 한 판 집행)** — 실데이터 수집 개시. 배포 `e4ff290`.<br>**집행 순서**(리셋 중 쓰기 차단): 백업(`saju_submissions.db.bak_pre_reset_20260814_233350`) → `git pull` → `systemctl stop` → 구 DB 퇴역(`.retired_20260814_233400`) → 기동(`init_db` 신규 생성) → 검증 → **스모크 행 3건 삭제**. **최종 submissions/feedbacks/users/milestones 전부 0행**. 지워진 실데이터 = 7/29 DNS 스모크 1건(`120fa77f`)뿐<br>**게이트**: `csa1-open-20260814` — enabled=true·**random_frac 0.15**·seed_collection=true. 라이브 `/api/coldstart-config`=`{"seed_collection":true}` 확인. 실제 제출로 `_coldstart{seeds, arm_gate}`·도메인 `_arm` 저장 실측<br>★**개방 체크리스트 3번이 실결함을 잡았다** — 「클라이언트 렌더가 `_`접두 메타키를 건너뛰는지 확인」 → **아무도 안 건너뜀**(프론트 9곳·서버 1곳 전부 무필터). 게이트 켜는 순간 `/result`에 **라벨 `_coldstart`인 빈 9번째 카드**가 렌더되는 것을 재현. 렌더러 10곳 대신 **서버 경계 2곳**(`config.public_results()` → 제출 응답·`/result`)에서 차단 = 새 퀴즈 페이지가 추가돼도 자동 안전, **DB 저장본은 보존**(lift 분석이 `_coldstart.seeds`를 읽음). 테스트 +7(전체 **185**)<br>**롤백**: `enabled=false`면 즉시 항등 복귀. 구 DB는 `.retired_*`·`.bak_pre_reset_*`로 서버에 보존 |
| 2026-08-13 | **커피 리빌 결정 2건 반영 — 산미🫐·디저트🎂 노출 + 공유문구 펀치라인** (`6cd9340`, LEO 둘 다 B안): ① `COFFEE_PERSONA` 5종인데 `coffee_reveal()`이 pole을 black/sweet로 접어 **acidity·dessert 2종이 최종 카드에 원리상 안 나오던 것**을 `_refine_persona()`로 해소 — seed가 확정된 극의 하위 유형이면 그 카드로 승격. ★**pole(측정 축)은 불변** — 반응은 여전히 두 축으로만 측정하고 바뀌는 건 '어느 카드를 보여줄까'뿐(축 b 산미는 검증 전이라 측정 미사용·표현 재료로만). 반전 카드는 세분화 안 함(극 대비는 반전이 이미 표현). 감사용 `refined` 플래그 ② `_share_text()` 일원화로 oneliner 부착 — `내 커피 자아 = 겉은 블랙, 속은 스위트형 🎭 — 쿨하게 아메리카노 시켜놓고 결국 단 거에 반하는 반전 매력`. 테스트 +10(전체 **178**), 핵심 가드=「세분화해도 측정축은 안 바뀐다」. 엔드투엔드 OFF=항등/ON=실림 확인. **게이트 OFF라 사용자 화면 변화 0**<br>경위: kee 반려(8/12, 취향·브랜드는 LEO 전속) → LEO 직접 결정 |
| 2026-08-12 | **★26일 미발신 자기적발 + kee 판정 3건**: KANBAN에 7/16부터 「kee 검토 대기」로 적힌 리빌 결정이 **발신된 적 없음**을 발견(`find projects -name "kee_flavor_*"` → 0건). ***「대기」는 상대의 상태가 아니라 내 기재였다.*** kee 채택 — kee의 적치 처방(「가장 오래된 미처리 age」)이 **자기 인박스를 모집단으로 삼아 이 건을 원리상 못 잡음**(인박스에 없으니 age=0) → kee가 축 신설(「내 보드에 남 대기로 적힌 항목에 실제 발신 이력이 있는가」). 같은 형태가 그날 **세 곳 독립 발생**(flavor 26일·kee→sens 19일·kee→lmb 19일). kee 판정: ⑴리빌=**반려**(LEO 전속) ⑵속도규율 문서층 미착지=admin 발주(**flavor 재발신 금지**) ⑶L0 ⓒ형+제품repo에 심링크 처방 **부적합 인정**(제품 repo가 leoserver 배포 → dangling symlink) = **초과 감수·감축 압박 없음**. 표기 정정: `Leo(kee)` → **LEO 단일**(「보드에 두 이름이 같이 적히면 둘 다 자기 것이 아니라고 읽는다」) |
| 2026-08-07 | **★배포 f6d3d90 + 자가배포 첫 실사용 성공 (Leo 승인, flavor 직접 집행)**: `ssh leoserver` → `git pull`(69ab835→f6d3d90, 5커밋) + `sudo systemctl restart flavor`(MainPID 1758506→2526223). 선행 확인=의존성·스키마 변경 0(런타임 코드는 `api/admin.py` 1건). 검증: `/health`·`/api/me`·`/`·`/food-saju` 200, 무토큰 deploy 403. ★**그리고 자가배포를 처음으로 실제 집행** — `POST /api/admin/deploy` → `{"status":"ok","reload":"ok","master_pid":2526223}` + **워커 실교체**(2526225/226→2526478/480, 마스터 유지) = SIGHUP이 올바른 프로세스에 닿아 실제로 일했다는 증거. 구코드였다면 사망 PID 31344에 쏘고 `warn`+200이었음. 부수: 버그 근원인 stale PID 파일을 삭제 대신 `.stale_20260723_removed_20260807`로 개명(현 코드 참조 0회, 되돌림 여지 보존) |
| 2026-08-05 | **★자가배포 리로드 결함 발견·수정 (33ebafa)**: admin이 ssh 공개키가 이미 등재돼 있음을 실측 회신 → reklcli `~/.ssh/config` 3줄 추가로 leoserver 개통(tailscale 100.110.3.116), ADMIN_TOKEN 회수. **ssh가 열리자마자 리로드 쟁점을 직접 실측** — 예상('PID 파일 부재로 warn')이 틀렸고 실제는 **파일이 있고 값이 stale**: `ExecStart`에 `--pid` 없음 + `logs/gunicorn.pid`=31344(7/23자, **사망**) vs 실제 마스터 1758506 → `os.kill` OSError를 except가 삼키고 **HTTP 200** = pull만 되고 구코드가 도는 조용한 실패. 잠재 위험=stale PID 재활용 시 무관 프로세스에 SIGHUP(기본 동작=종료), leoserver 15종 서비스 물림(pid_max 4.19M/현재 2.2M이라 아직 도달 전). **조치**: PID 파일 참조 폐기 → 워커의 부모가 곧 마스터(`os.getppid()`)+커맨드라인 `gunicorn` 검증 후에만 시그널, 리로드 실패는 **200이 아니라 500**+복구 힌트. 테스트 +8(전체 **168**). admin `--pid` 권고는 철회(유닛 무변경). 서버 반영은 Leo 승인 대기(위 BLOCKED) |
| 2026-08-05 | **수신함 전수 점검 + project_docs 제출**: 루트 잔류 12건 판정 → 4/2 `project_docs` 자기소개서가 **4개월 미이행**임을 발견(타 10건 등재, flavor만 누락). 작성 후 `admin/` 직접 커밋은 스코프훅 차단 → **`AGENT_ID_BYPASS` 우회하지 않고** 정규 경로(내 스코프 원고+admin 등록요청)로 처리 → admin 등재 완료(4,335B 실물 확인) 및 "우회 안 한 판단이 맞다"는 평가 수령. 나머지 11건(완료보고·broadcast·본인 발신분)은 `processed/` 이관, 루트 0건. 부수: `agent-comm/projects/flavor/CLAUDE.md`의 CHANNEL_RULES 버전 핀(v5.5, 현행 v5.11) 제거 → 정본 참조 |
| 2026-08-04 | **leoserver 재배포 종결 확인 + 자가배포 개통(부분)**: 7/31 admin이 이미 `git pull`+재기동 집행 → 배포 HEAD **69ab835=origin/main 최신**. flavor가 외부 도메인 층에서 재검증(`/health` 200, `/api/me` 200 `enabled:false`=카카오 배선 라이브·키 OFF, `/static/og_dna.png` 200, `/`·`/romance-v2`·`/food-saju` OG 주입 실재) — **배포 대기분 0건**. ADMIN_TOKEN도 systemd drop-in으로 주입 완료(무토큰 403 실측)이나 **값이 reklcli에 없어 자가배포는 미개통** → 전달 경로 발주(admin_flavor_20260804_134431). 부수 발견: `/api/admin/deploy`의 SIGHUP 리로드가 systemd PID 파일 부재 시 조용히 실패(200 반환)할 수 있어 admin에 `--pid` 확인 동봉 |
| 2026-07-30 | **카카오 로그인 배선** (fail-safe OFF): users 테이블+submissions.user_id(additive) + api/auth.py 인가코드 플로우(/auth/kakao/login·/callback·/logout·/api/me, stdlib urllib=무의존, state CSRF+오픈리다이렉트 차단) + 세션 user_id 부착(익명=None 항등) + 허브 로그인 버튼(enabled일 때만). **키 미설정=익명 흐름 완전 항등**(OFF/ON 런타임 스모크 확인). 테스트 +11(전체 152). 활성화=Kakao앱 등록+env 3종+재배포(Leo) |
| 2026-07-29 | **★flavor.arkedia.work DNS repoint 완료 — 이관 100% 종료**: admin이 본인 보유 CF 토큰으로 직접 집행(Leo 토큰 발급 불요였음). CNAME 982b1f34(구 mukl)→78dc937e(leoserver) update, 502→200. flavor 재검증: 퀴즈 라우트 6종+제출 스모크(id 120fa77f→/result 200) **전건 200 엔드투엔드 확인**. 부수: mukl stale ingress(→8082, 502 직접원인) 주석 처리(cloudflared 미재기동, 타 서비스 15종 보호). 회신 admin_flavor_20260729_224800 |
| 2026-07-23 | **flavor leoserver 이관 배포 (admin 집행, 95%)**: DB백업(.bak 보존)+신규 빈 DB 0리셋+systemd(재부팅 생존)+CF ingress. 로컬 /health·/=200 실측. 유일 잔여=DNS CNAME repoint(Leo 게이트, 위 IN PROGRESS). 이관 재요청 admin_flavor_20260723_110229, 6분 만에 회신 |
| 2026-07-23 | **레거시 vol2/vol3·종합설문 seed 온보딩 배선**: shared vol4~20에만 있던 커피 seed 온보딩을 인라인 JS 5파일(romance_v2/food ±saju, survey.html)에 이식 → 콜드스타트 수집 커버리지 완결. 게이트 OFF=항등(서버 seeds 일반처리). node 문법검증 5파일 통과, 141 테스트 무회귀 |
| 2026-07-17 | **키워드 seed 패밀리 자연어 확장** (Leo 승인, 엔진): OOV 회복 위해 black에 '우유 없이'류, sweet에 설탕·생크림·부드럽·달게·믹스·'우유 많이'류 패밀리 추가. **OOV 0%→87.5%(7/8), in-vocab 100% 유지(무회귀)**. bare '쓴'은 부정("안 쓴") 충돌로 제외 = 정직한 LLM 영역. 패밀리당 1회 계상+총 LR 캡 3배(fableself Q3) 유지. 테스트 141개 |
| 2026-07-17 | **seed 분류기 오프라인 평가 하네스** (`scripts/eval_seed_classifier.py`): 대표 한국어 커피 seed 라벨셋(축 a)으로 분류기 품질을 실데이터 전에 검증. **측정 결과**: 키워드 휴리스틱 = 어휘 내 20/20(100%)이나 **어휘 밖 자연어("우유 없이 쓴맛으로", "설탕 팍팍") 0/8(0%) — 전부 중립으로 흘림** = LLM 경로 존재 이유 정량화. `--llm`로 Claude 회복률 비교(크레덴셜 필요). 테스트 141개(+4) |
| 2026-07-17 | **콜드스타트 LLM seed 우도 = Claude 래퍼 주입** (개방 체크리스트 항목 4): `scripts/llm_claude.build_claude_complete_fn()`(anthropic 지연 임포트, engines/ SDK 무의존 유지) → `measure_coldstart_lift.py --llm [--llm-model]`로 seed 우도를 키워드 휴리스틱→LLM 승격. 미지정 시 현행 항등. 테스트 137개(+3, 클라이언트 주입으로 네트워크 없이 검증). 자격증명=SDK 기본 해석, 서버 서빙 경로 무영향 |
| 2026-07-16 | **커피 자아 리빌 카드 렌더 프리뷰**(개방 전 비주얼 점검): 실제 coffee_reveal×renderCoffeeReveal 템플릿 그대로 아티팩트 발행. 카피/톤/카드 다양성 결정(산미·디저트 페르소나 미노출, 공유문구 펀치라인 미포함). ⚠**당시 「Leo 검토 대기(내일, kee)」로 적었으나 발신하지 않았음 — 8/12 자기적발·발신 완료**(위 TODO 참조) |
| 2026-07-16 | **커피 자아 리빌 프론트+서버 배선 완료**: /api/feedback가 게이트 ON·커피일 때 응답에 reveal 실어 내림(served 아이템+seed→coffee_reveal), sendFeedback가 lock 후 리빌 카드 렌더(스냅샷·반전·공유). thumb 정정(🤷=중립, 👎만 반전). OFF=항등 엔드투엔드 확인. 테스트 134개 |
| 2026-07-16 | **커피 자아 카드 로직층 + fableself 배치 결정**: Leo 재미·공유 원칙 → seed를 캐릭터로 되돌림. fableself(Leo 위임) 결정=예측 라벨 노출은 랜덤 arm으로도 못 고치는 측정 오염 → 카드는 측정창 종료+피드백 lock 후 '피드백 산출물'로 리빌. `coffee_reveal()`(반응 주재료, said 어긋나면 반전카드 '겉은블랙 속은스위트') + `coffee_persona()`. 테스트 130개. 프론트 배선은 다음 |
| 2026-07-16 | **seed 온보딩 프론트 배선** (Leo 지정 7/13): 커피 seed 1문항 자유입력 → submit `seeds:[]`. 서버 게이트 `/api/coldstart-config`(seed_collection, 기본 OFF) 노출 → quiz-engine.js가 플래그 ON일 때만 마지막 문항 후 seed 화면 **동적 주입**(HTML 쉘 20여개 무변경). OFF=완전 항등 엔드투엔드 확인(문항 미노출·`_coldstart` 미부착). 배정 규칙(랜덤 arm)은 서버 담당이라 프론트 미노출. 테스트 115개(+3). shared 엔진 vol4~20 커버, 레거시 vol2/vol3·종합설문은 별도 JS라 이후 확장 |
| 2026-07-13 | **콜드스타트 커피 축 정직화 + 키워드 교정** (페플셀프 점검 Q1·Q3·Q6, Leo 승인): 쓴맛형/산미형 → 진한 블랙형/부드러운 스위트형(축 a=우유·단맛 유무). 핸드드립·산미=축 b 예약어 분리. seed 패밀리 계상+총 LR 캡 3배. pivot 변수화. 심볼 전수 동기, 테스트 112개 |
| 2026-07-13 | **콜드스타트 랜덤 arm + seed 수집 + LLM 우도 인터페이스** (페플셀프 점검 Q2/Q3 반영, Leo "①리셋 전 필수" 선택): 리셋 순간부터 켜야 소급 가능한 2건 게이트형 구현. apply_random_arm(OFF=완전 항등) + config/coldstart_arm.json + submit 배선(seeds→results._coldstart) + lift 하네스 --arm random 무교란 필터 + build_llm_infer. 설계서 docs/COLDSTART_MEASUREMENT_DESIGN.md. 테스트 20개(전체 107). OFF/ON 엔드투엔드 스모크 확인. 커밋 push 완료 |
| 2026-07-13 | **페플셀프 파일럿 A 점검** 의뢰·회신: 방향 충실, 실질 결함 2건(키워드 축 혼동·lift 셀렉션 바이어스). 리셋 전 필수=랜덤 arm+seed 수집(소급 불가). exchange/flavor-pilotA-review-v01.md |
| 2026-07-12 | **파일럿 A — 커피 콜드스타트 예측** (Leo 승인, fableself 리서치 기반): 코호트(연령·성별 문헌 계수)+seed 베이지안 → 쓴맛형/산미형. lift 하네스(concordance, 저장 데이터 소급 재계산) 합성검증 통과. 사주=미사용(외부 예측력 0). 실 lift는 데이터 대기, 추천 교체 미적용 |
| 2026-07-12 | **fableself 리서치 의뢰·회신**: 외부 데이터셋/방법론 shortlist. 결론=코호트+LLM seed 콜드스타트가 최속 lift, 사주=예측력 0(게이트 정합 확인) |
| 2026-07-12 | **학습 루프 실작동 (게이트)** (Leo 선택): 무력했던 confidence 주석 → 유사유저 피드백 아이템 재랭킹. domains.py 후보 풀 + recommend.py learned_rerank + config/learning_gate.json(default OFF=항등). 활성화만 Leo 승인 대기 |
| 2026-07-12 | **클라이언트 맵 MAP_V2 패리티** (§7): saju-engine.js가 감사 이전 구맵 → 서버 V2 동기화 + 가드 테스트. 감사 아크 완결 |
| 2026-07-12 | **게이트 수정안 v1.1 발효** (Leo 승인): 노출 전 원칙 + CONTAMINATION_FLAG + 신봉도 층화가 게이트 판정 정본 기준 |
| 2026-07-12 | **오염 완화책 3·4 완료**: 어휘 분리(사전+페르소나 리라이트+가드 테스트), nc/신봉도 메타 문항, 하네스 v1.1. 버그픽스 2건(클라이언트 지장간 본기, innate 집계 공회전) |
| 2026-07-12 | **sf-4 국(局) 감지 검증 → 미채택**: 별격 recall +7pp ↔ 정격 오탐 상쇄, 교차평가 이득 0. 실험 코드 experiment/sf4-guk 보존 (VERDICT_2026-07-12_guk) |
| 2026-07-11 | **오염 차단 UX** (Leo 승인): 선천 배너 응답 후 노출, A/B 랜덤 순서, ux:'nv1' 플래그 — 엔진+레거시 4파일 |
| 2026-07-11 | **별격 감지 v1 (sf-3)**: 합화/양기성상/전왕/종격 + 록겁 격명 + 순세 용신. 격국 44.9%→61.7% (VERDICT_byeolgyeok) |
| 2026-07-11 | **이론 검증 사이클 1 완결**: 신강약 87.5% ✅ / 격국(자평진전) 75% ✅ / 용신 47.8% ❌→저신뢰 태그 (VERDICT 2건) |
| 2026-07-11 | 억부용신 v2 원인 기반 규칙 (sf-2, +10.4pp), 적천수천미 508 정답지 구축 |
| 2026-07-10 | **Leoflavor v0.2 — 사주 검증 게이트** 설계+구현 (설계서 docs/ENGINE_V02_DESIGN.md) |
| 2026-07-10 | engines/saju_features.py: 십신 강도(지장간·궁성 가중)/신강약/억부용신/격국+투간/상호작용 7종 |
| 2026-07-10 | 검증 하네스 scripts/validate_saju_signal.py (Spearman+순열+BH-FDR, 기준 pre-registered) |
| 2026-07-10 | 버그픽스: sipsin.py 지장간 본기(여기로 읽던 것), recommend.py 🎯→👎 집계, measure_accuracy 동일 |
| 2026-07-10 | Phase B 배선: submit.py에 get_feedback_data 연동 (min_sim 0.3, min_contributors 3) |
| 2026-07-10 | DB saju_json 컬럼 + admin export 확장, 테스트 31개 (tests/) |
| 2026-03-22 | 피드백 UI 4단계 리액션 교체 (👍👎 → 🎯👍🤷👎, 2x2 그리드, thumb 2/1/-1/-2) |
| 2026-03-20 | 시즌 매거진 허브 리디자인 (시즌 탭, 매거진 카드, 프로그레스바, 리포트 CTA) |
| 2026-03-20 | 취향 리포트 페이지 (`/my-report`, `/my-report-saju`) — 수집 그리드, 갭분석, 공유 |
| 2026-03-20 | quiz-engine.js: 결과 타입(innate/actual) localStorage 저장 추가 |
| 2026-03-18 | 시즌 2 퀴즈 10개 (vol11-vol20) DNA+사주 20파일 생성, 40개 라우트 추가 |
| 2026-03-18 | 기존 퀴즈 전수 검수: 오타, 전문용어→일반어, 브랜드명 삽입 |
| 2026-03-18 | 퀴즈 제목 개그맨 페르소나(유재석+신동엽) 리라이트 |
| 2026-03-18 | 어드민 대시보드 `/dashboard` 생성 |
| 2026-03-18 | 피드백 UI(👍👎) 전 퀴즈 추가 (→ 3/22에 4단계 리액션으로 교체) |
| 2026-03-16 | 적중률 측정 실행 (74.8%, 테스트 데이터) |
| 2026-03-15 | 만세력 엔진 교체: lunar 라이브러리 |
| 2026-03-15 | 전체 퀴즈 135문항 실제사례 리라이트 |

---

## 📌 메모

- **현재 총 퀴즈**: 시즌1(9개) + 시즌2(10개) + 종합(1개) = 20개 (DNA+사주 = 40파일)
- **접속 현황 (3/20)**: 총 90건 누적, 최근 24시간 0건 → 유통 급선무
- **카카오 로그인**: 네이버보다 쉬움, client_secret 선택, 검수 불필요. localStorage→서버 세션 전환 필요
- 다음 milestone: 200명 (ML 전환)
- **발신 속도 규율 4조** (admin 08-09 19:03 P0 발효): `to` 수신처 **5곳 이상**이면 발신 전 「사전 반증 1회」.
  되돌릴 수 없는 요구는 판 확정 후에만. 개정본엔 반증자 포함. **과거를 소급 위반으로 세지 말 것.**
  → flavor 발신은 거의 admin 1곳이라 실질 무영향. **문면 복제 안 함**(킷 §4-4 + L0 초과 상태).
  ⚠**미착지 3일 경과 (8/12 재확인)**: `CHANNEL_RULES.md`=v5.6, 규율 관련 `grep` **0건**(킷도 0건).
  집행층(`pre-commit:187~202`)은 정상 — kee 판별선 「집행층엔 갔고 문서층에만 안 갔다」(encore)의 사례가
  그 판별선을 낳은 규율 자신. admin 상정(8/9)+kee 보고(8/12) 완료, **재촉 없이 대기**(규율 C).
  착지 안 되면 브로드캐스트는 어느 세션 컨텍스트에도 안 남아 다음 세션이 규율을 모른다.
  ⚠**미결 2건이 정본 없이 떠 있음**: 「무응답 시효」·차단 전환/`pre-push` 축 (판정 소관=kee).
  → **kee가 admin에 발주 완료 (8/12)**. ★**flavor는 admin에 다시 보내지 않는다**(중복 재촉 — kee 지시).
- **L0 (kee 8/12 판정)**: flavor는 **ⓒ형+제품repo**라 L0 래칫이 권하는 「agent-comm 정본+로컬 심링크」
  처방이 **부적합**(제품 repo가 leoserver 배포 → 서버에서 dangling symlink). ⇒ ★**현 판정=초과 감수·감축
  압박 없음.** 처방 유형별 분기는 kee가 admin 발주.
  ★**표기 규칙**: L0는 **항상 두 값 병기** — **2파일 107% / 머신공통층 포함 157%**.
  (공통층 `~/.claude/CLAUDE.md` 3,080B를 모집단에 넣을지는 **미결** — 157%만 인용하면 위험)
