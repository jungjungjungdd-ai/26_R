-- 분석 결과 테이블 (원본 테이블 7개는 업로드할 때 pandas가 자동으로 만듦)
CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL,          -- uploaded / done
    rows_json   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    finding_id   TEXT PRIMARY KEY,
    run_id       TEXT NOT NULL REFERENCES runs(run_id),
    employee_id  TEXT,
    tool_id      TEXT NOT NULL,
    asset_id     TEXT NOT NULL,
    scopes       TEXT NOT NULL,         -- "read,send"
    score        INTEGER NOT NULL,
    level        TEXT NOT NULL,         -- 위험 / 주의 / 낮음
    status       TEXT NOT NULL DEFAULT 'open'   -- open / revoked / mitigated
);

-- 경로 번호 고정용 표. 같은 (직원, 도구, 자산) 경로는 재분석해도 같은 F 번호를 쓴다.
CREATE TABLE IF NOT EXISTS finding_ids (
    run_id       TEXT NOT NULL,
    employee_id  TEXT NOT NULL,         -- 직원이 없으면 '' 로 저장 (PK 에 NULL 이 들어가지 않게)
    tool_id      TEXT NOT NULL,
    asset_id     TEXT NOT NULL,
    seq          INTEGER NOT NULL,      -- F001 의 1
    PRIMARY KEY (run_id, employee_id, tool_id, asset_id)
);

CREATE TABLE IF NOT EXISTS finding_reasons (
    reason_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id    TEXT NOT NULL REFERENCES findings(finding_id),
    rule_code     TEXT NOT NULL,
    points        INTEGER NOT NULL,
    description   TEXT NOT NULL,
    source_table  TEXT,
    source_id     TEXT
);

CREATE TABLE IF NOT EXISTS payload_hits (
    hit_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    finding_id  TEXT,
    log_id      TEXT NOT NULL,
    type        TEXT NOT NULL,
    start_pos   INTEGER NOT NULL,
    end_pos     INTEGER NOT NULL
);

-- 실시간 시연 (LIVE-01~04)
-- 대본을 몇 단계까지 진행했는지
CREATE TABLE IF NOT EXISTS live_state (
    run_id      TEXT PRIMARY KEY REFERENCES runs(run_id),
    step        INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT NOT NULL
);

-- 대본이 원본 테이블에 추가한 행 (reset 할 때 이 행들만 지움)
CREATE TABLE IF NOT EXISTS live_applied (
    run_id      TEXT NOT NULL,
    step        INTEGER NOT NULL,
    table_name  TEXT NOT NULL,
    row_id      TEXT NOT NULL,
    PRIMARY KEY (run_id, table_name, row_id)
);

-- 재분석 전후를 비교해 찾은 변화
CREATE TABLE IF NOT EXISTS events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    step        INTEGER NOT NULL,
    created_at  TEXT NOT NULL,          -- 2026-10-31 10:00:00.123 (밀리초까지)
    type        TEXT NOT NULL,          -- new_finding / score_up / new_payload_hit
    finding_id  TEXT,
    message     TEXT NOT NULL,
    detail      TEXT NOT NULL DEFAULT '{}'   -- JSON
);

CREATE TABLE IF NOT EXISTS recommendations (
    rec_id          TEXT NOT NULL,
    finding_id      TEXT NOT NULL REFERENCES findings(finding_id),
    action          TEXT NOT NULL,
    description     TEXT NOT NULL,
    expected_score  INTEGER NOT NULL,
    applied         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (rec_id, finding_id)
);
