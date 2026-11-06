# 사전등록 — 아마존 동일인으로 일반 축(강도·자극)이 분야를 넘어 함께 움직이나

**작성**: 2026-11-06 flavor | **지시**: LEO 슬랙 11-06 「음식이 아닌 다른 취향의 경우에도 일반 축은 의미가 있어」(스레드 `1793364360.433739`)
**규칙**: CD·영화 리뷰 파일을 받기 전, 결과를 보기 전에 커밋한다. 상품 메타(상품명·범주 이름)만 보고 축을 정했다. 커밋 뒤 기준을 바꾸지 않는다.
**정본**: Notion `40a76e47daa381e4b02ed8aeb0afd003` ★ 논리 판정 절(다섯 레이어, 레이어 2 일반 축).

## 0. 묻는 것

레이어 2의 일반 축은 음식에만 걸리는 축이 아니라 모든 취향에 걸리는 축이어야 한다(LEO 11-06). 그런데 「한 축이 음식과 음악·영화를 같은 사람에게서 함께 움직인다」는 1차 근거는 조사에서 0건이었다(`docs/research/general_taste_axes_20261106.md`). 같은 사람이 식품·음악·영화를 모두 리뷰한 아마존 자료로, 후보 축 중 근거가 가장 직접적인 **② 강도·자극 선호**가 세 분야에서 같은 방향으로 나타나는지 본다.

## 1. 자료

- Amazon Reviews 2023 (McAuley Lab, Hou et al. 2024): `Grocery_and_Gourmet_Food`(11-04 분석에 쓴 같은 파일), `CDs_and_Vinyl`, `Movies_and_TV`의 리뷰와 메타. sha256은 결과 리포트에 적는다.
- 라이선스: 공개 카드에 명시가 없다. 연구용으로만 쓰고 레포에는 집계만 둔다.
- 사용자 ID는 리뷰의 `user_id`. 세 파일에서 같은 값이면 같은 사람으로 본다.

## 2. 축 (리뷰 열람 전 확정, 상세 값은 `scripts/amazon_cross_domain.py`)

| 분야 | A = 강한 쪽 | B = 순한 쪽 | 기준 |
|---|---|---|---|
| 식품 | 상품명: `extra hot`/`spicy`/`habanero`/`ghost pepper`, 다크·프렌치·이탈리안·에스프레소 로스트, `dark chocolate`, 70–90% 카카오 | 상품명: `mild`, `milk chocolate` | 11-04 사전등록의 매운맛·로스트·초콜릿 축을 한 축으로 묶음. 라이트 로스트는 산미 축이라 뺌 |
| 음악 | 범주: Metal, Hardcore & Punk, Punk, Hard Rock, Hard Rock & Metal, Death Metal, Industrial, Goth & Industrial, Alternative Metal, Gangsta & Hardcore, Hardcore, Progressive Metal, Pop Metal | 범주: New Age, Easy Listening, Smooth Jazz, Adult Contemporary, Meditation, Ambient, Traditional Vocal Pop, Vocal Pop, Traditional Pop | MUSIC 모델 Intense ↔ Mellow (Rentfrow et al. 2011) |
| 영화 | 범주·분위기: Horror, Action & Adventure, Action, Mystery & Thrillers, Suspense, Intense, Tense, Thrilling, Frightening, Gritty | 범주·분위기: Romance, Gentle, Cheerful, Charming, Joyous, Musicals | Kids & Family는 부모 여부라는 교란이 커서 뺌 |

- 한 상품이 같은 분야의 A와 B에 모두 걸리면 뺀다.
- 「좋아함」은 평점 4 이상. 사용자 방향은 좋아한 A 수 > B 수이면 A, 반대면 B, 같으면 제외(11-04와 같은 규칙).

## 3. 검정 (2×2 표, 사용자 라벨 순열 B=10,000, seed=20261106, 한쪽: A–A 칸이 우연보다 많다)

| # | 가설 (방향 고정) | 통과 |
|---|---|---|
| **X1 (주검정)** | 강한 식품을 좋아하는 사람은 강한 음악 쪽이다. 오즈비 > 1 | p < 0.01 |
| X2 | 강한 식품 ↔ 강한 영화. 오즈비 > 1 | p < 0.005 |
| X3 | 강한 음악 ↔ 강한 영화. 오즈비 > 1 (음식이 빠진 비교) | p < 0.005 |

- 셀 하나라도 30 미만이면 그 검정은 「판정 불가」이고 수치는 참고로만 둔다.
- **보고할 크기**: 오즈비, 순열 영분포 5–95백분위, 한 분야 방향을 알 때 다른 분야 방향 적중률과 기준율의 차이(LEO 7/12 base-rate lift).

## 4. 통제 (판정 외)

- P1·P2 플라시보: 식품의 「상품명에 organic 포함」 방향(축 상품 제외)을 음악(P1)·영화(P2) 강도 방향과 대 본다. 맛·강도와 무관한 쇼핑 성향 축이다. 이 관계가 X1·X2만큼 크면 X1·X2를 약하게 읽는다(11-04 결과에서 플라시보가 더 컸던 교훈).

## 5. 해석 경계 (결과 전에 적어 둔다)

- **나이·성별 교란을 이 자료로는 가르지 못한다.** 젊은 남성이 매운 음식과 메탈을 함께 좋아하는 것만으로도 X1이 통과할 수 있다. 그래서 통과는 「분야를 넘어 함께 움직이는 무언가가 있다」까지이고, 그것이 타고난 일반 축인지 인구 집단 차이인지는 말하지 않는다.
- 반대로 이런 교란이 있는데도 관계가 없다면, 분야를 넘는 일반 축이라는 가정은 약해진다. 그쪽이 더 많은 정보를 준다.
- 상품명·범주 키워드로 잡은 축은 거칠다. 리뷰를 쓰는 사람은 치우쳐 있다.
- 엔진 공식·가중치는 바꾸지 않는다(LEO 승인 사항).
