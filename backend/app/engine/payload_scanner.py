"""F-06 전송 내용 스캔 (담당: 탐지)

할 일: PATTERNS 를 채우고 scan_text 를 완성하세요.
완료 기준: `pytest tests/test_payload_scanner.py` 통과
"""
import re

import pandas as pd

HIT_COLUMNS = ["log_id", "type", "start", "end"]

# 종류 이름 → 정규식. 예시로 전화번호 하나만 넣어 두었습니다.
PATTERNS: dict[str, re.Pattern] = {
    "전화번호": re.compile(r"01[016789]-?\d{3,4}-?\d{4}"),
    # TODO(탐지): "주민등록번호"  예) 900101-1234567
    # TODO(탐지): "이메일"        예) kim@company.com
    # TODO(탐지): "API 키"        예) sk-로 시작하는 긴 문자열, AKIA로 시작하는 20자
    # TODO(탐지): "소스코드"      예) def , import , SELECT ... FROM  (선택)
}


def scan_text(text: str) -> list[dict]:
    """문자열 하나에서 민감 정보를 찾는다.

    입력: "홍길동,010-1234-5678,서울시"
    출력: [{"type": "전화번호", "start": 4, "end": 17}]
        start, end 는 text[start:end] 가 찾은 부분이 되는 위치 (re 의 m.start(), m.end())

    힌트: PATTERNS 를 돌면서 pattern.finditer(text) 를 쓰세요. 결과는 start 순서로 정렬.
    """
    hits: list[dict] = []
    # TODO(탐지)
    return hits


def scan_logs(network_logs: pd.DataFrame) -> pd.DataFrame:
    """네트워크 로그 전체의 payload_sample 을 스캔한다. (이 함수는 완성되어 있음)"""
    rows = []
    for _, log in network_logs.iterrows():
        for hit in scan_text(str(log.get("payload_sample", ""))):
            rows.append({"log_id": log["log_id"], **hit})
    return pd.DataFrame(rows, columns=HIT_COLUMNS)
