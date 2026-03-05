# SAJU - 사주 기반 취향 분석 서비스

사주팔자(생년월일시)와 간단한 설문으로 8가지 도메인의 취향을 분석해드립니다.

🌐 서비스 URL: https://flavor.arkedia.work

## 도메인
커피 · 향수 · 음악 · 식당 · 운동 · 여행 · 패션 · 인테리어

## 실행

```bash
pip install -r requirements.txt
DB_PATH=/var/data/saju_submissions.db python app.py
```

## 배포 (gunicorn)

```bash
DB_PATH=/var/data/saju_submissions.db DEBUG=false \
  gunicorn app:app --bind 0.0.0.0:8000 --workers 2 --daemon
```

## API

| 엔드포인트 | 메서드 | 설명 |
|---|---|---|
| `/api/submit` | POST | 설문 제출 → 결과 반환 |
| `/result/<id>` | GET | 결과 조회 |
| `/api/results` | GET | 전체 제출 목록 |
| `/health` | GET | 헬스체크 |
