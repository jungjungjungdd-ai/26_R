"""Live 도메인: LIVE-01 ~ LIVE-04 (담당: 테크 리드)

시연할 때 "로그가 실시간으로 들어오는 것처럼" 보여 주기 위한 API입니다.
대본(JSON)에 적힌 로그를 단계마다 하나씩 DB에 추가하고 다시 분석해서,
위험 경로가 새로 생기거나 점수가 오르는 변화를 events 테이블에 기록합니다.

- 백그라운드 타이머는 없습니다. 프론트가 몇 초마다 LIVE-01(step)을 호출합니다.
- 대본 형식은 data/sample/live_script.json 을 보세요.
- 대본 위치는 환경변수 LIVE_SCRIPT_PATH 로 바꿀 수 있습니다. (app/config.py)
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Query

from .. import config
from ..db import RAW_TABLES, connect, read_raw, save_raw
from ..engine import detector, loader, pipeline
from ..errors import ApiError
from .common import finding_to_dict, get_run

router = APIRouter(prefix="/runs", tags=["Live"])

SCRIPT_NAME = "live_script.json"

# events.type 값
BLOCKED = "blocked"                  # 회수된 경로라서 이번 단계 로그를 넣지 않음
NEW_FINDING = "new_finding"          # 새 위험 경로가 생김
SCORE_UP = "score_up"                # 기존 경로의 점수가 올라감
NEW_PAYLOAD_HIT = "new_payload_hit"  # 새 민감정보가 검출됨


# ---------------------------------------------------------------- 대본 읽기
def load_script() -> list[dict]:
    """대본 파일의 steps 목록을 읽는다. 매번 읽으므로 서버를 켠 채로 대본을 고쳐도 반영된다."""
    path = Path(config.LIVE_SCRIPT_PATH)
    try:
        steps = json.loads(path.read_text(encoding="utf-8-sig"))["steps"]
    except FileNotFoundError:
        raise ApiError(500, "INTERNAL_ERROR", "시연 대본 파일이 없습니다", {"file": str(path)})
    except (ValueError, KeyError, TypeError):
        raise ApiError(500, "INTERNAL_ERROR", "시연 대본 형식이 올바르지 않습니다", {"file": str(path)})
    if not isinstance(steps, list) or not steps or not all(isinstance(s, dict) for s in steps):
        raise ApiError(500, "INTERNAL_ERROR", "시연 대본에 steps 가 비어 있습니다", {"file": str(path)})
    return steps


def step_title(steps: list[dict], index: int) -> str:
    return str(steps[index].get("title") or f"{index + 1}단계")


# ---------------------------------------------------------------- 진행 상태
def get_step(conn: sqlite3.Connection, run_id: str) -> int:
    """지금까지 진행한 단계 수 (아직 시작하지 않았으면 0)"""
    row = conn.execute("SELECT step FROM live_state WHERE run_id = ?", (run_id,)).fetchone()
    return row["step"] if row else 0


def status_dict(run_id: str, step: int, steps: list[dict]) -> dict:
    total = len(steps)
    return {
        "run_id": run_id,
        "step": step,
        "total": total,
        "finished": step >= total,
        "last_title": step_title(steps, step - 1) if step > 0 else None,
        "next_title": step_title(steps, step) if step < total else None,
    }


# ---------------------------------------------------------------- 로그 추가
def _frame(table: str, rows: object) -> pd.DataFrame:
    """대본의 한 테이블 분량(dict 목록)을 업로드 파일과 같은 방식으로 DataFrame 으로 만든다."""
    id_col = RAW_TABLES[table]
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ApiError(400, "INVALID_FILE", f"대본의 {table}은 행 목록이어야 합니다", {"file": SCRIPT_NAME})
    if any(not str(r.get(id_col, "")).strip() for r in rows):
        # 자동 ID(N0001 …)를 쓰면 기존 행과 겹치므로 대본에는 ID를 꼭 적어야 한다
        raise ApiError(400, "INVALID_FILE", f"대본의 {table}에 {id_col}이 없는 행이 있습니다",
                       {"file": SCRIPT_NAME, "column": id_col})
    if table == "ai_tools":
        df = loader.read_file(table, SCRIPT_NAME, json.dumps(rows, ensure_ascii=False).encode("utf-8"))
    else:
        df = pd.DataFrame(rows).fillna("").astype(str)
    return loader.validate(table, SCRIPT_NAME, df)


def apply_rows(conn: sqlite3.Connection, run_id: str, step_no: int, spec: dict) -> int:
    """이번 단계의 로그를 원본 테이블에 추가하고(save_raw), 되돌릴 수 있게 live_applied 에 기록한다."""
    added = 0
    for table, rows in (spec.get("rows") or {}).items():
        if table not in RAW_TABLES:
            raise ApiError(400, "INVALID_FILE", f"대본에 알 수 없는 테이블이 있습니다: {table}",
                           {"file": SCRIPT_NAME, "table": table})
        if not rows:
            continue
        id_col = RAW_TABLES[table]  # 테이블·열 이름은 RAW_TABLES 에 있는 값만 SQL 에 넣는다
        df = _frame(table, rows)
        ids = [str(v) for v in df[id_col]]
        if len(set(ids)) != len(ids):
            raise ApiError(400, "INVALID_FILE", f"대본의 {table}에 같은 ID가 두 번 있습니다",
                           {"file": SCRIPT_NAME, "table": table})
        for row_id in ids:
            if conn.execute(f"SELECT 1 FROM {table} WHERE run_id = ? AND {id_col} = ?",
                            (run_id, row_id)).fetchone():
                raise ApiError(400, "INVALID_FILE", f"{table}에 이미 있는 ID입니다: {row_id}",
                               {"file": SCRIPT_NAME, "table": table, "row_id": row_id})
        # 업로드한 테이블의 열에 맞춘다 (대본에 없는 열은 빈 값, 모르는 열은 버림)
        columns = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})") if r["name"] != "run_id"]
        save_raw(conn, run_id, table, df.reindex(columns=columns))
        conn.executemany("INSERT INTO live_applied (run_id, step, table_name, row_id) VALUES (?, ?, ?, ?)",
                         [(run_id, step_no, table, i) for i in ids])
        added += len(ids)
    return added


def delete_applied(conn: sqlite3.Connection, run_id: str, step_no: int | None = None) -> None:
    """대본이 추가했던 로그를 지운다. step_no 를 주면 그 단계 것만, 없으면 전부."""
    sql, params = "SELECT table_name, row_id FROM live_applied WHERE run_id = ?", [run_id]
    if step_no is not None:
        sql, params = sql + " AND step = ?", params + [step_no]
    for r in conn.execute(sql, params).fetchall():
        conn.execute(f"DELETE FROM {r['table_name']} WHERE run_id = ? AND {RAW_TABLES[r['table_name']]} = ?",
                     (run_id, r["row_id"]))
    conn.execute(sql.replace("SELECT table_name, row_id", "DELETE"), params)


# ---------------------------------------------------------------- 재분석 전후 비교
def _key(row: sqlite3.Row) -> tuple[str, str, str]:
    """경로를 가리키는 값. finding_id 는 재분석할 때마다 번호가 바뀔 수 있어서 이걸로 같은 경로를 찾는다."""
    return (row["employee_id"] or "", row["tool_id"], row["asset_id"])


def snapshot(conn: sqlite3.Connection, run_id: str) -> tuple[dict, dict]:
    """지금의 경로(키 → RUN-04 항목)와 민감정보 검출(키 → finding_id)"""
    findings = {_key(r): finding_to_dict(conn, r)
                for r in conn.execute("SELECT * FROM findings WHERE run_id = ?", (run_id,))}
    hits = {(h["log_id"], h["type"], h["start_pos"], h["end_pos"]): h["finding_id"]
            for h in conn.execute("SELECT * FROM payload_hits WHERE run_id = ?", (run_id,))}
    return findings, hits


def restore_status(conn: sqlite3.Connection, run_id: str, before: dict) -> None:
    """재분석은 경로를 새로 만들어 상태가 open 으로 돌아가므로, 회수·조치된 경로는 이전 상태를 되살린다."""
    for (emp, tool, asset), old in before.items():
        if old["status"] == "open":
            continue
        where = "run_id = ? AND employee_id = ? AND tool_id = ? AND asset_id = ?"
        if old["status"] == "mitigated":  # 조치 적용은 점수도 바꾸므로 점수도 되살린다
            conn.execute(f"UPDATE findings SET status = ?, score = ? WHERE {where}",
                         (old["status"], old["score"], run_id, emp, tool, asset))
        else:
            conn.execute(f"UPDATE findings SET status = ? WHERE {where}", (old["status"], run_id, emp, tool, asset))


def _label(item: dict) -> str:
    emp = item["employee"]["name"] or item["employee"]["id"] or "알 수 없는 직원"
    return f"{emp} → {item['tool']['name']} → {item['asset']['name']}"


def record_events(conn: sqlite3.Connection, run_id: str, step_no: int,
                  before: tuple[dict, dict], after: tuple[dict, dict]) -> list[dict]:
    """재분석 전후를 비교해서 새 경로, 점수 상승, 새 민감정보를 events 테이블에 기록한다."""
    (before_f, before_h), (after_f, after_h) = before, after
    pending = []  # (type, finding_id, message, detail)

    for key in sorted(after_f):
        item, old = after_f[key], before_f.get(key)
        ids = {"employee_id": key[0], "tool_id": key[1], "asset_id": key[2]}
        if old is None:
            pending.append((NEW_FINDING, item["finding_id"],
                            f"새 위험 경로: {_label(item)} ({item['score']}점, {item['level']})",
                            {**ids, "score": item["score"], "level": item["level"]}))
        elif item["score"] > old["score"]:
            pending.append((SCORE_UP, item["finding_id"],
                            f"점수 상승: {_label(item)} {old['score']}점 → {item['score']}점",
                            {**ids, "score_before": old["score"], "score_after": item["score"],
                             "level_before": old["level"], "level_after": item["level"]}))

    groups: dict[tuple[str, str], dict] = {}  # (로그, 종류) → 새로 걸린 개수
    for hit_key in sorted(set(after_h) - set(before_h)):
        g = groups.setdefault((hit_key[0], hit_key[1]), {"count": 0, "finding_id": after_h[hit_key]})
        g["count"] += 1
    for (log_id, kind), g in groups.items():
        pending.append((NEW_PAYLOAD_HIT, g["finding_id"], f"새 민감정보 검출: {kind} {g['count']}건 (로그 {log_id})",
                        {"log_id": log_id, "hit_type": kind, "count": g["count"]}))

    created_at = now()
    events = []
    for kind, finding_id, message, detail in pending:
        cur = conn.execute(
            "INSERT INTO events (run_id, step, created_at, type, finding_id, message, detail) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, step_no, created_at, kind, finding_id, message, json.dumps(detail, ensure_ascii=False)))
        events.append({"event_id": cur.lastrowid, "step": step_no, "created_at": created_at, "type": kind,
                       "finding_id": finding_id, "message": message, "detail": detail})
    return events


# ---------------------------------------------------------------- 회수된 경로 차단
BLOCK_NOUN = {"network_logs": "전송 로그", "oauth_grants": "권한 부여", "processes": "프로세스 실행"}


def row_owner_tool(table: str, row: dict, domain_map: dict, process_map: dict) -> tuple[str, str] | None:
    """대본 행 하나가 (직원, 도구) 중 누구 것인지. 알 수 없으면 None (그 행은 차단 대상이 아니다)."""
    emp = str(row.get("employee_id", "")).strip()
    if table == "network_logs":
        tool = domain_map.get(str(row.get("domain", "")).strip().lower())
    elif table == "oauth_grants":
        tool = str(row.get("tool_id", "")).strip() or None
    elif table == "processes":
        tool = process_map.get(str(row.get("process_name", "")).strip())
    else:
        return None
    return (emp, tool) if emp and tool else None


def drop_revoked(conn: sqlite3.Connection, run_id: str, spec: dict) -> tuple[dict, list[dict]]:
    """회수(revoked)된 직원+도구 조합의 행은 빼고 나머지만 돌려준다. 뺀 행은 두 번째 값으로 알려 준다."""
    revoked = {(r["employee_id"] or "", r["tool_id"]) for r in conn.execute(
        "SELECT employee_id, tool_id FROM findings WHERE run_id = ? AND status = 'revoked'", (run_id,))}
    rows = spec.get("rows") or {}
    if not revoked or not rows:
        return spec, []
    domain_map, process_map = detector.build_lookup(read_raw(conn, run_id, "ai_tools"))
    kept, blocked = {}, []
    for table, items in rows.items():
        if table not in RAW_TABLES or not isinstance(items, list):
            kept[table] = items  # 형식 오류는 apply_rows 가 알려 준다
            continue
        id_col = RAW_TABLES[table]
        kept[table] = []
        for row in items:
            owner = row_owner_tool(table, row, domain_map, process_map) if isinstance(row, dict) else None
            if owner in revoked:
                blocked.append({"table": table, "row_id": str(row.get(id_col, "")),
                                "employee_id": owner[0], "tool_id": owner[1]})
            else:
                kept[table].append(row)
    return {**spec, "rows": kept}, blocked


def record_blocked(conn: sqlite3.Connection, run_id: str, step_no: int, blocked: list[dict],
                   after: dict) -> list[dict]:
    """건너뛴 행을 '회수로 차단됨' 이벤트로 남긴다. after 는 재분석 뒤의 경로(snapshot 의 첫 번째 값)."""
    created_at = now()
    events = []
    for b in blocked:
        match = [item for key, item in sorted(after.items())
                 if key[0] == b["employee_id"] and key[1] == b["tool_id"] and item["status"] == "revoked"]
        item = match[0] if match else None
        emp = (item["employee"]["name"] if item else None) or b["employee_id"]
        tool = item["tool"]["name"] if item else b["tool_id"]
        message = f"회수로 차단됨: {emp} → {tool} {BLOCK_NOUN.get(b['table'], '로그')} {b['row_id']} 추가 안 함"
        finding_id = item["finding_id"] if item else None
        cur = conn.execute(
            "INSERT INTO events (run_id, step, created_at, type, finding_id, message, detail) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, step_no, created_at, BLOCKED, finding_id, message, json.dumps(b, ensure_ascii=False)))
        events.append({"event_id": cur.lastrowid, "step": step_no, "created_at": created_at, "type": BLOCKED,
                       "finding_id": finding_id, "message": message, "detail": b})
    return events


def now() -> str:
    """밀리초까지 적는다. 같은 초 안에 생긴 이벤트도 since 로 구분하기 위해서다."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# ---------------------------------------------------------------- API
@router.post("/{run_id}/live/step")
def live_step(run_id: str):
    """LIVE-01 대본의 다음 단계 로그를 추가하고 재분석한다. 끝난 뒤에 불러도 아무 일 없이 finished 를 돌려준다."""
    steps = load_script()
    with connect() as conn:
        get_run(conn, run_id)  # 먼저 분석(RUN-02)이 끝나 있어야 변화를 비교할 수 있다
        step = get_step(conn, run_id)
        if step >= len(steps):
            count = conn.execute("SELECT COUNT(*) FROM findings WHERE run_id = ?", (run_id,)).fetchone()[0]
            return {**status_dict(run_id, step, steps), "title": None, "changed": False, "rows_added": 0,
                    "rows_blocked": 0, "findings": count, "events": []}

        step_no = step + 1
        before = snapshot(conn, run_id)
        spec, blocked = drop_revoked(conn, run_id, steps[step])  # 회수된 경로의 로그는 넣지 않는다
        try:
            rows_added = apply_rows(conn, run_id, step_no, spec)
            conn.commit()  # 추가한 로그와 live_applied 기록을 먼저 확정해 둔다 (실패했을 때 지우기 위해)
            count = pipeline.run_analysis(conn, run_id)
        except Exception:
            # 중간에 실패하면 분석 중이던 변경은 취소하고, 이번 단계에서 넣은 로그를 지워서
            # 같은 단계를 다시 누를 수 있게 한다
            conn.rollback()
            delete_applied(conn, run_id, step_no)
            conn.commit()
            raise
        restore_status(conn, run_id, before[0])
        after = snapshot(conn, run_id)
        events = record_events(conn, run_id, step_no, before, after)
        events += record_blocked(conn, run_id, step_no, blocked, after[0])
        conn.execute(
            "INSERT INTO live_state (run_id, step, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(run_id) DO UPDATE SET step = excluded.step, updated_at = excluded.updated_at",
            (run_id, step_no, now()))
    return {**status_dict(run_id, step_no, steps), "title": step_title(steps, step), "changed": bool(events),
            "rows_added": rows_added, "rows_blocked": len(blocked), "findings": count,
            "events": events}


@router.get("/{run_id}/live/status")
def live_status(run_id: str):
    """LIVE-02 현재 단계, 전체 단계 수, 끝났는지"""
    steps = load_script()
    with connect() as conn:
        get_run(conn, run_id, need_done=False)
        step = get_step(conn, run_id)
    return status_dict(run_id, step, steps)


@router.post("/{run_id}/live/reset")
def live_reset(run_id: str):
    """LIVE-03 처음 상태로 되돌린다 (리허설용). 추가했던 로그, 이벤트, 진행 단계를 지우고 다시 분석한다."""
    steps = load_script()
    with connect() as conn:
        run = get_run(conn, run_id, need_done=False)
        delete_applied(conn, run_id)
        conn.execute("DELETE FROM events WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM live_state WHERE run_id = ?", (run_id,))
        if run["status"] == "done":
            pipeline.run_analysis(conn, run_id)  # 회수·조치 상태도 함께 처음으로 돌아간다
    return status_dict(run_id, 0, steps)


@router.get("/{run_id}/events")
def live_events(
    run_id: str,
    since: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d{1,6})?$"),
    after_id: int | None = None,
):
    """LIVE-04 새 위험 경로, 점수 상승, 새 민감정보 검출 목록 (오래된 것부터)

    since: 이 시각보다 나중에 생긴 이벤트만 (예: 2026-10-31 10:00:00)
    after_id: 이 event_id 보다 큰 이벤트만. 같은 시각에 생긴 이벤트를 놓치거나 두 번 받지 않으려면 이쪽을 쓰세요.
    """
    with connect() as conn:
        get_run(conn, run_id, need_done=False)
        sql, params = "SELECT * FROM events WHERE run_id = ?", [run_id]
        if since:
            sql, params = sql + " AND created_at > ?", params + [since]
        if after_id is not None:
            sql, params = sql + " AND event_id > ?", params + [after_id]
        rows = conn.execute(sql + " ORDER BY event_id", params).fetchall()
    return [{"event_id": r["event_id"], "step": r["step"], "created_at": r["created_at"], "type": r["type"],
             "finding_id": r["finding_id"], "message": r["message"], "detail": json.loads(r["detail"])}
            for r in rows]
