"""
F-06 전송 내용 스캔 (담당: 탐지)

할 일: PATTERNS 를 채우고 scan_text 를 완성하세요.
완료 기준: pytest tests/test_payload_scanner.py 통과
"""

import re

import pandas as pd


HIT_COLUMNS = ["log_id", "type", "start", "end"]


# 종류 이름 → 정규식
PATTERNS: dict[str, re.Pattern] = {
    "주민등록번호": re.compile(
    r"(?<!\d)\d{6}-?[1-4]\d{6}(?!\d)"
    ),

    "전화번호": re.compile(
        r"(?<!\d)01[016789][-\s]?\d{3,4}[-\s]?\d{4}(?!\d)"
    ),

    "이메일": re.compile(
    r"[a-zA-Z][a-zA-Z0-9._%+-]*"
    r"@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    ),

    # API 키
    # sk-로 시작하는 긴 문자열 또는 AKIA로 시작하는 20자
    "API 키": re.compile(
        r"\bsk-[a-zA-Z0-9_-]{20,}\b|\bAKIA[A-Z0-9]{16}\b"
    ),

    "소스코드": re.compile(
    r"\bdef\s+[a-zA-Z_]\w*\s*\("
    r"|\bimport\s+[a-zA-Z_][a-zA-Z0-9_.]*"
    r"|\bSELECT\b.+?\bFROM\b",
    re.IGNORECASE | re.DOTALL
    ),
}


def scan_text(text: str) -> list[dict]:
    """문자열 하나에서 민감 정보를 찾는다.

    입력: "홍길동,010-1234-5678,서울시"

    출력:
    [
        {"type": "전화번호", "start": 4, "end": 17}
    ]

    start, end는 text[start:end]가 찾은 부분이 되는 위치다.
    """

    hits: list[dict] = []

    # 등록된 모든 정규식 순회
    for type_name, pattern in PATTERNS.items():

        # 문자열에서 일치하는 모든 부분 검색
        for match in pattern.finditer(text):

            hits.append({
                "type": type_name,
                "start": match.start(),
                "end": match.end()
            })

    # 시작 위치 기준 오름차순 정렬
    hits.sort(key=lambda hit: hit["start"])

    return hits


def scan_logs(network_logs: pd.DataFrame) -> pd.DataFrame:
    """네트워크 로그 전체의 payload_sample 을 스캔한다."""

    rows = []

    for _, log in network_logs.iterrows():

        for hit in scan_text(str(log.get("payload_sample", ""))):

            rows.append({
                "log_id": log["log_id"],
                **hit
            })

    return pd.DataFrame(rows, columns=HIT_COLUMNS)