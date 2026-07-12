# 파일럿 A — 커피 콜드스타트 취향 예측 (구현 기록)

**날짜**: 2026-07-12
**승인**: Leo ("응 해보자", fableself 리서치 회신 검토 후)
**근거**: fableself 리서치 (agent-comm/projects/fableself/exchange/flavor-taste-research-v01.md)
**목적**: 카테고리 내 '제품 종류'(커피 쓴맛형/산미형)를 base rate보다 높은 확률로 예측 —
자체 설문·데이터 0에서 시작하는 콜드스타트.

---

## 무엇을 만들었나

1. **engines/coldstart.py** — 코호트 사전확률 × seed 우도 베이지안 예측기
   - `cohort_bitter_prior(age, gender)`: 문헌 방향성 prior. 연령↑→쓴맛↑(Barragán 2018),
     남성→쓴맛/여성→산미(Frontiers 2024, PTC 테이스터). fitted 아님, 클램프 [0.15, 0.85].
   - `predict_coffee_type(age, gender, seeds, llm_infer)`: 사전확률 × seed 자연어 우도
     → 쓴맛형/산미형. LLM은 콜러블 주입(미지정 시 오프라인 키워드 휴리스틱).
   - **사주·별자리·출생계절 미사용** — 외부 예측력 0(fableself 확인, 현행 사주 게이트 0과 정합).
     생년월일은 연령 환원분만 투입.
2. **scripts/measure_coldstart_lift.py** — base rate 대비 lift 하네스
   - concordance lift = P(👍|보여준 타입==예측) − P(👍|불일치). 부분관측(아이템 1개만
     노출) 하의 정직한 지표.
   - 저장된 birth_date·gender에서 예측을 **결정적으로 재계산** → 예측 사전 로깅 불필요,
     옛 행도 소급 측정. seed는 아직 미수집이라 코호트-only.
   - 합성 자가검증: 신호 있음 lift=0.099, null=−0.008 → 하네스가 신호를 잡고 잡음엔 무반응.
3. **tests/test_coldstart.py** — 17개 (단조성/성별/클램프/seed 방향/LLM 주입/풀 라벨 커버리지/
   하네스 신호·null·재구성). 전체 87개 통과.

## 정직성 (효과크기·한계)

- 계수는 **문헌 방향성 prior**이지 적합값이 아니다. 기대 lift는 소~중(fableself: "확률을
  올리는 게임"에 정확히 부합, 마법 아님).
- **실 유저 lift는 아직 미측정** — 데이터 0(리셋 대기). 예측기+하네스는 구축·합성검증
  완료 상태이며, 커피 피드백이 쌓이면 `--db`로 즉시 실측정 가능.
- seed 층은 인터페이스만 완성(오프라인 키워드 기본). 자연어 seed 수집(온보딩 or 카페 퀴즈의
  coffee_purist 등 카테고리 직접 신호 연결) + 실 LLM(Claude) 주입이 확장 지점.
- **추천 교체 미적용**: 이번 파일럿은 예측·측정까지. 예측으로 추천 아이템을 실제 교체하는
  것은 실 lift 검증 후 별도 게이트(사주·학습 게이트와 동일 패턴, Leo 승인)로 개방.

## 다음 단계

1. 리셋 후 커피 피드백 수집 → `measure_coldstart_lift.py --db`로 실 lift 측정.
2. lift 확인 시: 자연어 seed 수집 + 실 LLM 주입 → 코호트 위 보정층 활성화.
3. lift 확정 시: 콜드스타트 게이트로 커피 추천 아이템 교체 개방 (Leo 승인).
4. 파일럿 B(음악, Music4All-Onion 코호트+경량 성격) — 커피 파일럿 검증 후 확장.
