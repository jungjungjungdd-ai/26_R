# 실시간 시연 API 명세 (LIVE-01 ~ LIVE-04)

시연 대본(`data/sample/live_script.json`)의 단계를 하나씩 DB에 넣고 **재분석**한 뒤, 이전 결과와 비교해 바뀐 점을 `events`에 기록한다.
서버에는 타이머가 없다. 프론트가 몇 초마다 `step`을 호출한다.

공통: 모든 경로 앞에 `/api`. 에러 형식은 기존과 같다 `{"error": {"code","message","detail"}}`.
선행 조건: 해당 run 이 **분석 완료(`status = done`)** 상태여야 한다. 아니면 409 `NOT_ANALYZED`.

---

## LIVE-01  다음 단계 실행
`POST /api/runs/{run_id}/live/step`

대본의 다음 단계 로그를 원본 테이블에 추가(save_raw) → 재분석 → 전후 비교 → events 기록.

응답 200
```json
{
  "run_id": "R20261031-01",
  "step": 1, "total": 4, "finished": false,
  "last_title": "Zapier로 고객 연락처 전송",
  "next_title": "이미지 생성 AI가 사내 문서 접근 권한 획득",
  "title": "Zapier로 고객 연락처 전송",
  "changed": true,
  "rows_added": 1,
  "findings": 5,
  "events": [
    {"event_id": 1, "step": 1, "created_at": "2026-10-31 10:00:01.123", "type": "score_up",
     "finding_id": "R20261031-01-F003", "message": "점수 상승: 박마케팅 → Zapier AI → 사내 메일 50점 → 70점", "detail": {}},
    {"event_id": 2, "step": 1, "created_at": "2026-10-31 10:00:01.123", "type": "new_payload_hit",
     "finding_id": "R20261031-01-F003", "message": "새 민감정보 검출: 전화번호 2건 (로그 N0007)", "detail": {}}
  ]
}
```
- 이미 마지막 단계면 변화 없이 `finished: true, changed: false, events: []` (에러 아님).
- 분석 중 오류가 나면 이번 단계에서 추가한 행을 지우고 단계를 올리지 않는다. 같은 단계를 다시 누르면 된다.

## LIVE-02  진행 상태
`GET /api/runs/{run_id}/live/status`

```json
{"run_id": "R20261031-01", "step": 2, "total": 4, "finished": false,
 "last_title": "...", "next_title": "..."}
```

## LIVE-03  처음으로 되돌리기 (리허설용)
`POST /api/runs/{run_id}/live/reset`

대본이 추가한 행, events, 진행 단계를 지우고 다시 분석한다. 응답은 LIVE-02 형식(`step: 0`).
다시 step을 누르면 처음과 같은 결과가 나온다.
※ 시연 중에 누른 "회수/조치 적용" 상태도 함께 처음(open)으로 돌아간다.

## LIVE-04  변화 목록
`GET /api/runs/{run_id}/events?since=2026-10-31 10:00:01.123&after_id=7`

| 파라미터 | 설명 |
|---|---|
| `since` | `YYYY-MM-DD HH:MM:SS` 또는 밀리초까지. 이 시각 **이후**만. 형식이 틀리면 422 |
| `after_id` | 이 `event_id` 이후만. 폴링에는 이쪽이 더 안전(같은 시각 이벤트 누락 없음) |

응답: 이벤트 배열(오래된 순). 각 항목 `{event_id, step, created_at, type, finding_id, message, detail}`

| type | 뜻 |
|---|---|
| `new_finding` | 새 위험 경로 생김 |
| `score_up` | 기존 경로 점수 상승 |
| `new_payload_hit` | 새 민감정보 검출 (종류별 건수) |

## 에러
| 상황 | 코드 |
|---|---|
| run 없음 | 404 NOT_FOUND |
| 분석 전 | 409 NOT_ANALYZED |
| 대본 파일 없음/형식 오류 | 500 INTERNAL_ERROR |
| 대본 행의 ID 누락/중복 | 400 INVALID_FILE |
| `since` 형식 오류 | 422 (FastAPI 기본) |

## 대본 형식 `live_script.json`
```json
{"name": "...", "description": "...",
 "steps": [{"title": "...", "description": "...",
            "rows": {"network_logs": [{"log_id": "N0007", "...": "..."}],
                     "oauth_grants": [{"grant_id": "G0005", "...": "..."}]}}]}
```
- `rows` 의 테이블 이름·열은 업로드 파일 7개와 같다. 행 ID는 기존 데이터와 겹치면 안 된다.
- 경로는 환경변수 `LIVE_SCRIPT_PATH` 로 바꿀 수 있다.

## 새 DB 테이블
`live_state`(진행 단계), `live_applied`(대본이 넣은 행 — reset 때 이것만 삭제), `events`(변화 기록)

## 프론트 함수 예시
`live_step(run_id)`, `live_status(run_id)`, `live_reset(run_id)`, `get_events(run_id, after_id)`

## 주의
- 재분석 때 finding_id 번호(`F001`…)가 바뀔 수 있다. 경로는 (직원, 도구, 자산)으로 맞춰 비교하며, `events.detail` 에도 이 값이 들어간다.
- 시연 중 회수/조치 상태는 step을 눌러도 유지된다. reset 하면 초기화된다.
