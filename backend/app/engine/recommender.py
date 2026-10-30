"""F-17 조치 추천 (담당: 위험도, 선택 기능)

필수 기능이 끝난 뒤에 구현합니다.
"""


def recommend(path: dict, current_score: int) -> list[dict]:
    """경로 하나에 대해 업무를 멈추지 않는 조치를 추천한다.

    출력 예:
    [{"rec_id": "REC01", "action": "권한 축소",
      "description": "Gmail 전체 읽기를 특정 라벨 읽기로 축소", "expected_score": 20}]

    아이디어
    - 소유 직원 퇴사         → 즉시 회수 (expected_score 0)
    - write/delete 권한     → 읽기 전용으로 축소 (R03 → R02 로 바뀐 점수)
    - 로컬 MCP              → 승인된 MCP 허브로 이전 (R01, R03 제거)
    expected_score 는 path 를 고친 복사본으로 scorer.score 를 다시 돌려 구하면 정확합니다.
    """
    # TODO(위험도, 선택)
    return []
