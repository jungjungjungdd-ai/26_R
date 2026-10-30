"""F-10, F-11 위험도 점수와 근거 (담당: 위험도)  [핵심]

할 일: score 함수를 완성하세요.
완료 기준: `pytest tests/test_scorer.py` 통과
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


def level_of(score: int) -> str:
    """70 이상 위험, 40~69 주의, 39 이하 낮음"""
    if score >= 70:
        return "위험"
    if score >= 40:
        return "주의"
    return "낮음"


def reason(code: str, table: str | None, row_id: str | None, description: str | None = None) -> dict:
    """근거 한 줄을 만든다. (완성되어 있음)"""
    points, default_desc = RULES[code]
    return {"rule_code": code, "points": points, "description": description or default_desc,
            "source": {"table": table, "row_id": row_id}}


def score(path: dict) -> dict:
    """경로 하나의 점수, 등급, 근거를 계산한다.

    입력: correlator.PATH_KEYS 형식의 dict
    출력: {"score": 95, "level": "위험", "reasons": [reason(...), ...]}

    규칙과 근거 출처
    - R01 approved 가 False            → reason("R01", "ai_tools", tool_id)
    - R03 scopes 에 write 또는 delete  → 권한 근거 (grant_id 있으면 oauth_grants, 없으면 processes/proc_id)
      R02 그게 아니고 read 가 있으면   → 같은 근거
    - R05 sensitivity == "개인정보"    → reason("R05", "assets", asset_id)
      R04 sensitivity == "기밀"
    - R06 scopes 에 send 또는 bytes_out > 0
          send 가 있으면 oauth_grants/grant_id, 아니면 network_logs/network_log_ids[0]
    - R07 payload_hit_count > 0        → network_logs/payload_log_ids[0],
          설명은 f"전송 내용에 민감 정보 {payload_hit_count}건 포함"
    - R08 employee_status == "퇴사"    → reason("R08", "employees", employee_id)
    합계는 최대 100, 등급은 level_of 사용
    """
    reasons: list[dict] = []
    # TODO(위험도)
    total = min(100, sum(r["points"] for r in reasons))
    return {"score": total, "level": level_of(total), "reasons": reasons}
