# 오염 완화책 3·4 구현 기록 — 2026-07-12

**근거**: EVIDENCE_AUDIT_2026-07-10.md 완화책 목록 (1·2는 2026-07-11 완료)
**승인**: Leo (2026-07-12 "EVIDENCE_AUDIT 완화책부터 진행" — 이론 토대 우선 지침)
**게이트 기준 수정안**: docs/ENGINE_V02_DESIGN.md §4 수정안 v1.1 (발효는 Leo 승인 커밋)

---

## 완화책 3 — 어휘 분리

사주 파생 카피가 설문 도구 어휘를 쓰면 자기귀인으로 십신→취향 상관이 인공 생성된다.

- **어휘 사전**: `config/dimension_lexicon.json` — 전 퀴즈 문항/트레이트에서 차원별
  서술어 큐레이션 (social 사교/혼자/함께…, adventurous 모험/도전/새로운… 등 9차원)
- **페르소나 리라이트**: 일간 페르소나 10종 중 9종이 오염 어휘 포함이었음
  (탐험가/새로운/호기심↔adventurous, 안정감↔comfort, 에너지↔energetic,
  완벽주의자↔maximalist, 아름답게↔aesthetic, 깊은 감각↔bitter 등)
  → 사물·자연 이미지로만 재서술. 서버(engines/persona.py)와 클라이언트
  (static/shared/saju-engine.js) 동기 수정
- **가드**: `tests/test_lexicon_separation.py` — 어휘 위반 + 서버/클라이언트 패리티
  자동 검사. 새 사주 카피 표면이 생기면 테스트에 추가 의무

## 완화책 4 — 네거티브 컨트롤 + 신봉도

- **메타 문항 2개** (모든 A/B 퀴즈 끝에 자동 추가, 9차원 프로필에서 제외,
  answers 배열로 저장 — DB 스키마 변경 없음):
  - `nc_noodle` 네거티브 컨트롤: "라면 국물부터 vs 면부터" — 사주 이론(MAP_V2)·
    표시 카피와 무연결, delta 영구 부재 서약. 사주 피처가 이걸 "예측"하면 오염
  - `meta_belief` 신봉도: "사주 꽤 믿는 vs 재미로만" — 바넘/자기귀인 층화 공변량
  - 적용: quiz-engine.js(공용 36퀴즈) + 레거시 인라인 4파일(vol2/vol3 DNA·사주)
- **하네스 v1.1** (`scripts/validate_saju_signal.py`):
  - 노출 전 서브셋 = 게이트 판정 주 대상 (첫 제출 survey, 실측 차원만)
  - `negative_control()`: prior×nc 상관이 CONFIRMED 동등 기준 충족 시
    CONTAMINATION_FLAG → 리포트 전체 무효
  - `belief_stratified()`: CONFIRMED가 비신봉군에서 부재/역부호면
    SELF_ATTRIBUTION_SUSPECT → 개방 보류
- **테스트**: tests/test_harness_v11.py 12개 (합성 데이터 — 심은 신호 flag ✓,
  잡음 무flag ✓, 층화 suspect ✓) + 합성 DB 30건 엔드투엔드 스모크 통과

## 함께 수리한 버그 2건

1. **클라이언트 지장간 본기 버그**: saju-engine.js가 지장간 배열 마지막(여기)을
   본기로 카운트 — 서버 sipsin.py의 2026-07-10 수정과 동일 버그가 클라이언트에
   잔존. lunar-javascript 앵커 검증(1977-04-11 무술일 → 술 본기 비견) 후 arr[0]으로
   수정. 종전 innate 표시값/agreed_with_innate가 왜곡돼 있었음 (리셋 전 데이터라 영향 무)
2. **하네스 innate 집계 공회전**: dedupe_persons 출력에 submissions가 없어
   innate_agreement()가 항상 0건 — submissions 포함으로 수정 + 회귀 테스트

## 남은 한계 (알려진 것)

- **트레이트 축 구조 노출**: 결과 화면이 선천 마커를 설문 축(low/high 라벨) 위에
  직접 표시 — 어휘 분리로 못 막는 구조적 오염. v1.1-①(첫 제출만 게이트 사용)이
  통계적 방어선. UI 재설계는 별도 결정 사항
- **퀴즈 유형명 어휘**: innate/actual 공용 유형명("문화 탐험가" 등 40파일)은
  설문 어휘 포함 — 동일하게 v1.1-①로 방어. 전량 리라이트는 비용 대비 보류
- **vol1_taste(27문항 survey.html)**: 메타 문항 미적용 (별도 포맷) — 유통 재개 전
  적용 여부 결정 필요
- nc 문항 1개는 표본 특성상 우연 상관 가능 — flag 발생 시 문항 추가로 재검 권장
