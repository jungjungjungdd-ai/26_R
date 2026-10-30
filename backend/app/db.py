import sqlite3
from pathlib import Path

import pandas as pd

from .config import DB_PATH

SCHEMA = Path(__file__).with_name("schema.sql")

# 원본 테이블과 각 테이블의 행 ID 열
RAW_TABLES = {
    "employees": "employee_id",
    "assets": "asset_id",
    "ai_tools": "tool_id",
    "network_logs": "log_id",
    "oauth_grants": "grant_id",
    "asset_activities": "activity_id",
    "processes": "proc_id",
}


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))


def save_raw(conn: sqlite3.Connection, run_id: str, table: str, df: pd.DataFrame) -> None:
    """원본 테이블에 run_id를 붙여 추가 저장."""
    df = df.copy()
    df.insert(0, "run_id", run_id)
    df.to_sql(table, conn, if_exists="append", index=False)


def read_raw(conn: sqlite3.Connection, run_id: str, table: str) -> pd.DataFrame:
    """특정 run의 원본 테이블을 DataFrame으로 읽기 (run_id 열은 빼고)."""
    df = pd.read_sql_query(f"SELECT * FROM {table} WHERE run_id = ?", conn, params=(run_id,))
    return df.drop(columns=["run_id"])
