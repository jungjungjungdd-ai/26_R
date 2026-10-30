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
    paths: list[dict] = []
    # TODO(위험도)
    return paths
