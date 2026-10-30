# 백엔드 (FastAPI)

## 실행

저장소 맨 위에서 가상환경을 켠 뒤:

```powershell
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

- API 문서: http://localhost:8000/docs (여기서 파일 업로드와 분석을 직접 눌러 볼 수 있음)
- 상태 확인: http://localhost:8000/api/health

## 폴더 구조

```
backend/
├── app/
│   ├── main.py            서버 시작, 라우터 등록
│   ├── config.py          DB 위치 (환경변수 DB_PATH)
│   ├── db.py              SQLite 연결, 원본 테이블 저장·읽기
│   ├── schema.sql         분석 결과 테이블 5개
│   ├── errors.py          API명세서 에러 형식
│   ├── routers/           도메인별 API
│   │   ├── system.py      SYS-01
│   │   ├── runs.py        RUN-01 ~ RUN-06
│   │   ├── findings.py    FND-01 ~ FND-05
│   │   └── logs.py        LOG-01
│   └── engine/            분석 파이프라인
│       ├── loader.py          검증·적재          (완성)
│       ├── detector.py        AI 도구 탐지        TODO 탐지 담당
│       ├── payload_scanner.py 전송 내용 스캔      TODO 탐지 담당
│       ├── correlator.py      상관분석·경로 생성  TODO 위험도 담당  [핵심]
│       ├── scorer.py          위험도·근거         TODO 위험도 담당  [핵심]
│       ├── recommender.py     조치 추천 (선택)    TODO 위험도 담당
│       └── pipeline.py        단계 연결·저장      (완성, 고치지 않음)
└── tests/                 담당자별 완료 기준 테스트
```

## 담당자 작업 방법

1. 자기 파일을 열고 `TODO(담당)` 주석과 함수 설명(입력·출력 예시)을 읽습니다.
2. 함수를 채운 뒤 자기 테스트를 돌립니다. **모두 통과하면 완료**입니다.

| 담당 | 파일 | 완료 기준 |
| --- | --- | --- |
| 탐지 | `engine/detector.py` | `pytest tests/test_detector.py` |
| 탐지 | `engine/payload_scanner.py` | `pytest tests/test_payload_scanner.py` |
| 위험도 | `engine/scorer.py` | `pytest tests/test_scorer.py` |
| 위험도 | `engine/correlator.py` | `pytest tests/test_correlator.py` (detector, scanner 완성 후) |
| 전체 | 4개 모두 | `pytest` 전부 통과 = 시연 사례 점수가 기대값대로 나옴 |

- 아직 구현 안 된 부분을 빼고 기본 동작만 확인: `pytest -m "not todo"`
- 엔진 함수끼리 주고받는 데이터 형식(`USAGE_COLUMNS`, `HIT_COLUMNS`, `PATH_KEYS`)은 팀 약속이라 바꾸면 안 됩니다. 바꿔야 하면 테크 리드와 먼저 이야기하세요.

## 샘플 데이터

`data/sample/`에 시연용 숨긴 사례 4개 + 승인 도구 1개가 들어간 작은 데이터가 있습니다. 데이터 담당은 같은 형식으로 행을 늘리면 됩니다.

| 경로 | 기대 점수 |
| --- | --- |
| 김영업(퇴사) → n8n → CRM 고객 정보 | 95 위험 |
| 이개발 → MCP(postgres) → 고객 DB | 70 위험 |
| 박마케팅 → Zapier AI → 사내 메일 | 50 주의 |
| 최디자인 → 이미지 생성 AI → 홍보 폴더 | 25 낮음 |
| 정회계 → ChatGPT Enterprise(승인) → 사내 문서 | 30 낮음 |
