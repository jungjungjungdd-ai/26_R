"""F-03 ~ F-05 AI 도구 탐지 (담당: 탐지)

할 일: 아래 두 함수의 TODO를 채우세요.
완료 기준: `pytest tests/test_detector.py` 통과
"""
import json

import pandas as pd

USAGE_COLUMNS = ["employee_id", "tool_id", "source_table", "source_id", "bytes_out"]


def _as_list(value) -> list:
    """JSON 문자열(또는 이미 리스트)을 리스트로 바꾼다. 비어 있으면 []."""
    if isinstance(value, list):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if not text:
        return []
    try:
        items = json.loads(text)
    except (TypeError, ValueError):
        return []
    return items if isinstance(items, list) else []


def _to_int(value) -> int:
    """숫자로 바꿀 수 없으면 0."""
    if pd.isna(value):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def build_lookup(ai_tools: pd.DataFrame) -> tuple[dict, dict]:
    """AI 카탈로그로 '도메인 → tool_id', '프로세스 이름 → tool_id' 사전을 만든다.

    입력 ai_tools 예:
        tool_id="T_N8N", domains='["hooks.n8n.io", "n8n.cloud"]', process_names='[]'
    출력 예:
        ({"hooks.n8n.io": "T_N8N", "n8n.cloud": "T_N8N"}, {"mcp-server-postgres": "T_MCP_PG"})

    힌트: domains, process_names는 JSON 문자열이라 json.loads()로 리스트로 바꿔야 합니다.
    """
    domain_map: dict[str, str] = {}
    process_map: dict[str, str] = {}
    for _, tool in ai_tools.iterrows():
        tool_id = str(tool["tool_id"])
        # 도메인은 대소문자·앞뒤 공백 차이를 무시하고 비교한다
        for domain in _as_list(tool.get("domains")):
            domain_map[str(domain).strip().lower()] = tool_id
        for process_name in _as_list(tool.get("process_names")):
            process_map[str(process_name).strip()] = tool_id
    return domain_map, process_map


def detect_tools(network_logs: pd.DataFrame, processes: pd.DataFrame, ai_tools: pd.DataFrame) -> pd.DataFrame:
    """네트워크 로그와 PC 실행 기록에서 AI 도구 사용을 찾는다.

    출력: AI 도구로 판별된 기록만, 열은 USAGE_COLUMNS
        employee_id  tool_id   source_table   source_id  bytes_out
        E001         T_N8N     network_logs   N0001      850000
        E002         T_MCP_PG  processes      P0001      0

    규칙
    - network_logs.domain 이 domain_map 에 있으면 그 tool_id (bytes_out 그대로)
    - processes.process_name 이 process_map 에 있으면 그 tool_id (bytes_out 은 0)
    - 카탈로그에 없는 도메인·프로세스는 버린다
    """
    domain_map, process_map = build_lookup(ai_tools)
    rows: list[dict] = []
    # network_logs: 도메인이 카탈로그에 있으면 AI 도구 사용 기록
    for _, log in network_logs.iterrows():
        tool_id = domain_map.get(str(log.get("domain", "")).strip().lower())
        if tool_id is None:
            continue
        rows.append({
            "employee_id": log["employee_id"],
            "tool_id": tool_id,
            "source_table": "network_logs",
            "source_id": log["log_id"],
            "bytes_out": _to_int(log.get("bytes_out", 0)),
        })
    # processes: 프로세스 이름이 카탈로그에 있으면 AI 도구 사용 기록
    for _, proc in processes.iterrows():
        tool_id = process_map.get(str(proc.get("process_name", "")).strip())
        if tool_id is None:
            continue
        rows.append({
            "employee_id": proc["employee_id"],
            "tool_id": tool_id,
            "source_table": "processes",
            "source_id": proc["proc_id"],
            "bytes_out": 0,  # 실행 기록에는 전송량이 없다
        })
    return pd.DataFrame(rows, columns=USAGE_COLUMNS)
