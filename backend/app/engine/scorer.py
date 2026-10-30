"""F-10, F-11 위험도 점수와 근거 (담당: 위험도)  [핵심]

경로 하나(correlator.PATH_KEYS 형식 dict)를 받아 규칙별 점수를 더하고,
등급과 근거 목록을 만든다.
"""

# 위험도 규칙표 (기능명세서와 같음)
RULES = {
    "R01": (20, "비승인 도구"),
    "R02": (5, "읽기 권한만 있음"),
    "R03": (15, "쓰기·삭제 권한 있음"),
    "R04": (10, "기밀 자산 접근"),
    "R05": (20, "개인정보 자산 접근"),
    "R06": (15, "외부 전송 권한 또는 실제 전송 발생"),
    "R07": (20, "전송 내용에 민감 정보 포함"),
    "R08": (15, "소유 직원 퇴사"),
}

MAX_SCORE = 100


def level_of(score: int) -> str:
    """70 이상 위험, 40~69 주의, 39 이하 낮음"""
    if score >= 70:
        return "위험"
    if score >= 40:
        return "주의"
    return "낮음"


def reason(code: str, table: str | None, row_id: str | None, description: str | None = None) -> dict:
    """근거 한 줄을 만든다."""
    points, default_description = RULES[code]
    return {
        "rule_code": code,
        "points": points,
        "description": description or default_description,
        "source": {"table": table, "row_id": row_id},
    }


def _grant_source(path: dict) -> tuple[str | None, str | None]:
    """권한 근거: grant_id가 있으면 oauth_grants, 없으면 processes(proc_id)."""
    if path.get("grant_id"):
        return "oauth_grants", path["grant_id"]
    return "processes", path.get("proc_id")


def score(path: dict) -> dict:
    """경로 하나의 점수, 등급, 근거를 계산한다.

    입력: correlator.PATH_KEYS 형식의 dict
    출력: {"score": 95, "level": "위험", "reasons": [reason(...), ...]}

    규칙과 근거 출처
    - R01 approved 가 False            → ai_tools / tool_id
    - R02 읽기만 (write·delete 없음)    → 권한 근거
    - R03 write 또는 delete             → 권한 근거
    - R04 sensitivity 기밀              → assets / asset_id
    - R05 sensitivity 개인정보          → assets / asset_id
    - R06 send 권한 또는 bytes_out > 0  → 권한 근거 / network_logs 첫 행
    - R07 payload_hit_count > 0         → network_logs / payload_log_ids 첫 행
    - R08 employee_status 퇴사          → employees / employee_id
    합계가 100을 넘으면 100으로 표시한다.
    """
    scopes = set(path.get("scopes") or [])
    bytes_out = path.get("bytes_out") or 0
    net_ids = path.get("network_log_ids") or []
    payload_ids = path.get("payload_log_ids") or []
    hit_count = path.get("payload_hit_count") or 0
    grant_table, grant_row = _grant_source(path)

    reasons = []

    # R01 비승인 도구 (승인된 도구는 이것만 빠진다)
    if path.get("approved") is False:
        reasons.append(reason("R01", "ai_tools", path.get("tool_id")))

    # R02 / R03 권한 (겹치지 않음: 쓰기·삭제가 있으면 R03만)
    if scopes & {"write", "delete"}:
        reasons.append(reason("R03", grant_table, grant_row))
    elif "read" in scopes:
        reasons.append(reason("R02", grant_table, grant_row))

    # R04 / R05 자산 민감도 (겹치지 않음)
    sensitivity = path.get("sensitivity")
    if sensitivity == "개인정보":
        reasons.append(reason("R05", "assets", path.get("asset_id")))
    elif sensitivity == "기밀":
        reasons.append(reason("R04", "assets", path.get("asset_id")))

    # R06 외부 전송 권한 또는 실제 전송 발생
    if "send" in scopes:
        reasons.append(reason("R06", grant_table, grant_row, "외부 전송 권한"))
    elif bytes_out > 0:
        reasons.append(
            reason("R06", "network_logs", net_ids[0] if net_ids else None, "외부 전송 발생")
        )

    # R07 전송 내용에 민감 정보 포함
    if hit_count > 0:
        reasons.append(
            reason(
                "R07",
                "network_logs",
                payload_ids[0] if payload_ids else None,
                f"전송 내용에 민감 정보 {hit_count}건 포함",
            )
        )

    # R08 소유 직원 퇴사
    if path.get("employee_status") == "퇴사":
        reasons.append(reason("R08", "employees", path.get("employee_id")))

    total = min(sum(r["points"] for r in reasons), MAX_SCORE)
    return {"score": total, "level": level_of(total), "reasons": reasons}
