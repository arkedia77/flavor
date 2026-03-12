# Leoflavor KANBAN

**최종 수정**: 2026-03-12
**엔진**: Leoflavor v0.1

---

## 🔄 IN PROGRESS

| 항목 | 우선순위 | 담당 | 비고 |
|------|---------|------|------|
| Leoflavor v0.1 코드 완성 | High | reklcli | 엔진 재설계 완료, 테스트 통과 |

---

## 📋 TODO

| 항목 | 우선순위 | 담당 | 비고 |
|------|---------|------|------|
| 60건 실데이터 적중률 재측정 | High | reklcli | 사주 blend 제거 후 변화 확인 |
| 210건 피드백 → 학습 루프 검증 | High | reklcli | recommend.py 실데이터 테스트 |
| 바이럴 퀴즈 기획 | Medium | reklcli | 데이터 플라이휠 |
| v0.1 서버 배포 | High | mukl | git pull + restart |
| Phase B: 피드백 실시간 반영 | Medium | reklcli | submit.py에 get_feedback_data 연동 |
| Phase C: 바이럴 퀴즈 3종 | Medium | reklcli | 연애/여행/식도락 |
| Phase D: ML 전환 | Low | reklcli | 200명+ 데이터 후 |

---

## ✅ DONE (최근)

| 날짜 | 항목 |
|------|------|
| 2026-03-12 | Leoflavor v0.1 엔진 재설계 (사주 blend 제거, 피드백 학습 구조) |
| 2026-03-12 | 사주 가설 최종 판정 (60건 분석, 통계적 미지지) |
| 2026-03-12 | 아카이브: v1.5-archive 태그 + archive/saju-engine-v1.5 브랜치 |
| 2026-03-12 | 노션: 사주 가설 리포트 + 엔진 재설계 제안서 |

---

## 📌 메모

- 사주 가설 폐기 (2026-03-12): p=0.575, CV R²=-0.222
- 추천 적중률 74.8% = 설문의 힘 (사주 제거 시 78~80% 기대)
- 50명 milestone 도달 완료 (60명, 피드백 210건)
- 다음 milestone: 200명 (ML 전환 가능)
