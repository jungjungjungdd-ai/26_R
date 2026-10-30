"""여러 라우터가 같이 쓰는 함수"""
import sqlite3

from ..errors import ApiError


def get_run(conn: sqlite3.Connection, run_id: str, need_done: bool = True) -> sqlite3.Row:
    run = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if run is None:
        raise ApiError(404, "NOT_FOUND", "분석 작업이 없습니다", {"run_id": run_id})
    if need_done and run["status"] != "done":
        raise ApiError(409, "NOT_ANALYZED", "아직 분석하지 않았습니다", {"run_id": run_id})
    return run


def finding_to_dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    """findings 한 줄을 API명세서 RUN-04 형식으로 바꾼다."""
    run_id = row["run_id"]
    emp = conn.execute("SELECT * FROM employees WHERE run_id = ? AND employee_id = ?",
                       (run_id, row["employee_id"])).fetchone()
    tool = conn.execute("SELECT * FROM ai_tools WHERE run_id = ? AND tool_id = ?",
                        (run_id, row["tool_id"])).fetchone()
    asset = conn.execute("SELECT * FROM assets WHERE run_id = ? AND asset_id = ?",
                         (run_id, row["asset_id"])).fetchone()
    return {
        "finding_id": row["finding_id"],
        "employee": {"id": row["employee_id"], "name": emp["name"] if emp else None,
                     "status": emp["status"] if emp else None},
        "tool": {"id": row["tool_id"], "name": tool["name"] if tool else row["tool_id"],
                 "approved": bool(tool["approved"]) if tool else False},
        "asset": {"id": row["asset_id"], "name": asset["name"] if asset else row["asset_id"],
                  "sensitivity": asset["sensitivity"] if asset else None},
        "scopes": [s for s in row["scopes"].split(",") if s],
        "score": row["score"],
        "level": row["level"],
        "status": row["status"],
    }


def get_finding_row(conn: sqlite3.Connection, finding_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM findings WHERE finding_id = ?", (finding_id,)).fetchone()
    if row is None:
        raise ApiError(404, "NOT_FOUND", "경로가 없습니다", {"finding_id": finding_id})
    return row
