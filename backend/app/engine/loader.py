"""F-01, F-02 로그 파일 검증과 읽기 (담당: 테크 리드)

업로드된 파일 7개를 DataFrame으로 읽고, 필수 열이 다 있는지 검사합니다.
행 ID 열(log_id 등)이 없으면 자동으로 만들어 줍니다.
"""
import io
import json

import pandas as pd

from ..errors import ApiError

# 파일별 필수 열 (데이터 형식 약속)
REQUIRED_COLUMNS = {
    "employees": ["employee_id", "name", "dept", "status"],
    "assets": ["asset_id", "name", "type", "sensitivity"],
    "ai_tools": ["tool_id", "name", "category", "approved", "domains", "process_names"],
    "network_logs": ["timestamp", "employee_id", "domain", "bytes_out", "payload_sample"],
    "oauth_grants": ["timestamp", "employee_id", "tool_id", "asset_id", "scope"],
    "asset_activities": ["timestamp", "tool_id", "asset_id", "action", "record_count"],
    "processes": ["timestamp", "employee_id", "host", "process_name", "connected_asset_id"],
}

# 행 ID가 없으면 자동으로 만들 테이블: (ID 열, 접두어)
AUTO_IDS = {
    "network_logs": ("log_id", "N"),
    "oauth_grants": ("grant_id", "G"),
    "asset_activities": ("activity_id", "AC"),
    "processes": ("proc_id", "P"),
}


def read_file(name: str, filename: str, content: bytes) -> pd.DataFrame:
    """업로드된 파일 하나를 DataFrame으로 읽는다. ai_tools는 JSON, 나머지는 CSV."""
    try:
        if name == "ai_tools":
            items = json.loads(content.decode("utf-8-sig"))
            df = pd.DataFrame(items)
            # 리스트 열은 DB에 넣기 위해 JSON 문자열로 저장
            for col in ("domains", "process_names"):
                if col in df.columns:
                    df[col] = df[col].apply(lambda v: json.dumps(v or [], ensure_ascii=False))
            if "approved" in df.columns:
                df["approved"] = df["approved"].astype(bool).astype(int)
        else:
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    except Exception as e:
        raise ApiError(400, "INVALID_FILE", f"{filename}을(를) 읽을 수 없습니다: {e}", {"file": filename})
    return df


def validate(name: str, filename: str, df: pd.DataFrame) -> pd.DataFrame:
    """필수 열 검사, 숫자 열 변환, 행 ID 자동 생성."""
    missing = [c for c in REQUIRED_COLUMNS[name] if c not in df.columns]
    if missing:
        raise ApiError(
            400, "INVALID_FILE", f"{filename}에 {', '.join(missing)} 열이 없습니다",
            {"file": filename, "column": missing[0]},
        )
    df = df.copy()
    if name in AUTO_IDS:
        id_col, prefix = AUTO_IDS[name]
        if id_col not in df.columns or (df[id_col] == "").all():
            df[id_col] = [f"{prefix}{i:04d}" for i in range(1, len(df) + 1)]
        df = df[[id_col] + [c for c in df.columns if c != id_col]]
    for col in ("bytes_out", "record_count"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df
