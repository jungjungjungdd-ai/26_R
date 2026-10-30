"""F-07 ~ F-09 로그 상관분석으로 접근 경로 만들기 (담당: 위험도)  [핵심]

할 일: build_paths 를 완성하세요.
완료 기준: `pytest tests/test_correlator.py` 통과
"""
import pandas as pd

# scorer 에 넘겨줄 경로 한 줄의 형식 (팀 약속)
PATH_KEYS = [
    "employee_id",       # str        누가
    "tool_id",           # str        어떤 AI 도구로
    "asset_id",          # str        어떤 자산에
    "approved",          # bool       회사 승인 도구인가 (ai_tools.approved)
    "scopes",            # list[str]  권한 + 실제 행동 합집합, 예 ["read", "send"]
    "sensitivity",       # str        일반 / 기밀 / 개인정보 (assets)
    "employee_status",   # str        재직 / 퇴사 (employees)
    "bytes_out",         # int        이 직원이 이 도구로 보낸 총 바이트 (network_logs)
    "network_log_ids",   # list[str]  관련 network_logs.log_id
    "payload_hit_count", # int        관련 로그에서 찾은 민감 정보 개수
    "payload_log_ids",   # list[str]  민감 정보가 나온 log_id
    "grant_id",          # str|None   관련 oauth_grants.grant_id (첫 번째)
    "proc_id",           # str|None   관련 processes.proc_id (첫 번째)
    "activity_count",    # int        asset_activities 에서 다룬 record_count 합
]


def _records(table: pd.DataFrame | None) -> list[dict]:
    """DataFrame 을 dict 행 목록으로 바꾼다. 없거나 비었으면 []."""
    if table is None or not isinstance(table, pd.DataFrame) or table.empty:
        return []
    return table.to_dict("records")


def _text(value) -> str:
    """NaN/None 을 빈 문자열로 바꾸고 앞뒤 공백을 지운다."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def _to_int(value) -> int:
    """숫자로 바꿀 수 없으면 0."""
    if value is None:
        return 0
    try:
        if pd.isna(value):
            return 0
    except (TypeError, ValueError):
        pass
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _to_bool(value) -> bool:
    """approved 열(True/False, 1/0, 'true'/'false')을 bool 로 바꾼다."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(value, (int, float)):
        return int(value) != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}


def build_paths(
    usage: pd.DataFrame,
    hits: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
) -> list[dict]:
    """`직원 → AI 도구 → 자산` 경로 목록을 만든다.

    입력
    - usage: detector.detect_tools 결과
    - hits: payload_scanner.scan_logs 결과
    - tables: 원본 7개 {"employees": df, "assets": df, "ai_tools": df, "network_logs": df,
                       "oauth_grants": df, "asset_activities": df, "processes": df}

    경로를 만드는 곳 (키는 employee_id + tool_id + asset_id)
    1. oauth_grants 한 줄   → (employee_id, tool_id, asset_id), scope 를 쉼표로 나눠 scopes 에
    2. processes 중 usage 에 잡힌 줄 → (employee_id, 그 tool_id, connected_asset_id), scopes 는 일단 []
    같은 키가 여러 번 나오면 하나로 합친다.

    합친 뒤 채울 것
    - asset_activities 에서 같은 (tool_id, asset_id) 의 action 을 scopes 에 추가, record_count 합 → activity_count
    - network_logs 에서 같은 (employee_id, tool_id) 로 판별된 로그의 bytes_out 합, log_id 목록
    - hits 중 그 로그들에 해당하는 개수와 log_id 목록
    - approved, sensitivity, employee_status 는 각 표에서 찾아 넣기
    - scopes 는 중복 없이 정렬: sorted(set(...))

    출력: PATH_KEYS 를 모두 가진 dict 의 리스트

    힌트: pandas merge 를 써도 되고, dict 로 하나씩 모아도 됩니다. 편한 방법으로!
    """
    paths: dict[tuple[str, str, str], dict] = {}

    def add_path(employee_id: str, tool_id: str, asset_id: str) -> dict | None:
        """키(직원, 도구, 자산)가 없으면 만들고 돌려준다. 빈 값이면 버린다."""
        if not employee_id or not tool_id or not asset_id:
            return None
        key = (employee_id, tool_id, asset_id)
        if key not in paths:
            paths[key] = {
                "employee_id": employee_id,
                "tool_id": tool_id,
                "asset_id": asset_id,
                "scopes": set(),
                "grant_id": None,
                "proc_id": None,
            }
        return paths[key]

    # 임직원 상태 / 자산 민감도 / 도구 승인 여부 lookup
    employees = {
        _text(row.get("employee_id")): _text(row.get("status"))
        for row in _records(tables.get("employees"))
        if _text(row.get("employee_id"))
    }
    assets = {
        _text(row.get("asset_id")): _text(row.get("sensitivity"))
        for row in _records(tables.get("assets"))
        if _text(row.get("asset_id"))
    }
    tools = {
        _text(row.get("tool_id")): _to_bool(row.get("approved"))
        for row in _records(tables.get("ai_tools"))
        if _text(row.get("tool_id"))
    }
    processes = {
        _text(row.get("proc_id")): row
        for row in _records(tables.get("processes"))
        if _text(row.get("proc_id"))
    }

    # 1) oauth_grants 한 줄 → 경로 한 줄 (부여된 권한을 scopes 에)
    for grant in _records(tables.get("oauth_grants")):
        path = add_path(
            _text(grant.get("employee_id")),
            _text(grant.get("tool_id")),
            _text(grant.get("asset_id")),
        )
        if path is None:
            continue
        for scope in _text(grant.get("scope")).split(","):
            scope = scope.strip()
            if scope:
                path["scopes"].add(scope)
        grant_id = _text(grant.get("grant_id"))
        if path["grant_id"] is None and grant_id:
            path["grant_id"] = grant_id

    usage_rows = _records(usage)

    # 2) usage 에 잡힌 processes → 경로 (연결된 자산 사용, scopes 는 나중에 채움)
    for row in usage_rows:
        if _text(row.get("source_table")) != "processes":
            continue
        proc_id = _text(row.get("source_id"))
        proc = processes.get(proc_id)
        if proc is None:
            continue
        path = add_path(
            _text(row.get("employee_id")) or _text(proc.get("employee_id")),
            _text(row.get("tool_id")),
            _text(proc.get("connected_asset_id")),
        )
        if path is None:
            continue
        if path["proc_id"] is None and proc_id:
            path["proc_id"] = proc_id

    # (도구, 자산) 별 실제 행동과 처리 건수
    activity_scopes: dict[tuple[str, str], set[str]] = {}
    activity_counts: dict[tuple[str, str], int] = {}
    for activity in _records(tables.get("asset_activities")):
        tool_id = _text(activity.get("tool_id"))
        asset_id = _text(activity.get("asset_id"))
        if not tool_id or not asset_id:
            continue
        key = (tool_id, asset_id)
        action = _text(activity.get("action"))
        if action:
            activity_scopes.setdefault(key, set()).add(action)
        activity_counts[key] = activity_counts.get(key, 0) + _to_int(activity.get("record_count"))

    # (직원, 도구) 별 네트워크 전송 — 로그에는 자산 정보가 없어 같은 도구 경로에 붙인다
    network: dict[tuple[str, str], dict] = {}
    for row in usage_rows:
        if _text(row.get("source_table")) != "network_logs":
            continue
        employee_id = _text(row.get("employee_id"))
        tool_id = _text(row.get("tool_id"))
        log_id = _text(row.get("source_id"))
        if not employee_id or not tool_id or not log_id:
            continue
        bucket = network.setdefault((employee_id, tool_id), {"bytes_out": 0, "log_ids": set()})
        if log_id in bucket["log_ids"]:  # 같은 로그를 두 번 세지 않는다
            continue
        bucket["log_ids"].add(log_id)
        bucket["bytes_out"] += _to_int(row.get("bytes_out"))

    # log_id 별 민감 정보 발견 건수
    hit_counts: dict[str, int] = {}
    for hit in _records(hits):
        log_id = _text(hit.get("log_id"))
        if log_id:
            hit_counts[log_id] = hit_counts.get(log_id, 0) + 1

    # 합친 경로마다 PATH_KEYS 순서대로 값을 채운다
    result: list[dict] = []
    for key in sorted(paths):
        path = paths[key]
        employee_id = path["employee_id"]
        tool_id = path["tool_id"]
        asset_id = path["asset_id"]

        scopes = set(path["scopes"])
        scopes |= activity_scopes.get((tool_id, asset_id), set())

        bucket = network.get((employee_id, tool_id), {"bytes_out": 0, "log_ids": set()})
        log_ids = sorted(bucket["log_ids"])
        payload_log_ids = [log_id for log_id in log_ids if hit_counts.get(log_id, 0) > 0]

        row = {
            "employee_id": employee_id,
            "tool_id": tool_id,
            "asset_id": asset_id,
            "approved": tools.get(tool_id, False),
            "scopes": sorted(scopes),
            "sensitivity": assets.get(asset_id) or None,
            "employee_status": employees.get(employee_id) or None,
            "bytes_out": _to_int(bucket["bytes_out"]),
            "network_log_ids": log_ids,
            "payload_hit_count": sum(hit_counts.get(log_id, 0) for log_id in log_ids),
            "payload_log_ids": payload_log_ids,
            "grant_id": path["grant_id"],
            "proc_id": path["proc_id"],
            "activity_count": _to_int(activity_counts.get((tool_id, asset_id), 0)),
        }
        result.append({key_name: row[key_name] for key_name in PATH_KEYS})
    return result
