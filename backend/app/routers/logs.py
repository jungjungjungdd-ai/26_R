"""Log 도메인: LOG-01 (담당: 탐지)"""
from fastapi import APIRouter

from ..db import RAW_TABLES, connect
from ..errors import ApiError

router = APIRouter(prefix="/logs", tags=["Log"])


@router.get("/{table}/{row_id}")
def get_log(table: str, row_id: str, run_id: str | None = None):
    """LOG-01 근거 원본 로그 한 줄. run_id 를 안 주면 가장 최근 분석의 행."""
    if table not in RAW_TABLES:
        raise ApiError(404, "NOT_FOUND", "없는 테이블입니다", {"table": table})
    id_col = RAW_TABLES[table]
    sql = f"SELECT * FROM {table} WHERE {id_col} = ?"
    params: tuple = (row_id,)
    if run_id:
        sql += " AND run_id = ?"
        params += (run_id,)
    with connect() as conn:
        row = conn.execute(sql + " ORDER BY rowid DESC LIMIT 1", params).fetchone()
    if row is None:
        raise ApiError(404, "NOT_FOUND", "로그가 없습니다", {"table": table, "row_id": row_id})
    data = dict(row)
    data.pop("run_id", None)
    return {"table": table, "row": data}
